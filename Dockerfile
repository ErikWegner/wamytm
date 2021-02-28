FROM python:3.9

WORKDIR /usr/src/app

COPY Pipfile .
COPY Pipfile.lock .

RUN pip install --no-cache-dir pipenv && pipenv install --system --deploy

COPY src/ .

RUN mkdir -p /usr/src/app/wamytmsite/staticfiles/

RUN DJANGO_SETTINGS_MODULE=wamytmsite.settings.build ./manage.py collectstatic
RUN /bin/bash -c "sed -i \"s/Version: [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}/Version: $(date '+%Y-%m-%d')/g\" wamytmapp/templates/wamytmapp/footer.html"

HEALTHCHECK CMD curl --fail http://localhost:8000/status/health || exit 1

EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=wamytmsite.settings.container \
    WAMYTM_DATABASE_PORT=""
CMD [ "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "wamytmsite.wsgi" ]
