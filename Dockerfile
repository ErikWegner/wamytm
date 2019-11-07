FROM python:3.7

WORKDIR /usr/src/app

COPY Pipfile .
COPY Pipfile.lock .

RUN pip install --no-cache-dir pipenv && pipenv install --system --deploy

COPY wamytmsite/ .

EXPOSE 8000

CMD [ "python", "./manage.py", "runserver", "0.0.0.0:8000", "--noreload" ]
