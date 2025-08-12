declare
  l_count integer;
begin
-- Migrate WAMYTMAPP_TIMERANGE
-- WAMYTMAPP_TIMERANGE.data CLOB to VARCHAR2(4000)
  select count(*)
    into l_count
    from WAMYTMAPP_TIMERANGE
   where dbms_lob.getlength(data) > 4000;
  if l_count > 0 then
    raise_application_error(-20001, 'Abbruch: Es existieren Daten mit mehr als 4000 Zeichen in WAMYTMAPP_TIMERANGE.data');
  end if;

  alter table WAMYTMAPP_TIMERANGE rename column data to DATA_OLD;
  alter table WAMYTMAPP_TIMERANGE add data varchar2(4000);
  update WAMYTMAPP_TIMERANGE
     set data = dbms_lob.substr(lob_loc => data_old,
                                amount  => 4000,
                                offset  => 0);
  commit;
  alter table WAMYTMAPP_TIMERANGE modify data not null;
  alter table WAMYTMAPP_TIMERANGE drop column data_old;


-- Migrate WAMYTMAPP_ALLDAYEVENT
-- WAMYTMAPP_ALLDAYEVENT.description CLOB to VARCHAR2(255)
alter table WAMYTMAPP_ALLDAYEVENT rename column description to DESCRIPTION2;
alter table WAMYTMAPP_ALLDAYEVENT add description varchar2(255);
update WAMYTMAPP_ALLDAYEVENT t set t.description = dbms_lob.substr(t.description2, 255);
commit;
alter table WAMYTMAPP_ALLDAYEVENT drop column description2;
end;
