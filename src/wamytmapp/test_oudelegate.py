from django.test import TestCase
from django.contrib.auth.models import User

from .models import OrgUnit, TeamMember, OrgUnitDelegate


class OrgUnitDelegatesTests(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.userindex = 0

    def childOU(self, org_units, prefix, parent_name, count):
        parents = [v for k, v in org_units.items() if k.startswith(parent_name)]
        for i in range(count):
            parent = parents[i % len(parents)]
            id_base = parent.id * 10
            name = F"{prefix}{i + 1}"
            ou = OrgUnit(
                name=name, id=id_base + i, parent=parent)
            ou.save()
            org_units[name] = ou

    def setupDefaultOrgChart(self):
        org_units = {}
        org_units['company'] = OrgUnit(name="company", id=1)
        org_units['company'].save()

        self.childOU(org_units, "branch", 'company', 2)
        self.childOU(org_units, "department", "branch", 6)
        self.childOU(org_units, "unit", "department", 12)
        self.childOU(org_units, "team", "unit", 36)
        return org_units

    def setupTeamMembers(self, org_units):
        teammembers = []
        teams = [v for k, v in org_units.items() if k.startswith('team')]
        for team in teams:
            for _ in range(4):
                self.userindex = self.userindex + 1
                user = User.objects.create_user(
                    F"testuser{self.userindex}",
                    first_name='John' if self.userindex % 2 == 0 else 'Jane',
                    last_name='Doe' + str(self.userindex))
                tm = TeamMember(user=user, orgunit=team)
                tm.save()
                teammembers.append(tm)
        return teammembers

    def setupLeads(self, org_units: dict):
        ouleaders = []
        for orgunit in org_units.values():
            self.userindex = self.userindex + 1
            user = User.objects.create_user(
                F"testuser{self.userindex}",
                first_name='John' if self.userindex % 2 == 0 else 'Jane',
                last_name='Lead' + str(self.userindex))
            tm = TeamMember(user=user, orgunit=orgunit)
            tm.save()
            ouleaders.append(tm)
            oudelegate = OrgUnitDelegate(orgunit=orgunit, user=user)
            oudelegate.save()
        return ouleaders

    def setUp(self):
        self.org_units = self.setupDefaultOrgChart()
        self.people = self.setupTeamMembers(self.org_units)
        self.leaders = self.setupLeads(self.org_units)

    def test_TeamLeaderHas5Persons(self):
        # Arrange
        leader = OrgUnitDelegate.objects.get(orgunit=self.org_units['team12'])

        # Act
        delegatedUsers = OrgUnitDelegate.objects.delegatedUsers(leader.user_id)

        # Assert
        self.assertEqual(len(delegatedUsers), 5)
