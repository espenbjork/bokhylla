#!/usr/bin/env python3
"""Build a static, read-only copy of Bokhylla for GitHub Pages.

The copy holds only what the three rooms need: title, author, series, genre,
formats, reading status, year and progress. Notes, file paths, provenance,
photo sources and daily Audible listening logs are left out.

    python3 build_demo.py <output-folder>
"""
import json, re, shutil, sys
from pathlib import Path
from PIL import Image
from library import DATA, ROOT

STATIC = ROOT/'static'
KEEP = ['id', 'title', 'author', 'status', 'year', 'year_uncertain', 'finished_date', 'progress',
        'progress_unit', 'medium', 'read_count', 'language', 'series', 'series_index', 'genre',
        'cover_color', 'cover_hue', 'cover_saturation', 'title_uncertain', 'user_shelf']
EBOOK = {'EPUB', 'PDF', 'MOBI', 'AZW3'}
AUDIO = {'MP3', 'M4B', 'M4A', 'AAC', 'AAX', 'AAXC'}

def formats(b):
    # Same rule as formats() in app.js, computed here so asset paths can be dropped.
    out = set(b.get('formats') or [])
    if not out and b.get('medium') not in (None, 'unknown', 'mixed'): out.add(b['medium'])
    for a in b.get('assets', []):
        if a.get('role') == 'supplement': continue
        if a.get('format') in EBOOK: out.add('ebook')
        elif a.get('format') in AUDIO: out.add('audio')
    if b.get('audible_owned'): out.add('audio')
    return sorted(out)

def public_book(b):
    p = {k: b.get(k) for k in KEEP if k in b}
    p.update(formats=formats(b), assets=[], provenance=[], notes='', source='')
    p['cover'] = 'covers/'+Path(b['cover']).name if b.get('cover') else ''
    # Completion dates drive «Leseåret»; the per-day listening log is not published.
    hist = [{'title': h.get('title', ''), 'completions': [{k: c.get(k) for k in ('date', 'started', 'coverage', 'end_percent', 'certainty')} for c in h.get('completions', [])]}
            for h in b.get('audible_history', [])]
    if hist: p['audible_history'] = hist
    if b.get('audible_import_original'): p['audible_import_original'] = b['audible_import_original']
    return p

def build(out):
    if out.exists(): shutil.rmtree(out)
    (out/'covers').mkdir(parents=True); (out/'room').mkdir()
    library = json.loads((DATA/'library.json').read_text())
    books = [public_book(b) for b in library['books']]
    arrangement = {k: library.get('arrangement', {}).get(k) for k in ('order', 'shelves', 'sort')}
    (out/'library.json').write_text(json.dumps({'books': books, 'arrangement': arrangement}, ensure_ascii=False, separators=(',', ':')))
    for b in books:
        if not b['cover']: continue
        with Image.open(STATIC/'covers'/Path(b['cover']).name) as im:
            im = im.convert('RGB'); im.thumbnail((360, 540)); im.save(out/b['cover'], quality=78, optimize=True)
    for png in (STATIC/'room').glob('*.png'):
        with Image.open(png) as im: im.convert('RGB').save(out/'room'/(png.stem+'.jpg'), quality=80, optimize=True)
    for name in ['app.js', 'library-wall.js', 'room.js', 'reading-history.js', 'style.css', 'library-wall.css', 'reading-history.css']:
        shutil.copy(STATIC/name, out/name)
    css = (STATIC/'room.css').read_text()
    (out/'room.css').write_text(re.sub(r"'/room/([\w-]+)\.png'", r"'room/\1.jpg'", css))
    html = (STATIC/'index.html').read_text()
    html = re.sub(r'(href|src)="/(?=[\w-]+\.(css|js)")', r'\1="', html)
    html = html.replace('class="brand" href="/"', 'class="brand" href="./"')
    html = html.replace('<script src="app.js">', '<script src="demo.js"></script><script src="app.js">', 1)
    (out/'index.html').write_text(html)
    shutil.copy(ROOT/'demo'/'demo.js', out/'demo.js')
    print(f'{len(books)} bøker, {sum(1 for b in books if b["cover"])} omslag → {out}')

if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit(__doc__)
    build(Path(sys.argv[1]).resolve())
