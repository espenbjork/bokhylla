"""Read local Libation M4B metadata without decoding or modifying audio."""
import os, struct, re, json, uuid, argparse
from pathlib import Path
from library import connect, all_books, new_book, save, snapshot, now, norm, DATA, ROOT
LIBATION=Path(os.environ.get('BOKHYLLA_LIBATION',Path.home()/'Music/Libation/Books'))
def atoms(f,start,end):
    pos=start
    while pos+8<=end:
        f.seek(pos);head=f.read(8)
        if len(head)<8:raise ValueError('Ufullstendig MP4-header')
        size,tag=struct.unpack('>I4s',head);header=8
        if size==1:
            raw=f.read(8)
            if len(raw)<8:raise ValueError('Ufullstendig MP4-størrelse')
            size=struct.unpack('>Q',raw)[0];header=16
        if size==0:size=end-pos
        if size<header or pos+size>end:raise ValueError('Ufullstendig MP4-fil')
        yield tag,pos+header,pos+size
        pos+=size

def read_metadata(path):
    tags={};free={};cover=None;duration=None;has_audio=False
    size=path.stat().st_size
    with path.open('rb') as f:
        def walk(start,end,depth=0):
            nonlocal cover,duration,has_audio
            if depth>8:raise ValueError('For dyp metadata-struktur')
            for tag,a,z in atoms(f,start,end):
                if tag==b'mdat':has_audio=True
                elif tag in [b'moov',b'udta']:walk(a,z,depth+1)
                elif tag==b'meta':walk(a+4,z,depth+1)
                elif tag==b'mvhd':
                    f.seek(a);raw=f.read(min(z-a,40))
                    offset=20 if raw[0]==1 else 12
                    scale=struct.unpack_from('>I',raw,offset)[0]
                    ticks=struct.unpack_from('>Q' if raw[0]==1 else '>I',raw,offset+4)[0]
                    if scale:duration=round(ticks/scale,2)
                elif tag==b'ilst':
                    for name,na,nz in atoms(f,a,z):
                        data=None;free_name=None
                        for sub,sa,sz in atoms(f,na,nz):
                            if sz-sa>12*1024*1024:continue
                            f.seek(sa);raw=f.read(sz-sa)
                            if sub==b'data':data=raw[8:]
                            elif sub==b'name':free_name=raw[4:].decode('utf-8','replace')
                        if name==b'covr':cover=data
                        elif data is not None:
                            value=data.decode('utf-8','replace').strip('\x00')
                            if name==b'----' and free_name:free[free_name]=value
                            else:tags[name.decode('latin1')]=value
        walk(0,size)
    if not has_audio or not tags.get('©nam') or not duration:raise ValueError('Mangler lyd, tittel eller varighet')
    if path.stat().st_size!=size:raise ValueError('Filen endres fortsatt; prøv igjen når nedlastingen er ferdig')
    asin=tags.get('asin') or tags.get('CDEK') or free.get('AUDIBLE_ASIN','')
    if not asin:
        match=re.search(r'\[([A-Z0-9]{10})\]',path.name);asin=match[1] if match else ''
    return {'path':str(path),'title':tags['©nam'],'author':tags.get('©ART') or tags.get('aART') or 'Ukjent','asin':asin,'narrator':tags.get('©nrt') or tags.get('©wrt',''),'duration_seconds':duration,'series':free.get('SERIES',''),'series_index':free.get('PART',''),'size':size,'cover_bytes':cover,'genres':[s.strip() for s in tags.get('©gen','').split(',') if s.strip()]}

def title_key(s):
    s=re.sub(r'\s*\(Unabridged\)\s*','',s,flags=re.I)
    return norm(s)
# Explicit, reviewed title variants between this Calibre collection and audio tags.
ALIASES={
 'artemis':'artemis a novel',
 'off to be the wizard':'m2 01 off to be the wizard',
 'the final empire':'mistborn the final empire',
 'path of daggers':'the path of daggers',
 'towers of midnight':'towers of midnigh',
 'a parade of horribles':'a parade of horribles dungeon crawler carl book 8',
 'dark age':'dark age book 5 of the red rising saga',
}
def author_key(s):return ''.join(c for c in norm(s) if c.isalnum())
def matching(meta,books):
    for b in books:
        if meta['asin'] and (meta['asin']==b.get('audible_asin') or any(a.get('asin')==meta['asin'] for a in b['assets'])):return b,'asin'
        if any(a.get('path')==meta['path'] for a in b['assets']):return b,'path'
    if meta['asin']=='B009OJXEOW':
        candidates=[b for b in books if b['title']=='A Memory of Light' and b['author']=='Robert Jordan']
        if len(candidates)==1:return candidates[0],'reviewed-author-variant'
    title=title_key(meta['title']);titles={title,ALIASES.get(title,title)}
    matches=[b for b in books if title_key(b['title']) in titles and author_key(b['author'])==author_key(meta['author'])]
    return (matches[0],'title-author') if len(matches)==1 else (None,'new')

def scan():
    found=[];errors=[]
    for path in sorted(LIBATION.rglob('*.m4b')):
        if not path.resolve().is_relative_to(LIBATION.resolve()):continue
        try:found.append(read_metadata(path))
        except (OSError,ValueError,struct.error,IndexError) as e:errors.append({'path':str(path),'error':str(e)})
    return found,errors

def import_libation(c):
    metadata,errors=scan()
    if not metadata and errors:raise ValueError('Ingen ferdige lydfiler kunne leses.')
    # Backup immediately before import, including all user edits since the daily backup.
    import sqlite3
    backups=DATA/'backups';backups.mkdir(exist_ok=True)
    dest=backups/('before-libation-'+now().replace(':','-')+'-'+uuid.uuid4().hex[:6]+'.sqlite3')
    target=sqlite3.connect(dest);c.backup(target);target.close()
    report={'at':now(),'scanned':len(metadata),'added':0,'linked':0,'existing_matches':0,'covers':0,'pdfs':0,'errors':errors,'entries':[]}
    c.execute('BEGIN IMMEDIATE')
    try:
        books=all_books(c)
        for m in metadata:
            b,method=matching(m,books)
            existed=b is not None
            if not b:
                b=new_book(m['title'],m['author']);books.append(b);report['added']+=1
            if any(a.get('path')==m['path'] for a in b['assets']):continue
            if existed:report['existing_matches']+=1
            asset={'id':uuid.uuid4().hex,'path':m['path'],'format':'M4B','origin':'Audible · Libation','asin':m['asin'],'name':Path(m['path']).name,'narrator':m['narrator'],'duration_seconds':m['duration_seconds'],'size_bytes':m['size'],'audio_title':m['title']}
            b['assets'].append(asset);report['linked']+=1;b['audible_owned']=True
            if not b.get('audible_asin'):b['audible_asin']=m['asin']
            # Consumption fields (including source/medium/year) intentionally remain untouched.
            if not b['series'] and m['series']:
                b['series']=m['series']
                try:b['series_index']=float(m['series_index'])
                except (ValueError,TypeError):pass
            if m['cover_bytes'] and not b['cover']:
                raw=m['cover_bytes'];ext='png' if raw.startswith(b'\x89PNG') else 'jpg' if raw.startswith(b'\xff\xd8') else None
                if ext:
                    cover=ROOT/'static/covers'/(b['id']+'.'+ext);cover.parent.mkdir(exist_ok=True);cover.write_bytes(raw);b['cover']='/covers/'+cover.name;report['covers']+=1
            prov='Libation · '+m['asin']
            if prov not in b['provenance']:b['provenance'].append(prov)
            for pdf in Path(m['path']).parent.glob('*.pdf'):
                if not any(a.get('path')==str(pdf) for a in b['assets']):
                    b['assets'].append({'id':uuid.uuid4().hex,'path':str(pdf),'name':pdf.name,'format':'PDF','origin':'Audible · Libation','role':'supplement','asin':m['asin']});report['pdfs']+=1
            save(c,b)
            report['entries'].append({'title':m['title'],'author':m['author'],'book_title':b['title'],'book_id':b['id'],'asin':m['asin'],'match':method})
        c.execute("insert or replace into meta values('libation_import',?)",(json.dumps({k:v for k,v in report.items() if k!='entries'}),))
        snapshot(c)
    except Exception:c.rollback();raise
    reports=DATA/'imports';reports.mkdir(exist_ok=True)
    (reports/('libation-'+now().replace(':','-')+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--import',dest='apply',action='store_true');args=p.parse_args()
    with connect() as c:
        if args.apply:
            report=import_libation(c);print(json.dumps({k:v for k,v in report.items() if k!='entries'},ensure_ascii=False,indent=2))
        else:
            rows,errors=scan();books=all_books(c)
            for m in rows:
                b,method=matching(m,books)
                print(json.dumps({'title':m['title'],'author':m['author'],'series':m['series'],'part':m['series_index'],'match':b['title'] if b else None},ensure_ascii=False))
            print('ERRORS',errors)
