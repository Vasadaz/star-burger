#!/usr/bin/bash
echo "START deploy"
echo

set -e

git pull > /dev/null
echo "DONE git pull"

source .venv/bin/activate
echo "DONE activate venv"

pip install -r requirements.txt > /dev/null
echo "DONE pip"

npm ci --include=dev > /dev/null
echo "DONE npm"

./node_modules/.bin/parcel watch bundles-src/index.js --dist-dir bundles --public-url="./" > /dev/null
echo "DONE parcel"

python manage.py collectstatic --noinput > /dev/null
echo "DONE collectstatic"

python manage.py migrate > /dev/null
echo "DONE migrate"

deactivate
echo "DONE deactivate venv"

systemctl restart star-burger.service
echo "DONE restsrt site"

echo
echo "INFO status site"
systemctl status star-burger.service

echo
echo "END deploy"
