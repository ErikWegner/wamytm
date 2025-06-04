from .base import *
from .ODB import ODB_ORG, OMS

class OrgUnitManager(models.Manager):
    def selectListItems(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        return toplevel

    def selectListItemsWithAllChoice(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        toplevel.insert(0, ("", pgettext_lazy('OrgUnitManager', "All")))
        return toplevel

    def queryDescendants(self, parents):
        parentslist = tuple(parents if type(parents) is list else [parents])
        if len(parentslist) == 0:
            return list()
        qu = super().raw('''
        WITH RECURSIVE ou(id, parent_id) AS (
            SELECT id, parent_id
            FROM wamytmapp_orgunit
            WHERE id in %s
        UNION ALL
            SELECT t2.id, t2.parent_id
            FROM wamytmapp_orgunit AS t2, ou AS t1
            WHERE t2.parent_id = t1.id
        )
        SELECT DISTINCT id FROM ou
        ''', params=[parentslist])
        return list(qu)

    def queryDescendants2(self, parents):
        #parentslist = tuple(parents if type(parents) is list else [parents])
        parentslist = ','.join(str(x) for x in (parents if type(parents) is list else [parents]))
        if len(parentslist) == 0:
            return list()
        qu = super().raw('''
        select distinct t.id
  from mv_odb_org t
 where t.id > 0
 start with t.id in (''' + parentslist + ''') or 0 in (''' + parentslist + ''')
connect by t.parent_id = prior t.id
        ''')
        return list(qu)

    def queryParents(self, children):
        idlist = children if type(children) is list else [children]
        qu = super().raw('''
        WITH RECURSIVE ou(id, parent_id) AS (
            SELECT id, parent_id
            FROM wamytmapp_orgunit
            WHERE id in (%s)
        UNION ALL
            SELECT t2.id, t2.parent_id
            FROM wamytmapp_orgunit AS t2, ou AS t1
            WHERE t2.id = t1.parent_id
        )
        SELECT DISTINCT id FROM ou
        ''', idlist)
        return list(qu)

    def listDescendants(self, parent_id):
        all_org_units = super().all()
        descendants = collect_descendents(all_org_units, parent_id)
        descendants.insert(0, parent_id)
        return descendants


class OrgUnit(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True)
    delegates = models.ManyToManyField(
        User,
        through='OrgUnitDelegate'
    )

    objects = OrgUnitManager()

    class Meta:
        ordering = ['name']
        verbose_name = pgettext_lazy('Models', 'Organizational unit')
        verbose_name_plural = pgettext_lazy('Models', 'Organizational units')

    def __str__(self):
        return self.name
    
def get_children(org_units: List[OrgUnit]):
    z = []
    c = {}
    for org_unit in org_units:
        if org_unit.parent is None:
            if org_unit.id not in c.keys():
                z.append(org_unit)
                c[org_unit.id] = []
        else:
            if org_unit.parent_id not in c.keys():
                z.append(org_unit.parent)
                c[org_unit.parent_id] = []
            c[org_unit.parent_id].append(org_unit)

    r = []
    for org_unit in z:
        if org_unit.parent is None:
            r.append((org_unit.id, org_unit.name))
        if org_unit.id in c and len(c[org_unit.id]) > 0:
            charr = []
            for child_org_unit in c[org_unit.id]:
                charr.append((child_org_unit.id, child_org_unit.name))
            r.append((org_unit.name, tuple(charr)))
    return r

class OrgUnitDelegateManager(models.Manager):
    def isDelegateForUser(self, request, otheruser):
        if otheruser is None or request.user is None:
            return False
        if otheruser.id == request.user.id:
            return True
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList2(
            request.user.id)
        #teammember = TeamMember.objects.get(pk=otheruser.id)
        teammember = OMS.objects.getORG_ID(otheruser.id).m2o_org_id
        #if teammember.orgunit_id in delegatedOUList:
        if teammember in delegatedOUList:
            return True
        return False

    def delegatedOUIdList(self, user_id):
        delegatedOUList = list(super().filter(user__id=user_id).values_list('orgunit_id', flat=True))
        delegatedOUListRecursive = list(map(lambda ou: ou.id, OrgUnit.objects.queryDescendants(delegatedOUList)))
        return delegatedOUListRecursive

    def delegatedUsers(self, user_id):
        delegatedOUList = self.delegatedOUIdList(user_id)

        people = list(TeamMember.objects.filter(
            orgunit__id__in=delegatedOUList))

        return people

    def delegatedOUIdList2(self, user_id):
        delegatedOUList = list(super().filter(user__id=user_id).values_list('org_id', flat=True))
        delegatedOUListRecursive = list(map(lambda ou: ou.id, OrgUnit.objects.queryDescendants2(delegatedOUList)))
        return delegatedOUListRecursive

    def delegatedUsers2(self, user_id):
        delegatedOUList = self.delegatedOUIdList2(user_id)

        #people = list(TeamMember.objects.filter(orgunit__id__in=delegatedOUList))
        people = list(map(lambda ou: (ou.user_id, ou.first_name, ou.last_name,ou.org_name, ou.org_kbez), OMS.objects.queryTeammember(delegatedOUList)))
        return people


class OrgUnitDelegate(models.Model):
    orgunit = models.ForeignKey(OrgUnit, blank=True, null=True,on_delete=models.SET_NULL,
                                verbose_name=pgettext_lazy('Delegate', 'Organizational unit'))
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name=pgettext_lazy('Delegate', 'User'))
    org = models.ForeignKey(ODB_ORG, blank=True, null=True,on_delete=models.SET_NULL)
    objects = OrgUnitDelegateManager()

    def __str__(self):
        return str(format_lazy(
            pgettext_lazy(
                'Models', 'Delegation for {orgunit}'
            ), orgunit=self.orgunit))

    class Meta:
        verbose_name = pgettext_lazy(
            'Models', 'Delegate for an organizational unit')
        verbose_name_plural = pgettext_lazy(
            'Models', 'Delegate for organizational units')
        permissions = [
            ("assign_delegates", "Can assign delegates")
        ]

def collect_descendents(org_units: List[OrgUnit], parent_id: int):
    collected_ids = []
    ids_to_check = [parent_id]
    while True:
        pid = ids_to_check.pop(0)
        for org_unit in org_units:
            if org_unit.parent_id == pid:
                collected_ids.append(org_unit.id)
                ids_to_check.append(org_unit.id)
        if len(ids_to_check) == 0:
            break
    return collected_ids

def collect_descendents(org_units: List[OrgUnit], parent_id: int):
    collected_ids = []
    ids_to_check = [parent_id]
    while True:
        pid = ids_to_check.pop(0)
        for org_unit in org_units:
            if org_unit.parent_id == pid:
                collected_ids.append(org_unit.id)
                ids_to_check.append(org_unit.id)
        if len(ids_to_check) == 0:
            break
    return collected_ids