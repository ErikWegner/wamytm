# Install guide

## Requirements

* PostgresQL database
* OpenID Connect provider (optional), e. g. a [Keycloak](https://hub.docker.com/r/jboss/keycloak) instance, for single sign on

## Running

The application can be run using the provided container at [Docker Hub](https://hub.docker.com/r/erikwegner/korporator).

Supported environment variables:

* `SECRET_KEY` random value. Keep it secret. [Details](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-SECRET_KEY)
* `USE_X_FORWARDED_HOST` can be `True` to use a _X-Forwarded-Host_ header to construct links
* `WAMYTM_DEBUG` should be `False` in production to hide error details.
* `WAMYTM_DATABASE_HOST` Database server name
* `WAMYTM_DATABASE_NAME` Database name
* `WAMYTM_DATABASE_USERNAME` Username for database connection
* `WAMYTM_DATABASE_PASSWORD` Password  for database connection
* `WAMYTM_KEYCLOAK_CLIENT_ID` OpenID client id (value is taken from OpenID provider)
* `WAMYTM_KEYCLOAK_CLIENT_SECRET` OpenID client secret (value is taken from OpenID provider)
* `WAMYTM_KEYCLOAK_PUBLIC_KEY` JWT public key (value is taken from OpenID provider)
* `WAMYTM_KEYCLOAK_AUTH_URL` redirect uri for user logins
* `WAMYTM_KEYCLOAK_TOKEN_URL` uri to exchange tokens from backend to OpenID connect provider
* `WAMYTM_KEYCLOAK_VERIFY_SSL` should be `True` in production to verify provider connection
* `WAMYTM_TRUST_X_FORWARDED_PROTO` can be `True` to trust a _X-Forwarded_Proto_ header

### Running from repository using docker-compose

The following steps start a demonstration instance.

- Start required containers: `docker-compose up -d`
- Database
  - Connect to database server: `docker-compose exec db psql -U postgres`
  - Setup database (see [commands](#database-setup-commands))
- Keycloak identity server
  - Open Keycloak by visiting https://localhost:8443/auth/
  - Temporary accept certificate
- Korporator setup
  - Connect to the app: `docker-compose exec korporator /bin/bash`
  - Run `python manage.py migrate` to initialize database
  - Run `python manage.py createsuperuser` to create backend admin
- Access the backend at http://localhost:8000/admin/
- Access the frondend at http://localhost:8000/
  - Example users:
    user1:3itsvxks, user2:Fq5vnMfj

## Database setup commands:

```sql
create user wamytm with encrypted password 'Stw9nUvm';
alter role wamytm set client_encoding to 'utf8';
alter role wamytm set default_transaction_isolation to 'read committed';
alter role wamytm set timezone to 'UTC';
create database wamytmdb;
revoke CONNECT on DATABASE wamytmdb from public;
grant all on DATABASE wamytmdb to wamytm;
alter database wamytmdb owner to wamytm;
\c wamytmdb
alter schema public owner to wamytm;
\q
```

## Configure login with Keycloak

1. Create a new client `wamytm` in the realm's _Clients_ section
2. Configure client settings:
    - Settings > Access Type > confidential
    - Settings > Fine Grain OpenID Connect Configuration > User Info Signed Response Algorithm > RS256
    - Settings > Fine Grain OpenID Connect Configuration > Request Object Signature Algorithm > RS256
3. Use the _Client ID_ (Settings tab) as value for `WAMYTM_KEYCLOAK_CLIENT_ID`
4. Use the _Secret_ (Credentials tab) as value for `WAMYTM_KEYCLOAK_CLIENT_SECRET`
5. Get the public key from Realm Settings > Keys > Public key and put it into settings as `WAMYTM_KEYCLOAK_PUBLIC_KEY`
6. Update urls in `WAMYTM_KEYCLOAK_AUTH_URL` and `WAMYTM_KEYCLOAK_TOKEN_URL` with the correct hostname, port and realm name
7. Configure username mapper: Clients > Client ID > Mappers: Create _User Property_ mapper, set _Token Claim Name_ to `username`, Property to `username` (or something equal, e. g. email)
8. Open _Client Scopes_ and add new scope `wamytm`
9. Open _Mappers_ tab and add a new mapper: Name `wamytm-audience`, Mapper Type `Audience`, Included Client Audience: `wamytm`, Add to access token `on`
10. Open _Clients_ > wamytm > Client Scopes and add `wamytm ` from _Available client scopes_ to _Assigned default client scopes_
