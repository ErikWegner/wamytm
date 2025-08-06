from .base import *

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
def my_custom_sql(orgid, day_of_week, users):
    user = ''
    if users is not None and len(users) > 0:
        user =  "and u.username in (" + ','.join(map(lambda x: F"'{x}'", users)) + ")"        

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
with config as
 (select von, von + 4 as bis, org_id
    from (select to_date(:TAG, 'YYYY-MM-DD') as von, :ORG as org_id
            from dual) t),
orgs AS
 (SELECT t.id, t.parent_id, t.name, g.org_id, g.von, g.bis
    FROM mv_odb_org t
   cross join config g
   start with t.id = g.org_id
  connect by t.parent_id = prior t.id),
wt as
 (select t.von + level - 1 as tag, t.bis, level
    from config t
  connect by t.von + level - 1 <= t.bis),
src as
 (select distinct t.von,
                  t.bis,
                  t.kind,
                  t.user_id,
                  dbms_lob.substr(t.data, 4000) as data,
                  t.org_id,
                  u.last_name || ', ' || u.first_name || ' (' ||
                  upper(trim(leading '\\' from substr(u.username, 2))) || ')' as user_name
    from wamytmapp_timerange t
  
   cross join config g
  
    left join auth_user u
      on u.id = t.user_id
  
    left join wamytmapp_oms oms
      on oms.user_id = t.user_id
  
    left join odb_mitarbeiter2strukt m2o
      on m2o.m2o_mit_id = oms.mit_id
     and trunc(sysdate) >= m2o.m2o_von
     AND trunc(sysdate) <= COALESCE(m2o.m2o_bis, to_date('31.12.2099', 'DD.MM.RRRR'))
  
    left join wamytmapp_ma2vt m2t
      on m2t.user_id = t.user_id
  
    left join orgs org
      on org.id in (m2o.m2o_org_id, -m2t.vt_id)
  
   where (org.id is not null or g.org_id = 0)
     {user}
     and t.von <= g.bis
     and t.bis >= g.von),
ce as
 (select distinct wt.tag, src.user_id, src.user_name from src cross join wt),
asd as
 (select t.*,
         case
           when coalesce(t.lag, 'yaa') != coalesce(t.kind, 'yaa') or
                coalesce(t.lag_desc, 'yaa') != coalesce(t.data_desc, 'yaa') or
                coalesce(t.lag_partial, 'yaa') != coalesce(t.partial, 'yaa') then
            1
         end as ca
    from (select t.*,
                 lag(t.kind, 1, 'easd') over(partition by t.user_name order by t.tag) as lag,
                 lag(t.data_desc, 1, 'easd') over(partition by t.user_name order by t.tag) as lag_desc,
                 lag(t.partial, 1, 'easd') over(partition by t.user_name order by t.tag) as lag_partial
            from (select t.tag,
                         t.user_id,
                         t.user_name,
                         t.data_v,
                         min(t.wertung) as wertung,
                         listagg(t.data_desc, '; ') within group(order by t.data_partial desc) as data_desc,
                         DENSE_RANK() OVER(partition by t.tag, t.user_id order by min(t.wertung) desc, min(t.data_desc) nulls last) as rn,
                         case
                           when t.cnt = 1 then
                            coalesce('-' || min(t.data_partial), '')
                         end as partial,
                         listagg(t.kind, '') within group(order by t.data_partial desc) as kind
                  
                    from (select t.tag,
                                 t.user_id,
                                 t.user_name,
                                 g.kind,
                                 JSON_VALUE(g.data, '$.v') as data_v,
                                 JSON_VALUE(g.data, '$.partial') as data_partial,
                                 JSON_VALUE(g.data, '$.DATA_DESC') as data_desc,
                                 count(JSON_VALUE(g.data, '$.partial')) over(partition by t.tag, t.user_id) as cnt,
                                 o.wertung
                            from ce t
                          
                            left join src g
                              on t.user_name = g.user_name
                             and t.tag between g.von and g.bis
                          
                            left join wamytmapp_kind o
                              on o.kind = g.kind) t
                   group by t.tag, t.user_id, t.user_name, t.data_v, t.cnt) t
           where t.rn = 1) t)
select t.user_name,
       t.kind,
       t.data_v,
       t.data_desc,
       coalesce(t.partial, ' ') as partial,
       min(t.tag),
       max(t.lvl) as span,
       dense_rank() over(partition by t.user_name order by min(t.tag)) as dn
  from (select t.*,
               level as lvl,
               CONNECT_BY_ROOT to_char(t.tag, 'DDD') as root
          from asd t
        connect by t.user_id = prior t.user_id
               and coalesce(t.data_v, 'asergasfd') = prior coalesce(t.data_v, 'asergasfd')
               and coalesce(t.data_desc, 'asergasfd') = prior coalesce(t.data_desc, 'asergasfd')
               and coalesce(t.partial, 'asergasfd') = prior coalesce(t.partial, 'asergasfd')
               and coalesce(t.kind, 'asergasfd') = prior coalesce(t.kind, 'asergasfd')
               and t.tag = prior t.tag + 1
         start with ca = 1
         order siblings by user_name, tag) t
 group by t.root, t.user_name, t.kind, t.partial, t.data_desc, t.data_v
 order by t.user_name, min(t.tag)"""
    query = query.format(user=user)
    
    # Additional validation before executing the query
    formatted_date = day_of_week.strftime('%Y-%m-%d')
    if not formatted_date or len(formatted_date) < 10:
        formatted_date = datetime.date.today().strftime('%Y-%m-%d')
    
    #try:
    with connection.cursor() as cursor:
        cursor.execute(query, {"TAG": formatted_date, "ORG": str(orgid)})
        row = dictfetchall(cursor)
    return row
    #except Exception as e:
    #    print(connection.queries[-1]['sql'])
    #    print(f"Fehler aufgetreten: {e}")
    #    raise e