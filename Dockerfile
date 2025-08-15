FROM python:3.12-bookworm

# Oracle Instant Client variables
ARG INSTANTCLIENT_VERSION=23.8.0.25.04
ARG INSTANTCLIENT_MAJOR=23_8
ARG INSTANTCLIENT_URL=https://download.oracle.com/otn_software/linux/instantclient/2380000
ARG INSTANTCLIENT_FILE=instantclient-basiclite-linux.x64-${INSTANTCLIENT_VERSION}.zip

WORKDIR /usr/src/app

COPY Pipfile .
COPY Pipfile.lock .

RUN mkdir -p /opt/oracle

COPY . /tmp/context/
RUN if [ -f /tmp/context/${INSTANTCLIENT_FILE} ]; then \
        cp /tmp/context/${INSTANTCLIENT_FILE} /opt/oracle/; \
    else \
        wget -P /opt/oracle ${INSTANTCLIENT_URL}/${INSTANTCLIENT_FILE}; \
    fi && rm -rf /tmp/context

RUN unzip -q /opt/oracle/${INSTANTCLIENT_FILE} -d /opt/oracle
RUN echo "/opt/oracle/instantclient_${INSTANTCLIENT_MAJOR}" > /etc/ld.so.conf.d/oracle-instantclient.conf
RUN ldconfig

RUN apt update && apt install libaio1 -y

RUN pip install --no-cache-dir pipenv && pipenv install --system --deploy

COPY src/ .
COPY gunicorn.conf.py .

RUN mkdir -p /usr/src/app/wamytmsite/staticfiles/

RUN DJANGO_SETTINGS_MODULE=wamytmsite.settings.build ./manage.py collectstatic --noinput
RUN /bin/bash -c "sed -i \"s/Version: [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}/Version: $(date '+%Y-%m-%d')/g\" wamytmapp/templates/wamytmapp/footer.html"

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/status/up || exit 1

EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=wamytmsite.settings.container \
    WAMYTM_DATABASE_PORT=""
CMD [ "gunicorn", "--config", "gunicorn.conf.py", "wamytmsite.wsgi" ]
