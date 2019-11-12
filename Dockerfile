FROM python:3.7

WORKDIR /usr/src/app

COPY Pipfile .
COPY Pipfile.lock .

RUN pip install --no-cache-dir pipenv && pipenv install --system --deploy

COPY wamytmsite/ .

RUN mkdir -p /usr/src/app/wamytmsite/staticfiles/

RUN DATABASE="" SECRET_KEY="1" DJANGO_SETTINGS_MODULE=wamytmsite.settings.docker ./manage.py collectstatic

EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE wamytmsite.settings.docker

CMD [ "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "wamytmsite.wsgi" ]
