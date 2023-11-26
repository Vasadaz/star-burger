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

npm ci --include=dev
echo "DONE npm"

export NODE_OPTIONS=--no-experimental-fetch
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./" > /dev/null
echo "DONE parcel"

python manage.py collectstatic --noinput > /dev/null
echo "DONE collectstatic"

python manage.py migrate --noinput > /dev/null
echo "DONE migrate"

systemctl restart star_burger.service
echo "DONE restart site"

echo
echo "INFO status site"
systemctl status star_burger.service

source .env/django/.env
export COMMIT=`git rev-parse HEAD` HOSTNAME=`hostname`
curl -H "X-Rollbar-Access-Token: $ROLLBAR_ACCESS_TOKEN " -H "Content-Type: application/json" -X POST 'https://api.rollbar.com/api/1/deploy' -d '{"environment": "'$ROLLBAR_ENVIRONMENT'", "revision": "'$COMMIT'", "local_username": "'$USER'@'$HOSTNAME'", "comment": "Bash deployment", "status": "succeeded"}'> /dev/null

unset COMMIT HOSTNAME

echo "INFO rollbar created item of deploy"

deactivate
echo "DONE deactivate venv"

echo
echo "END deploy"

pip -V
PATH="$PATH:/home/vasadaz/.local/bin"
sudo curl https://bootstrap.pypa.io/get-pip.py | python3
pip -V
