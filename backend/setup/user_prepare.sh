#!/bin/bash
set -euo pipefail

CREDENTIALS_FILE="config/builtin_credentials.json"
mkdir -p config

export ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
export MOD_PASSWORD="${MOD_PASSWORD:-}"

mapfile -t GENERATED_PASSWORDS < <(python3 - <<'PY'
import json
import os
import secrets
from pathlib import Path

path = Path("config/builtin_credentials.json")
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
except (FileNotFoundError, json.JSONDecodeError, OSError):
    data = {}

for key, env_name in (("admin", "ADMIN_PASSWORD"), ("mod", "MOD_PASSWORD")):
    env_value = (os.environ.get(env_name) or "").strip()
    if env_value:
        data[key] = env_value
    elif not data.get(key):
        data[key] = secrets.token_hex(20)

path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
try:
    path.chmod(0o600)
except OSError:
    pass

print(data["admin"])
print(data["mod"])
PY
)

ADMIN_PASSWORD="${GENERATED_PASSWORDS[0]}"
MOD_PASSWORD="${GENERATED_PASSWORDS[1]}"
export ADMIN_PASSWORD MOD_PASSWORD

echo "Performing Migrations"
DJANGO_DEBUG=1 python3 manage.py migrate

echo "Creating Users"
DJANGO_DEBUG=1 python3 manage.py shell <<'PY'
import os
from django.contrib.auth.models import User

admin, _ = User.objects.get_or_create(
    username='admin',
    defaults={'email': '', 'is_staff': True, 'is_superuser': True, 'is_active': True},
)
admin.email = ''
admin.is_staff = True
admin.is_superuser = True
admin.is_active = True
admin.set_password(os.environ['ADMIN_PASSWORD'])
admin.save()

mod, _ = User.objects.get_or_create(
    username='mod',
    defaults={'is_active': True},
)
mod.is_active = True
mod.is_staff = False
mod.is_superuser = False
mod.set_password(os.environ['MOD_PASSWORD'])
mod.save()
PY

if [[ ! -f static/bundle.js ]]; then
    echo "building frontend"
    yarn --cwd frontend install
    yarn --cwd frontend build
fi

echo "Credentials stored in ${CREDENTIALS_FILE}"
