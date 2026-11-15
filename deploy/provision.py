"""Run as root on the VPS after uploading the application to /projects/astrodoctor."""
import pathlib
import secrets
import subprocess

def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

base = pathlib.Path('/projects/astrodoctor')
app = base
env = app / '.env'
if not env.exists():
    password = secrets.token_urlsafe(36)
    run('sudo', '-u', 'postgres', 'psql', '-v', 'ON_ERROR_STOP=1', '-c', f"CREATE ROLE astrodoctor LOGIN PASSWORD '{password}'")
    run('sudo', '-u', 'postgres', 'createdb', '-O', 'astrodoctor', 'astrodoctor')
    env.write_text(f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\nDJANGO_DEBUG=false\nDJANGO_ALLOWED_HOSTS=astrodoctor.space,www.astrodoctor.space,localhost,127.0.0.1\nDJANGO_CSRF_TRUSTED_ORIGINS=https://astrodoctor.space,https://www.astrodoctor.space\nDATABASE_URL=postgresql://astrodoctor:{password}@127.0.0.1:5432/astrodoctor\nOMP_NUM_THREADS=1\nOPENBLAS_NUM_THREADS=1\n')
    env.chmod(0o600)
    dump = pathlib.Path('/tmp/astrodoctor_20261115.sql')
    if dump.exists():
        run('sudo', '-u', 'postgres', 'psql', '-v', 'ON_ERROR_STOP=1', '-d', 'astrodoctor', '-c', 'SET ROLE astrodoctor', '-f', str(dump), stdout=subprocess.DEVNULL)
        run('sudo', '-u', 'postgres', 'psql', '-d', 'astrodoctor', '-c', 'DELETE FROM django_session', stdout=subprocess.DEVNULL)
        dump.unlink()
run('chown', '-R', 'astrodoctor:astrodoctor', str(base))
for command in [('migrate', '--noinput'), ('collectstatic', '--noinput'), ('generate_wellbeing_data',), ('train_recommender',), ('check', '--deploy')]:
    run('sudo', '-u', 'astrodoctor', str(base / '.venv/bin/python'), 'manage.py', *command, cwd=app)
pathlib.Path('/etc/supervisor/conf.d/astrodoctor.conf').write_text((app / 'deploy/astrodoctor.conf').read_text())
pathlib.Path('/etc/nginx/sites-available/astrodoctor').write_text('''server {
    listen 80;
    server_name astrodoctor.space www.astrodoctor.space;
    client_max_body_size 20m;
    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 180s;
    }
}
''')
link = pathlib.Path('/etc/nginx/sites-enabled/astrodoctor')
if not link.exists():
    link.symlink_to('/etc/nginx/sites-available/astrodoctor')
run('nginx', '-t')
run('supervisorctl', 'reread')
run('supervisorctl', 'update', 'astrodoctor')
run('systemctl', 'reload', 'nginx')
run('certbot', '--nginx', '-d', 'astrodoctor.space', '-d', 'www.astrodoctor.space', '--redirect', '--non-interactive', '--agree-tos', '--register-unsafely-without-email')
