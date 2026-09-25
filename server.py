#!/usr/bin/env python3
import argparse, csv, io, json, mimetypes, os, re, secrets, shutil, urllib.parse, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from library import *
from libation import import_libation
from visual_metadata import enrich
TOKEN=secrets.token_urlsafe(32)
HOST='127.0.0.1'
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,obj,status=200,content_type='application/json; charset=utf-8'):
        raw=json.dumps(obj,ensure_ascii=False).encode() if isinstance(obj,(dict,list)) else obj.encode() if isinstance(obj,str) else obj
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
    def allowed(self):
        return self.headers.get('Host') in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']
    def do_GET(self):
        if not self.allowed():return self.reply({'error':'Ugyldig vert.'},403)
        path=urllib.parse.urlparse(self.path).path
        try:
            with connect() as c:
                if path=='/api/library':return self.reply({'books':all_books(c),'arrangement':get_arrangement(c),'token':TOKEN,'year':2026,'calibre':json.loads((c.execute("select value from meta where key='calibre_import'").fetchone() or ['null'])[0])})
                if path=='/api/export':return self.reply({'schema_version':1,'exported_at':now(),'books':all_books(c),'arrangement':get_arrangement(c)})
                if path=='/api/export.csv':
                    out=io.StringIO();fields=['title','author','status','year','year_uncertain','finished_date','medium','source','progress','progress_unit','language','notes']
                    w=csv.DictWriter(out,fields,extrasaction='ignore');w.writeheader();w.writerows(all_books(c));return self.reply('\ufeff'+out.getvalue(),content_type='text/csv; charset=utf-8')
                if path.startswith('/api/history/'):
                    return self.reply([{'at':r['at'],'book':json.loads(r['payload'])} for r in c.execute('select at,payload from events where book_id=? order by id desc',(path.rsplit('/',1)[1],))])
                if path.startswith('/api/file/'):
                    id=path.rsplit('/',1)[1]
                    for b in all_books(c):
                        for a in b['assets']:
                            if a['id']==id:return self.send_file(Path(a['path']),True)
                    return self.reply({'error':'Filen finnes ikke.'},404)
            root=(ROOT/'static').resolve();file=(root/('index.html' if path=='/' else urllib.parse.unquote(path).lstrip('/'))).resolve()
            if not file.is_relative_to(root):return self.reply({'error':'Ikke tillatt.'},403)
            return self.send_file(file)
        except (ValueError,OSError) as e:self.reply({'error':str(e)},400)
    def send_file(self,p,download=False):
        if not p.is_file():return self.reply({'error':'Filen er ikke tilgjengelig på Mac-en.'},404)
        size=p.stat().st_size;start=0;end=size-1;partial=False
        if self.headers.get('Range'):
            m=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
            if not m:return self.reply({'error':'Ugyldig område.'},416)
            start=int(m[1]);end=min(int(m[2]) if m[2] else end,end);partial=True
            if start>end:return self.reply({'error':'Ugyldig område.'},416)
        self.send_response(206 if partial else 200);self.send_header('Content-Type',('audio/mp4' if p.suffix.lower() in ['.m4b','.m4a'] else mimetypes.guess_type(p)[0]) or 'application/octet-stream');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('X-Content-Type-Options','nosniff')
        if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        if download:self.send_header('Content-Disposition',"inline; filename*=UTF-8''"+urllib.parse.quote(p.name))
        self.end_headers()
        with p.open('rb') as f:
            f.seek(start);left=end-start+1
            while left>0:
                chunk=f.read(min(left,1024*1024))
                if not chunk:break
                self.wfile.write(chunk);left-=len(chunk)
    def do_POST(self):
        if not self.allowed() or self.headers.get('X-Bokhylla-Token')!=TOKEN:return self.reply({'error':'Last siden på nytt og prøv igjen.'},403)
        path=urllib.parse.urlparse(self.path).path
        try:
            length=int(self.headers.get('Content-Length',0))
            if length<0 or length>2*1024**3:raise ValueError('Filen er for stor. Maks 2 GB per fil.')
            backup()
            if path=='/api/upload':return self.upload(length)
            if length>10*1024**2:raise ValueError('For stor forespørsel.')
            body=json.loads(self.rfile.read(length) or b'{}')
            with connect() as c:
                if path.startswith('/api/book/'):
                    return self.reply(update(c,path.rsplit('/',1)[1],body))
                if path=='/api/place':return self.reply(place_book(c,body))
                if path=='/api/arrangement':return self.reply(set_arrangement(c,body))
                if path=='/api/books/status':return self.reply(bulk_status(c,body.get('ids'),body.get('status')))
                if path=='/api/libation':
                    report=import_libation(c);enrich();return self.reply({k:v for k,v in report.items() if k!='entries'})
                if path=='/api/calibre':
                    result=import_calibre(c);enrich();return self.reply(result)
                if path=='/api/audible/preview':return self.reply({'rows':csv_preview(body.get('text',''))})
                if path=='/api/audible/import':
                    rows=body.get('rows',[])
                    if not isinstance(rows,list) or len(rows)>10000:raise ValueError('Ugyldig import.')
                    return self.reply({'added':import_audible(c,rows)})
                if path=='/api/add':
                    title=str(body.get('title','')).strip();author=str(body.get('author','')).strip()
                    if not title or not author:raise ValueError('Fyll inn tittel og forfatter.')
                    if c.execute('select 1 from books where match_key=?',(key(title,author),)).fetchone():raise ValueError('Boka finnes allerede. Søk den opp i bokhylla.')
                    b=new_book(title[:1000],author[:1000]);b['provenance']=['Lagt til manuelt'];save(c,b,True);snapshot(c);return self.reply(b)
            self.reply({'error':'Ukjent handling.'},404)
        except (ValueError,TypeError,KeyError,OSError,sqlite3.Error) as e:self.reply({'error':str(e)},400)
    def upload(self,length):
        if length==0:raise ValueError('Filen er tom.')
        filename=Path(urllib.parse.unquote(self.headers.get('X-Filename',''))).name
        ext=Path(filename).suffix.lower()
        if ext not in ['.epub','.pdf','.m4b','.mp3','.m4a','.aac','.aax','.aaxc']:raise ValueError('Filtypen støttes ikke.')
        book_id=self.headers.get('X-Book-Id','')
        with connect() as c:
            row=c.execute('select payload from books where id=?',(book_id,)).fetchone()
            if not row:raise ValueError('Velg en bok før filen legges til.')
            b=json.loads(row[0]);folder=DATA/'files'/book_id;folder.mkdir(parents=True,exist_ok=True)
            dest=folder/(uuid.uuid4().hex+ext);temp=dest.with_suffix('.part')
            try:
                with temp.open('wb') as f:
                    remaining=length
                    while remaining:
                        chunk=self.rfile.read(min(1024*1024,remaining))
                        if not chunk:raise ValueError('Overføringen ble avbrutt.')
                        f.write(chunk);remaining-=len(chunk)
                temp.replace(dest)
                b['assets'].append({'id':uuid.uuid4().hex,'path':str(dest),'format':ext[1:].upper(),'origin':'Lokalt arkiv','name':filename})
                save(c,b,True);snapshot(c)
            except Exception:
                temp.unlink(missing_ok=True);raise
        self.reply(b)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8767);args=parser.parse_args()
    with connect() as c:
        seed(c)
        if not c.execute("select 1 from meta where key='calibre_import'").fetchone() and (CALIBRE/'metadata.db').exists():import_calibre(c)
    server=ThreadingHTTPServer((HOST,args.port),Handler)
    print(f'Bokhylla er klar: http://{HOST}:{args.port}',flush=True)
    server.serve_forever()
if __name__=='__main__':main()
