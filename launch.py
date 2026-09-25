#!/usr/bin/env python3
"""Start the local library and open it; no login item or system changes."""
import json, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path
root=Path(__file__).resolve().parent
url='http://127.0.0.1:8767/'
def ready():
    try:
        with urllib.request.urlopen(url+'api/library',timeout=1) as r:
            d=json.load(r);return isinstance(d.get('books'),list) and 'calibre' in d
    except Exception:return False
if not ready():
    (root/'data').mkdir(exist_ok=True)
    with (root/'data'/'server.log').open('a') as log:
        proc=subprocess.Popen([sys.executable,str(root/'server.py')],cwd=root,stdout=log,stderr=log,start_new_session=True)
        (root/'data'/'server.pid').write_text(str(proc.pid))
    for _ in range(40):
        if ready():break
        time.sleep(.25)
    else:raise SystemExit('Kunne ikke starte Bokhylla. Se data/server.log.')
webbrowser.open(url)
print('Bokhylla er åpen på '+url)
