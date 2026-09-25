import csv, io, json, os, re, shutil, sqlite3, unicodedata, uuid, threading
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('BOKHYLLA_DATA', ROOT/'data'))
CALIBRE = Path(os.environ.get('BOKHYLLA_CALIBRE', Path.home()/'Calibre Library'))
SNAPSHOT_LOCK = threading.Lock()
STATUSES = {'unknown', 'reading', 'finished', 'paused', 'want'}
def now(): return datetime.now().astimezone().isoformat(timespec='seconds')
def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DATA/'library.sqlite3', timeout=20)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.executescript('''CREATE TABLE IF NOT EXISTS books (id TEXT PRIMARY KEY, match_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, book_id TEXT NOT NULL REFERENCES books(id), at TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);''')
    return c

def norm(s): return re.sub(r'[^\w]+',' ',unicodedata.normalize('NFKC',s).casefold()).strip()
def key(title,author): return norm(title)+'|'+norm(author)
def all_books(c):
    books=[]
    for r in c.execute('select payload from books order by rowid'):
        b=json.loads(r[0])
        # New format history is additive; older records remain readable.
        b.setdefault('formats', [])
        b.setdefault('read_count', 1)
        books.append(b)
    return books
def save(c,b,event=False):
    b['updated_at']=now()
    c.execute('INSERT INTO books VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (b['id'],key(b['title'],b['author']),json.dumps(b,ensure_ascii=False)))
    if event: c.execute('INSERT INTO events(book_id,at,payload) VALUES(?,?,?)',(b['id'],now(),json.dumps(b,ensure_ascii=False)))
def new_book(title,author):
    return dict(id=uuid.uuid4().hex,title=title,author=author,status='unknown',year=None,year_uncertain=False,finished_date='',progress=None,progress_unit='percent',medium='unknown',formats=[],read_count=1,source='',language='',notes='',series='',series_index=None,assets=[],cover='',provenance=[],title_uncertain=False)
def snapshot(c):
    c.commit()
    with SNAPSHOT_LOCK:
        target=DATA/'library.json'
        tmp=target.with_suffix('.tmp')
        tmp.write_text(json.dumps({'schema_version':1,'exported_at':now(),'books':all_books(c),'arrangement':get_arrangement(c)},ensure_ascii=False,indent=2))
        tmp.replace(target)
def backup():
    src=DATA/'library.sqlite3'
    if src.exists():
        folder=DATA/'backups';folder.mkdir(exist_ok=True)
        dest=folder/(datetime.now().strftime('%Y-%m-%d')+'.sqlite3')
        if not dest.exists():
            a=sqlite3.connect(src);b=sqlite3.connect(dest);a.backup(b);b.close();a.close()
def seed(c):
    if c.execute("select 1 from meta where key='seed_v1'").fetchone(): return
    c.execute("insert into meta values('seed_v1',?)",(now(),));snapshot(c)
def import_calibre(c):
    if not (CALIBRE/'metadata.db').exists(): raise ValueError('Calibre-biblioteket ble ikke funnet.')
    src=sqlite3.connect((CALIBRE/'metadata.db').as_uri()+'?mode=ro',uri=True);src.row_factory=sqlite3.Row
    added=0;linked=0;skipped=[]
    for row in src.execute('select * from books order by id'):
        r=dict(row)
        if r['title'] in ['Quick Start Guide','CLAUDE']:
            skipped.append(r['title']);continue
        authors=[a[0].replace('|',',') for a in src.execute('select a.name from authors a join books_authors_link l on l.author=a.id where l.book=? order by l.id',(r['id'],))]
        author=', '.join(authors) or 'Ukjent'
        previous=c.execute('select payload from books where match_key=?',(key(r['title'],author),)).fetchone()
        b=json.loads(previous[0]) if previous else new_book(r['title'],author)
        if not previous:added+=1
        folder=(CALIBRE/r['path']).resolve()
        if not folder.is_relative_to(CALIBRE):continue
        langs=[x[0] for x in src.execute('select languages.lang_code from languages join books_languages_link l on languages.id=l.lang_code where l.book=?',(r['id'],))]
        if not b['language']: b['language']=', '.join(langs)
        series=src.execute('select name from series join books_series_link on series.id=series where book=?',(r['id'],)).fetchone()
        if series and not b['series']:b['series']=series[0];b['series_index']=r['series_index']
        for f in src.execute('select format,name from data where book=?',(r['id'],)):
            path=folder/(f['name']+'.'+f['format'].lower())
            if path.exists() and not any(a.get('path')==str(path) for a in b['assets']):
                b['assets'].append({'id':uuid.uuid4().hex,'path':str(path),'format':f['format'],'origin':'Calibre','calibre_id':r['id']});linked+=1
        cover=folder/'cover.jpg'
        if cover.exists() and not b['cover']:
            dest=ROOT/'static'/'covers';dest.mkdir(exist_ok=True)
            shutil.copy2(cover,dest/(b['id']+'.jpg'));b['cover']='/covers/'+b['id']+'.jpg'
        provenance='Calibre #'+str(r['id'])
        if provenance not in b['provenance']:b['provenance'].append(provenance)
        save(c,b)
    src.close()
    result={'added':added,'linked':linked,'skipped':skipped,'at':now()}
    c.execute("insert or replace into meta values('calibre_import',?)",(json.dumps(result),));snapshot(c);return result

def update(c,id,patch):
    r=c.execute('select payload from books where id=?',(id,)).fetchone()
    if not r:raise ValueError('Boka finnes ikke.')
    b=json.loads(r[0])
    for field in ['status','year','year_uncertain','finished_date','progress','progress_unit','medium','formats','read_count','source','language','notes','title_uncertain','genre','user_shelf','series','series_index']:
        if field in patch:b[field]=patch[field]
    if b['status'] not in STATUSES:raise ValueError('Ugyldig status.')
    if b['medium'] not in ['unknown','paper','ebook','audio','mixed']:raise ValueError('Ugyldig format.')
    if not isinstance(b.get('formats'),list) or any(x not in ['paper','ebook','audio'] for x in b['formats']):raise ValueError('Ugyldig formatliste.')
    b['formats']=sorted(set(b['formats']))
    b['read_count']=int(b.get('read_count',1))
    if b['read_count']<1 or b['read_count']>999:raise ValueError('Antall gjennomlesninger må være mellom 1 og 999.')
    if b['progress_unit'] not in ['percent','pages','minutes']:raise ValueError('Ugyldig fremdriftsenhet.')
    if b['year'] is not None:
        b['year']=int(b['year'])
        if not 1900<=b['year']<=2100:raise ValueError('År må være mellom 1900 og 2100.')
    if b['progress'] is not None:
        b['progress']=float(b['progress'])
        if b['progress']<0 or (b['progress_unit']=='percent' and b['progress']>100):raise ValueError('Ugyldig fremdrift.')
    if b['finished_date']:
        date=datetime.strptime(b['finished_date'],'%Y-%m-%d');b['year']=date.year;b['year_uncertain']=False
    if b.get('series_index') not in [None,'']:
        b['series_index']=float(b['series_index'])
    else:b['series_index']=None
    for f in ['genre','user_shelf','series']:
        if f in b and (not isinstance(b[f],str) or len(b[f])>250):raise ValueError('Ugyldig organisering.')
    for f in ['source','language','notes']:
        if not isinstance(b[f],str) or len(b[f])>20000:raise ValueError('Tekstfeltet er for langt.')
    save(c,b,True);snapshot(c);return b

def csv_preview(text):
    try:dialect=csv.Sniffer().sniff(text[:10000],delimiters=',;\t')
    except csv.Error:dialect=csv.excel
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),dialect=dialect)
    aliases={'title':['title','book title','product name','tittel','name'],'author':['author','authors','forfatter','author name'],'asin':['asin','product asin']}
    fields={norm(x):x for x in (reader.fieldnames or [])}
    mapping={k:next((fields[norm(a)] for a in v if norm(a) in fields),None) for k,v in aliases.items()}
    if not mapping['title']:raise ValueError('Fant ingen tittelkolonne. Bruk CSV med Title og Author, eller legg Amazon-eksporten i imports/audible for tilpasning.')
    rows=[];seen=set()
    for r in reader:
        title=(r.get(mapping['title']) or '').strip();author=(r.get(mapping['author']) or '').strip() if mapping['author'] else ''
        if not title:continue
        k=key(title,author)
        if k in seen:continue
        seen.add(k);rows.append({'title':title,'author':author or 'Ukjent','asin':(r.get(mapping['asin']) or '') if mapping['asin'] else ''})
    if len(rows)>10000:raise ValueError('For mange bøker i én import.')
    return rows

def import_audible(c,rows):
    count=0
    for r in rows:
        if not isinstance(r,dict) or not isinstance(r.get('title'),str) or not r['title'].strip():raise ValueError('Ugyldig bokrad.')
        title=r['title'].strip()[:1000];author=str(r.get('author') or 'Ukjent')[:1000]
        old=c.execute('select payload from books where match_key=?',(key(title,author),)).fetchone()
        b=json.loads(old[0]) if old else new_book(title,author)
        if not old:count+=1
        if 'Audible CSV' not in b['provenance']:b['provenance'].append('Audible CSV')
        if not b['source']:b['source']='Audible'
        b['audible_asin']=str(r.get('asin',''))[:100]
        b['audible_owned']=True
        save(c,b)
    snapshot(c);return count

def bulk_status(c, ids, status):
    if not isinstance(ids,list) or not ids or len(ids)>10000 or any(not isinstance(i,str) for i in ids):
        raise ValueError('Velg minst én bok.')
    if not isinstance(status,str) or status not in STATUSES:
        raise ValueError('Ugyldig status.')
    ids=list(dict.fromkeys(ids))
    # Validate every ID before writing, and commit all changes together.
    c.execute('BEGIN IMMEDIATE')
    try:
        chosen=[]
        for id in ids:
            row=c.execute('select payload from books where id=?',(id,)).fetchone()
            if not row:raise ValueError('En av bøkene finnes ikke. Last siden på nytt.')
            chosen.append(json.loads(row[0]))
        changed=0
        for b in chosen:
            if b['status']!=status:
                b['status']=status
                save(c,b,True)
                changed+=1
        snapshot(c)
    except Exception:
        c.rollback()
        raise
    return {'selected':len(ids),'changed':changed}


def get_arrangement(c):
    row=c.execute("select value from meta where key='arrangement'").fetchone()
    return json.loads(row[0]) if row else {'order':[], 'shelves':[], 'sort':'author'}

def set_arrangement(c,patch):
    if not isinstance(patch,dict):raise ValueError('Ugyldig organisering.')
    current=get_arrangement(c)
    if 'order' in patch:
        ids=patch['order']
        if not isinstance(ids,list) or len(ids)>10000 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):raise ValueError('Ugyldig rekkefølge.')
        valid={r[0] for r in c.execute('select id from books')}
        if not set(ids)<=valid:raise ValueError('Boka finnes ikke lenger.')
        current['order']=ids
    if 'shelves' in patch:
        shelves=patch['shelves']
        if not isinstance(shelves,list) or len(shelves)>100 or any(not isinstance(x,str) or not x.strip() or len(x)>100 or x.strip()=='Ikke plassert' for x in shelves):raise ValueError('Ugyldig hyllenavn.')
        current['shelves']=list(dict.fromkeys(x.strip() for x in shelves))
    if 'sort' in patch:
        if patch['sort'] not in ['title','series','genre','author','color','custom']:raise ValueError('Ugyldig sortering.')
        current['sort']=patch['sort']
    c.execute("insert or replace into meta values('arrangement',?)",(json.dumps(current,ensure_ascii=False),));snapshot(c)
    return current

def place_book(c,body):
    id=body.get('id');shelf=body.get('shelf');order=body.get('order')
    if not isinstance(shelf,str) or len(shelf)>100:raise ValueError('Ugyldig hylle.')
    current=get_arrangement(c)
    if shelf and shelf not in current['shelves'] and not any(b.get('user_shelf')==shelf for b in all_books(c)):raise ValueError('Hyllen finnes ikke.')
    valid={r[0] for r in c.execute('select id from books')}
    if not isinstance(order,list) or any(not isinstance(x,str) for x in order) or len(set(order))!=len(order) or set(order)!=valid or id not in valid:raise ValueError('Ugyldig rekkefølge. Last siden på nytt.')
    c.execute('BEGIN IMMEDIATE')
    try:
        b=json.loads(c.execute('select payload from books where id=?',(id,)).fetchone()[0]);b['user_shelf']=shelf;save(c,b,True)
        current['order']=order;current['sort']='custom'
        c.execute("insert or replace into meta values('arrangement',?)",(json.dumps(current,ensure_ascii=False),));snapshot(c)
    except Exception:c.rollback();raise
    return current
