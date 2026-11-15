# Namecheap VPS

Astro-Doctor runs at https://astrodoctor.space on 66.29.151.131.

Connect using the existing macOS keychain-backed SSH key:

```sh
ssh -o UseKeychain=yes root@66.29.151.131
```

Code, private `.env`, media, model files, and the `.venv` Python environment live in `/projects/astrodoctor`, owned by the dedicated `astrodoctor` user. PostgreSQL database and role are named `astrodoctor`.

Supervisor manages Gunicorn on `127.0.0.1:8003` using `/etc/supervisor/conf.d/astrodoctor.conf`. Nginx proxies HTTPS requests; its configuration is `/etc/nginx/sites-available/astrodoctor`. Certbot renews TLS certificates automatically. Private media is served by authenticated Django views.

```sh
supervisorctl status astrodoctor
supervisorctl restart astrodoctor
supervisorctl tail astrodoctor
```

Install `deploy/requirements.txt` using `.venv/bin/python -m pip`. NumPy 2.3.5 and SciPy 1.16.3 support the VPS CPU. Newer NumPy wheels require unavailable X86_V2 features.

Upload code updates without overwriting `.env`, `.venv`, or media, then run as root:

```sh
/projects/astrodoctor/deploy/update.sh
```

Retrain explicitly with `manage.py train_recommender` when model code changes.

`provision.py` configures a fresh installation after source, the virtual environment, and runtime dependencies have been installed. It creates the database, migrates, collects static files, generates synthetic data, trains the model, configures Supervisor and Nginx, and obtains TLS certificates. On the initial installation only, it restores `/tmp/astrodoctor_20261115.sql` if present, deletes that temporary dump, and invalidates restored login sessions. The owner explicitly authorized the initial backup transfer. Obtain authorization before transferring another backup.

Create an administrator interactively if needed:

```sh
ssh -t -o UseKeychain=yes root@66.29.151.131 'cd /projects/astrodoctor && sudo -u astrodoctor .venv/bin/python manage.py createsuperuser'
```
