#!/usr/bin/env bash
# Run as root after uploading updated application files to /projects/astrodoctor.
set -euo pipefail
cd /projects/astrodoctor
/projects/astrodoctor/.venv/bin/python -m pip install -r deploy/requirements.txt
chown -R astrodoctor:astrodoctor /projects/astrodoctor
run() { sudo -u astrodoctor /projects/astrodoctor/.venv/bin/python manage.py "$@"; }
run check --deploy
run migrate --noinput
run collectstatic --noinput
supervisorctl restart astrodoctor
for attempt in 1 2 3 4 5; do
    if curl --fail --silent --output /dev/null -H 'Host: astrodoctor.space' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8003/accounts/login/; then
        echo 'Astro-Doctor is responding.'
        exit 0
    fi
    sleep 2
done
supervisorctl tail astrodoctor
exit 1
