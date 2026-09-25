"""Import the Audible archive as additive, auditable listening evidence."""
import collections,csv,hashlib,io,json,re,sqlite3,sys,zipfile
from pathlib import Path
from datetime import datetime
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
import library as lib
VERSION='audible-2026-09-24-v1'
def run(data=None):
 if data:lib.DATA=Path(data)
 source=APP/'imports/audible/data-request-2026-09-24'
 analysis=json.loads((source/'analysis.json').read_text())
 byasin={x['asin']:x for x in analysis}
 def read(name):return list(csv.DictReader(io.StringIO((source/name).read_text(encoding='utf-8-sig'))))
 catalog=read('Library.csv');raw=read('Listening History.csv');keys=[k for k in raw[0] if k!='Product Name']
 rows=list({tuple(r[k] for k in keys):r for r in raw}.values())
 daily=collections.defaultdict(lambda:collections.defaultdict(lambda:dict(events=0,recorded_ms=0,position_ms=0)))
 for r in rows:
  if r['Audio Type'] in ('Preview','CatalogSample'):continue
  d=daily[r['ASIN']][r['End Date']];d['events']+=1;d['recorded_ms']+=float(r['Event Duration Milliseconds'] or 0)
  a=float(r['Start Position Milliseconds'] or 0);b=float(r['End Position Milliseconds'] or 0);speed=float(r['Narration Speed'] or 1)
  if b>a and b-a<=float(r['Event Duration Milliseconds'] or 0)*max(1,speed)*1.25+60000:d['position_ms']=max(d['position_ms'],b)
 c=lib.connect();backup=lib.DATA/'backups'/('before-audible-history-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3');backup.parent.mkdir(exist_ok=True)
 dst=sqlite3.connect(backup);c.backup(dst);dst.close()
 report=dict(added=0,linked=0,editions=0,completions=0,year2026=0,raw_rows=len(raw),deduplicated_rows=len(rows),unmatched=[],backup=str(backup))
 c.execute('BEGIN IMMEDIATE')
 try:
  books=lib.all_books(c)
  for row in catalog:
   asin=row['ASIN'];title=row['Title'];author=row['Authors'].replace(',',', ')
   matches=[b for b in books if b.get('audible_asin')==asin or any(a.get('asin')==asin for a in b.get('assets',[])) or any(h.get('asin')==asin for h in b.get('audible_history',[]))]
   if not matches:matches=[b for b in books if lib.norm(b['title'])==lib.norm(title) and lib.norm(b['author']).replace(' ','')==lib.norm(author).replace(' ','')]
   if len(matches)>1:raise ValueError('Ambiguous ASIN '+asin)
   if matches:b=matches[0];report['linked']+=1
   else:
    b=lib.new_book(title,author);books.append(b);report['added']+=1
    b['language']=row['Language'];b['source']='Audible';b['audible_asin']=asin;b['audible_owned']=row['Ownership']=='Active'
   x=byasin.get(asin,{})
   history=dict(asin=asin,title=title,source='Audible data request',import_version=VERSION,through='2026-09-23',first=x.get('first'),last=x.get('last'),length_hours=x.get('length'),library_finished=row['Is Finished']=='Yes',completions=[dict(date=t['date'],started=t['start'],coverage=t['coverage'],end_percent=t['end'],certainty='lower' if t['coverage']<85 else 'estimated') for t in x.get('cycles',[])],days=[dict(date=d,events=v['events'],recorded_hours=round(v['recorded_ms']/3600000,6),position_percent=round(min(100,v['position_ms']/(x['length']*3600000)*100),1) if x.get('length') else None) for d,v in sorted(daily[asin].items())])
   histories=[h for h in b.get('audible_history',[]) if h['asin']!=asin]+[history]
   if b.get('audible_history')==histories:continue
   b['audible_history']=histories
   b['formats']=list(dict.fromkeys(b.get('formats',[])+([b['medium']] if b.get('medium') in ('paper','ebook','audio') else [])+['audio']))
   count=sum(len(h['completions']) for h in histories)
   if 'audible_import_original' not in b:b['audible_import_original']={k:b.get(k) for k in ('status','year','finished_date','read_count','progress','medium')}
   b['audible_estimated_read_count']=count
   if count:b['read_count']=max(b.get('read_count',1),count)
   if b['status']=='unknown' and count:b['status']='finished'
   elif b['status']=='unknown' and history['days']:
    b['status']='paused'
   if b['status'] in ('unknown','paused') and b.get('progress') is None and history['days']:
    b['progress']=next((d['position_percent'] for d in reversed(history['days']) if d['position_percent'] is not None),None);b['progress_unit']='percent'
   marker='Audible-lyttehistorikk · 2015–2026 · anslåtte fullføringer'
   if marker not in b['provenance']:b['provenance'].append(marker)
   lib.save(c,b,event=True)
  for b in books:
   for h in b.get('audible_history',[]):
    report['editions']+=1;report['completions']+=len(h['completions']);report['year2026']+=sum(t['date'].startswith('2026') for t in h['completions'])
  c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('audible_history_import',json.dumps(report)))
  lib.snapshot(c)
 except: c.rollback();raise
 finally:c.close()
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else None)
