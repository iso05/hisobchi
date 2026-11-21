"""Create a private local admin password once. Never overwrite an existing one."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent
target = root / '.env'
if not target.exists():
    target.write_text('ADMIN_PASSWORD=' + secrets.token_urlsafe(24) + '\nHISOBCHI_DB=data/hisobchi.sqlite3\n', encoding='utf-8')
    print('Local admin password created in backend/.env (not printed).')
else:
    print('Existing backend/.env retained.')
