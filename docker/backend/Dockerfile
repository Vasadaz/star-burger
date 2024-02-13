FROM python:3.11.3-alpine

WORKDIR /opt/star_burger

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ../../ .

RUN apk add git && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD sleep 10 && \
    python manage.py migrate --no-input && \
    python manage.py collectstatic --no-input --clear && \
    gunicorn --preload -w 2 -b 0.0.0.0:8000 star_burger.wsgi:application
