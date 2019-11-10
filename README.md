# WAMYTM

## Installation

- Copy `settings-default.py` to `settings.py`
- Configure `settings.py`
  
  | `settings.py`| Description |
  |--------------|--------------|
  | `SECRET_KEY` | a random value |
  | `DEBUG`      | set it to `False` in production |
  | `DATABASES`  | see https://docs.djangoproject.com/en/2.2/ref/settings/#databases |
- Configure Keycloak
- Run `pipenv shell` to enter a Python virtual environment
- Run `pipenv install` to install dependencies
- Run `cd wamytmsite && python manage.py migrate` to initialize database
- Run `cd wamytmsite && python manage.py createsuperuser` to create backend admin
- Run `cd wamytmsite && python manage.py runserver` to start the application

## Keycloak-Login

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

## Development

- Run keycloak and postgres: `docker-compose up -d`
- Check logs: `docker-compose logs -f`

- Setup database:

        docker exec -it wamytm_db_1 psql -U postgres

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

- Example users:
  user1:3itsvxks, user2:Fq5vnMfj

- Run tests:
  - Bash: `DJANGO_SETTINGS_MODULE=wamytmsite.settings.test python manage.py test`
  - PowerShell: 

        [System.Environment]::SetEnvironmentVariable('DJANGO_SETTINGS_MODULE', "wamytmsite.settings.test")
        python manage.py test
