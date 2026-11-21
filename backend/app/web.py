"""Serve the compiled frontend and API from one origin."""
import mimetypes
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .main import app


DIST = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if not (DIST / 'index.html').is_file():
    raise RuntimeError('Build the frontend first: npm --prefix frontend run build')

# Windows may register ES modules as plain text, which browsers reject for PDF workers.
mimetypes.add_type('text/javascript', '.mjs')
app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/favicon.svg', include_in_schema=False)
def favicon():
    return FileResponse(DIST / 'favicon.svg')


@app.get('/', include_in_schema=False)
@app.get('/admin', include_in_schema=False)
@app.get('/ai-yordamchi', include_in_schema=False)
@app.get('/ariza', include_in_schema=False)
@app.get('/ai-ariza', include_in_schema=False)
@app.get('/ai-xizmat', include_in_schema=False)
def frontend():
    return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
