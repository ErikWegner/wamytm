FROM python:3.12

WORKDIR /usr/src/app

COPY Pipfile .
COPY Pipfile.lock .

RUN mkdir -p /opt/oracle
RUN wget -P /opt/oracle https://download.oracle.com/otn_software/linux/instantclient/2380000/instantclient-basiclite-linux.x64-23.8.0.25.04.zip
#COPY instantclient*.zip /opt/oracle/
RUN unzip /opt/oracle/instantclient-basiclite-linux.x64-23.8.0.25.04.zip -d /opt/oracle
RUN echo "/opt/oracle/instantclient_23_8" > /etc/ld.so.conf.d/oracle-instantclient.conf
RUN ldconfig
RUN apt update && apt install libaio1 -y

RUN pip install --no-cache-dir pipenv && pipenv install --system --deploy

COPY src/ .

RUN mkdir -p /usr/src/app/wamytmsite/staticfiles/

RUN DJANGO_SETTINGS_MODULE=wamytmsite.settings.build ./manage.py collectstatic --noinput
RUN /bin/bash -c "sed -i \"s/Version: [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}/Version: $(date '+%Y-%m-%d')/g\" wamytmapp/templates/wamytmapp/footer.html"

HEALTHCHECK CMD curl --fail http://localhost:8000/status/up || exit 1

EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=wamytmsite.settings.container \
    WAMYTM_DATABASE_PORT=""
CMD [ "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "wamytmsite.wsgi" ]
