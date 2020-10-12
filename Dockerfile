
FROM tiangolo/uwsgi-nginx-flask:python3.8

EXPOSE 5000

WORKDIR /app

COPY ./app /app

RUN pip install -r requirements.txt

CMD ["python", "manage.py", "runserver"]

