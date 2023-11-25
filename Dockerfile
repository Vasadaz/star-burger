FROM node:18.15-alpine AS parcel

ENV APP_DIR=/opt/star_burger

WORKDIR $APP_DIR

COPY package.json ./
COPY package-lock.json ./

RUN npm ci

COPY bundles-src/ ./

RUN ./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"


FROM python:3.11.3-alpine

ENV APP_DIR=/opt/star_burger

WORKDIR $APP_DIR

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt ./

RUN apk add git
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .
RUN python manage.py collectstatic --no-input --clear
