create user wamytm with encrypted password 'Stw9nUvm';
alter role wamytm set client_encoding to 'utf8';
alter role wamytm set default_transaction_isolation to 'read committed';
alter role wamytm set timezone to 'UTC';
ALTER USER wamytm CREATEDB;
create database wamytmdb;
revoke CONNECT on DATABASE wamytmdb from public;
grant all on DATABASE wamytmdb to wamytm;
alter database wamytmdb owner to wamytm;
\c wamytmdb
alter schema public owner to wamytm;
\q
