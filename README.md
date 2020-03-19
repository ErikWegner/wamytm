# WAMYTM – Korporator

This app allows every user to plan her/his office days and days off.

## Running

### Using docker-compose

- Start required containers: `docker-compose up -d`
- Database
  - Connect to database server: `docker-compose exec db psql -U postgres`
  - Setup database (see [commands](#database-setup-commands))
- Keycloak identity server
  - Open Keycloak by visiting https://localhost:8443/auth/
  - Login with the default credentials: username is `k-admin`, password is `s3c4stroNG`
  - Import the file `realm.json`
- Korporator setup
  - Connect to the app: `docker-compose exec korporator /bin/bash`
  - Run `python manage.py migrate` to initialize database
  - Run `python manage.py createsuperuser` to create backend admin
- Access the backend at http://localhost:8000/admin/
- Access the frondend at http://localhost:8000/

## Development

- Start required containers: `docker-compose -f docker-compose-dev.yml up -d`
- Database
  - Connect to database server: `docker-compose exec db psql -U postgres`
  - Setup database (see [commands](#database-setup-commands))
- Keycloak identity server
  - Open Keycloak by visiting https://localhost:8443/auth/
  - Login with the default credentials: username is `k-admin`, password is `s3c4stroNG`
  - Import the file `realm.json`
  - Create example users:
    user1:3itsvxks, user2:Fq5vnMfj
- Korporator setup
  - Install [Python 3.8](https://www.python.org/downloads/)
  - Install `pipenv`:

        pip install pipenv

  - Enter pipenv environment: `pipenv shell`
  - Install dependencies: `pipenv install`
  - Initialize database: `cd wamytmsite && python manage.py migrate`
  - Create super user: `cd wamytmsite && python manage.py createsuperuser`
- Run korporator
  - Run application in development mode: `cd wamytmsite && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py runserver`
  - Access the backend at http://localhost:8000/admin/
  - Access the frondend at http://localhost:8000/
- Run tests:
  - Bash: `DJANGO_SETTINGS_MODULE=wamytmsite.settings.test python manage.py test`
  - PowerShell: 

        # setup environment
        $env:DJANGO_SETTINGS_MODULE="wamytmsite.settings.test"
        cd wamytmsite
        python manage.py collectstatic

        # run tests
        python manage.py test

### Configure login with Keycloak

1. Create a new client `wamytm` in the realm's _Clients_ section
2. Configure client settings:
    - Settings > Access Type > confidential
    - Settings > Fine Grain OpenID Connect Configuration > User Info Signed Response Algorithm > RS256
    - Settings > Fine Grain OpenID Connect Configuration > Request Object Signature Algorithm > RS256
3. Use the _Client ID_ (Settings tab) as value for `SOCIAL_AUTH_KEYCLOAK_KEY`
4. Use the _Secret_ (Credentials tab) as value for `SOCIAL_AUTH_KEYCLOAK_SECRET`
5. Get the public key from Realm Settings > Keys > Public key and put it into settings as `SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY`
6. Update urls in `SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL` and `SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL` with the correct hostname, port and realm name
7. Configure username mapper: Clients > Client ID > Mappers: Create _User Property_ mapper, set _Token Claim Name_ to `username`, Property to `username` (or something equal, e. g. email)
8. Open _Client Scopes_ and add new scope `wamytm`
9. Open _Mappers_ tab and add a new mapper: Name `wamytm-audience`, Mapper Type `Audience`, Included Client Audience: `wamytm`, Add to access token `on`
10. Open _Clients_ > wamytm > Client Scopes and add `wamytm ` from _Available client scopes_ to _Assigned default client scopes_

## Database setup commands:

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

