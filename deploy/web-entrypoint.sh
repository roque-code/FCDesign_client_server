#!/bin/sh
set -e
cd /opt/traza/server
python manage.py migrate --noinput
exec gunicorn -c gunicorn.conf.py config.wsgi:application
