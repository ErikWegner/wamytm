# Development

## Preparations

- Checkout `dev` branch from repository 
- Start required containers: `docker-compose -f docker-compose-dev.yml up -d`
- Database
  - Connect to database server: `docker-compose -f docker-compose-dev.yml exec db psql -U postgres`
  - Setup database (see [commands](#database-setup-commands))
- Keycloak identity server
  - Open Keycloak by visiting https://localhost:8443/auth/
  - Temporarily accept certificate
- Korporator setup
  - Install [Python 3.9](https://www.python.org/downloads/)
  - Install [pipenv](https://pipenv.readthedocs.io/): `pip install pipenv`
  - Enter pipenv environment: `pipenv shell`
  - Install dependencies: `pipenv install`
  - Initialize database: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py migrate`
  - Create super user: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py createsuperuser`
  - (Optional) Remove existing data and create new example data: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py example_data`

## Running

- Run korporator
  - Run application in development mode: `cd src && DJANGO_SETTINGS_MODULE=wamytmsite.settings.dev python manage.py runserver`
  - Access the backend at http://localhost:8000/admin/
  - Access the frondend at http://localhost:8000/
  - Example users:
    user1:3itsvxks, user2:Fq5vnMfj

## Tests

### Run tests:

- Bash:
```bash
# setup environment
export DJANGO_SETTINGS_MODULE=wamytmsite.settings.test
cd src
./manage.py collectstatic

# run tests
./manage.py test
```

- PowerShell: 

```pwsh
# setup environment
$env:DJANGO_SETTINGS_MODULE="wamytmsite.settings.test"
cd src
python manage.py collectstatic

# run tests
python manage.py test
```

### Run tests with coverage:

```bash
cd src
DJANGO_SETTINGS_MODULE=wamytmsite.settings.test coverage run --source='.' manage.py test wamytmapp
coverage html
python -m http.server --directory htmlcov/ 8008
```

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
