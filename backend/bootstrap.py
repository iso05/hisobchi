"""Prepare local admin access and install the editable checkpoint calculators."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent
target = root / '.env'
if not target.exists():
    target.write_text('ADMIN_PASSWORD=' + secrets.token_urlsafe(24) + '\nHISOBCHI_DB=data/hisobchi.sqlite3\n', encoding='utf-8')
    print('Local admin password created in backend/.env (not printed).')
else:
    print('Existing backend/.env retained.')

# Install editable checkpoint definitions once the local admin account exists.
import os
from app.main import app
from traffic_presets import install_traffic, loan_preset

install_traffic(app, os.environ['ADMIN_PASSWORD'], extra=[loan_preset()])
