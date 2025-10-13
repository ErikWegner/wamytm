from .base import *
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class ODB_ORG(models.Model):
    org_id = models.IntegerField(primary_key=True)
    org_name = models.CharField(max_length=255, null=True)
    org_kbez = models.CharField(max_length=255, null=True)
    class Meta:
        managed = False
        db_table = 'odb_org'

    def __str__(self):
        return self.org_name + " (" + self.org_kbez + ")"
    
class ODB_STRUKT_Manager(models.Manager):
    def SelectList_with_Orgs(self):
        all_org_units = super().all().values_list("m_id", "m_org_id")
        return all_org_units

class ODB_STRUKT(models.Model):
    m_id = models.IntegerField(primary_key=True)
    m_parent_id = models.IntegerField(null=True)
    m_org_id = models.IntegerField(null=True)
    m_von = models.DateField(blank=True, null=True)
    m_bis = models.DateField(blank=True, null=True)
    objects = ODB_STRUKT_Manager()
    class Meta:
        managed = False
        db_table = 'odb_strukt'

class MV_OMS_DATEN(models.Model):
    mit_id = models.BigIntegerField(primary_key=True)
    mit_name_akt = models.CharField(max_length=255, null=True)
    mit_vorname = models.CharField(max_length=255, null=True)
    mit_austritt = models.DateField(blank=True, null=True)
    kid = models.CharField(max_length=255, null=True)
    class Meta:
        managed = False
        db_table = 'mv_oms_daten'

class orgs4wamytm(models.Model):
    m_org = models.OneToOneField(ODB_ORG, primary_key=True, on_delete=models.PROTECT)

class ODB_MITARBEITER2STRUKT(models.Model):
    m2o_id = models.IntegerField(primary_key=True)
    m2o_mit_id = models.BigIntegerField(null=True)
    m2o_org_id = models.IntegerField(null=True)
    m2o_von = models.DateField(blank=True, null=True)
    m2o_bis = models.DateField(blank=True, null=True)
    m2o_typ = models.IntegerField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'odb_mitarbeiter2strukt'

class OMSManager(models.Manager):
    def getMIT_ID(self, user_id):
        return super().all().filter(user_id__exact=user_id)[0]

    def getORG_ID(self,user_id):
        qu = super().raw('''select * from v_getORGID t where t.user_id = %s''', params=[user_id])
        if len(qu) == 0:
            return None
        return qu[0]
    
    def calculate_mit_id(self, user_id):
        """
        Berechnet mit_id für einen User (ersetzt F_UPDATE_USER2OMS)
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT F_UPDATE_USER2OMS(%s) FROM DUAL
                """, [user_id])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception:
            return None
        
    def queryAllTeammember(self, parents):
        parentslist = normalize_list(parents)
        
        if len(parentslist) == 0:
            return list()
        
        ids = parentslist[:4]
        placeholders = ','.join(['%s'] * len(ids))
        query = f"""
            SELECT g.user_id as id
              FROM odb_mitarbeiter2strukt t
              JOIN wamytmapp_oms g ON g.mit_id = t.m2o_mit_id
             WHERE trunc(sysdate) >= COALESCE(t.m2o_von, TO_DATE('01.01.1970','DD.MM.RRRR'))
               AND trunc(sysdate) <= COALESCE(t.m2o_bis, TO_DATE('31.12.2099','DD.MM.RRRR'))
               AND t.m2o_org_id IN ({placeholders})"""
        
        qu = super().raw(query, params=ids)
        return list(qu)

    def queryTeammember(self, parents):
        parentslist = normalize_list(parents)
        
        if len(parentslist) == 0:
            return list()
        
        placeholders = ','.join(['%s'] * len(parentslist))
        query = f"""
            SELECT t.*, u.first_name, u.last_name, g.org_name, g.org_kbez
            FROM v_getorgid t
            JOIN odb_org g
              ON g.org_id = t.m2o_org_id
            JOIN auth_user u
              on u.id = t.user_id
           WHERE t.m2o_org_id in ({placeholders})
           ORDER by u.last_name, u.first_name"""
        
        qu = super().raw(query, params=parentslist)

        return list(qu)

    def queryDescendants(self, parents):
        parentslist = normalize_list(parents)

        if len(parentslist) == 0:
            return list()
        
        placeholders = ','.join(['%s'] * len(parentslist))
        query = f"""
            SELECT distinct t.id
            FROM mv_odb_org t
            WHERE t.id > 0
            START WITH t.id in ({placeholders}) or 0 in ({placeholders})
            CONNECT BY t.parent_id = prior t.id
        """
        
        qu = super().raw(query,params=list(parentslist) * 2)
        return list(qu)

class OMS(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mit_id = models.IntegerField(null=True)
    objects = OMSManager()

class odb_org_Manager(models.Manager):  
    @safe_db_query
    def getORGS4FILTER(self):
        with connection.cursor() as cursor:
            cursor.execute("""
        select t.id, level, t.name, SYS_CONNECT_BY_PATH(t.name,',') as hierarchy
        from mv_odb_org t
        start with t.parent_id is null
        connect by prior t.id = t.parent_id
        order SIBLINGS by case when t.id < 0 then 1 else 2 end,t.name
            """)
            row = dictfetchall(cursor)
        return row
          
    def selectListItemsWithAllChoice(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        toplevel.insert(0, ("0", pgettext_lazy('OrgUnitManager', "All")))
        return toplevel

class mv_odb_org(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.DO_NOTHING, blank=True, null=True)
    objects = odb_org_Manager()
    class Meta:
        managed = False
        db_table = 'mv_odb_org'

@safe_db_query
def my_custom_sql2(orgid, day_of_week, users):
    user = ''
    if users is not None and len(users) > 0:
        user =  ':'.join(map(lambda x: F"{x}", users))

    # Validate and sanitize the day_of_week parameter
    if not day_of_week or not hasattr(day_of_week, 'strftime'):
        day_of_week = datetime.date.today()
    
    # Additional safety check: ensure the date is within Oracle's valid range
    min_oracle_date = datetime.date(100, 1, 1)  # More conservative minimum
    max_oracle_date = datetime.date(9000, 12, 31)  # More conservative maximum
    
    if day_of_week < min_oracle_date or day_of_week > max_oracle_date:
        day_of_week = datetime.date.today()
    
    # Additional validation: ensure year is not 0
    if day_of_week.year <= 0:
        day_of_week = datetime.date.today()
    
    query = """
        SELECT USER_NAME, KIND, DATA_V, DATA_DESC, PARTIAL, MIN_TAG, SPAN, DN
          FROM TABLE(get_events4index(:TAG, :ORG, :USERS))
         ORDER BY USER_NAME, MIN_TAG"""
    
    # Additional validation before executing the query
    formatted_date = day_of_week.strftime('%Y-%m-%d')
    if not formatted_date or len(formatted_date) < 10:
        formatted_date = datetime.date.today().strftime('%Y-%m-%d')
    
    #try:
    with connection.cursor() as cursor:
        cursor.execute(query, {"TAG": formatted_date, "ORG": str(orgid), "USERS": user })
        row = dictfetchall(cursor)
    return row

@safe_db_query
def my_custom_sql3(start, end, orgid = None):
    query = """
        SELECT TAG, USERNAME, KIND, DATA_DESC, N, CT, WT, FEIERTAG, FEIERTAG_DESC
          FROM TABLE(get_events4list(:VON, :BIS, :ORG_ID))
    """
    with connection.cursor() as cursor:
        cursor.execute(
            query,
            {
                "VON": start,
                "BIS": end,
                "ORG_ID": orgid
            }
        )
        row = dictfetchall(cursor)
    return row

@receiver(post_save, sender=User)
def create_oms_for_user(sender, instance, created, **kwargs):
    """
    Erstellt automatisch OMS-Eintrag nach User-Erstellung
    Ersetzt die Trigger AUTH_USER_AI und WAMYTM_OMS_BI
    """
    if created:  # Nur bei neuen Usern
        try:
            # Prüfen ob OMS bereits existiert (falls Trigger parallel läuft)
            if not OMS.objects.filter(user_id=instance.id).exists():
                # mit_id berechnen (ersetzt F_UPDATE_USER2OMS Funktion)
                mit_id = OMS.objects.calculate_mit_id(instance.id)
                
                # OMS erstellen
                OMS.objects.create(
                    user=instance,
                    mit_id=mit_id
                )
        except Exception as e:
            # Logging falls gewünscht
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Fehler beim Erstellen von OMS für User {instance.id}: {e}")