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
  - Temporary accept certificate
- Korporator setup
  - Connect to the app: `docker-compose exec korporator /bin/bash`
  - Run `python manage.py migrate` to initialize database
  - Run `python manage.py createsuperuser` to create backend admin
- Access the backend at http://localhost:8000/admin/
- Access the frondend at http://localhost:8000/
  - Example users:
    user1:3itsvxks, user2:Fq5vnMfj

## Development

- Checkout `dev` branch from repository
- Start required containers: `docker-compose -f docker-compose-dev.yml up -d`
- Database
  - Connect to database server: `docker-compose -f docker-compose-dev.yml exec db psql -U postgres`
  - Setup database (see [commands](#database-setup-commands))
- Keycloak identity server
  - Open Keycloak by visiting https://localhost:8443/auth/
  - Temporarily accept certificate
- Korporator setup
  - Install [Python 3.8](https://www.python.org/downloads/)
  - Install [pipenv](https://pipenv.readthedocs.io/): `pip install pipenv`
  - Enter pipenv environment: `pipenv shell`
  - Install dependencies: `pipenv install`
  - Initialize database: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py migrate`
  - Create super user: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py createsuperuser`
  - (Optional) Remove existing data and create new example data: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py example_data`
- Run korporator
  - Run application in development mode: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py runserver`
  - Access the backend at http://localhost:8000/admin/
  - Access the frondend at http://localhost:8000/
  - Example users:
    user1:3itsvxks, user2:Fq5vnMfj
- Run tests:
  - Bash:

        # setup environment
        export DJANGO_SETTINGS_MODULE=wamytmsite.settings.test
        cd src
        ./manage.py collectstatic

        # run tests
        ./manage.py test

  - PowerShell: 

        # setup environment
        $env:DJANGO_SETTINGS_MODULE="wamytmsite.settings.test"
        cd src
        python manage.py collectstatic

        # run tests
        python manage.py test

- Run tests with coverage:

  ```bash
  cd src
  DJANGO_SETTINGS_MODULE=wamytmsite.settings.test coverage run --source='.' manage.py test wamytmapp
  coverage html
  python -m http.server --directory htmlcov/ 8008
  ```

### Configure login with Keycloak

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

To run tests, execute this command:

    ALTER USER wamytm CREATEDB;

## Container settings

| Environment variable | Setting |  
|---|---|
| WAMYTM_TRUST_X_FORWARDED_PROTO |   `True` trust the X-Forwarded_Proto header |
| | `False` to ignore the header |
| USE_X_FORWARDED_HOST | `True` use X-Forwarded-Host header to construct links |
| | `False` to ignore the header |

See [docker-compose.yml](docker-compose.yml) for further settings.