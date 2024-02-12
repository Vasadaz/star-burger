FROM node:18.17.1

WORKDIR /opt/star_burger

COPY package*.json ./

RUN npm ci --include=dev
COPY ./bundles-src ./bundles-src

RUN ./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"

EXPOSE 8080

CMD [ "node", "server.js" ]
#CMD ["./node_modules/.bin/parcel", "build", "bundles-src/index.js", "--dist-dir", "bundles", "--public-url='./'"]
#CMD ["node", "bin/www"]