FROM node:18.17.1

WORKDIR /app

COPY ../../package*.json .
COPY ../../bundles-src* .

RUN npm ci --include=dev

CMD ["./node_modules/.bin/parcel", "watch", "bundles-src/index.js", "--dist-dir", "bundles", "--public-url='./'"]
