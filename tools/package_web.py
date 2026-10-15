"""Package the buildless website for upload to any static web host."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
web = root / 'web'
files = ['index.html', 'styles.css', 'favicon.svg', 'assets.js', 'engine.js',
         'renderer.js', 'audio.js', 'app.js']
for name in files:
    if not (web / name).is_file():
        raise SystemExit(f'Missing required runtime file: {name}')
target = root / 'dist' / 'tutti-frutti-web.zip'
target.parent.mkdir(exist_ok=True)
with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=9) as bundle:
    for name in files:
        bundle.write(web / name, name)
print(f'{target}: {target.stat().st_size:,} bytes, {len(files)} files')
