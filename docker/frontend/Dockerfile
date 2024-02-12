FROM node:18.15-alpine AS parcel

WORKDIR /opt/star_burger

COPY ../../package.json ./
COPY ../../package-lock.json ./

RUN npm ci

COPY ../../bundles-src/ ./

RUN ./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"
