FROM python:3.11.3-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . .

RUN apk add git && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD sleep 20 && chmod +x *sh && \
    python manage.py migrate --no-input && \
    python manage.py collectstatic --no-input --clear && \
    gunicorn --preload -w 2 -b 0.0.0.0:8080 star_burger.wsgi:application
