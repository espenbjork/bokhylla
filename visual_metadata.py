"""Enrich display metadata from local covers and embedded genre tags."""
from PIL import Image
import colorsys, sqlite3
from library import *
from libation import read_metadata

def color(path):
    with Image.open(path) as im:
        im=im.convert('RGB');im.thumbnail((80,80))
        colors=im.quantize(colors=12).convert('RGB').getcolors(6400) or []
        ranked=[]
        for n,(r,g,b) in colors:
            h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
            ranked.append((n*(.25+s)*(1 if .12<v<.93 else .2),(r,g,b)))
        rgb=max(ranked)[1] if ranked else (74,70,55)
        h,s,v=colorsys.rgb_to_hsv(*(x/255 for x in rgb))
        return '#%02x%02x%02x'%rgb,round(h*360,2),round(s,3)
def genre(tags):
    text=' '.join(tags).casefold()
    for words,label in [(['litrpg'],'LitRPG'),(['science fiction','space opera','hard science','dystopian'],'Science fiction'),(['fantasy','epic'],'Fantasy'),(['thriller','mystery','crime','suspense'],'Krim og spenning'),(['biograph','memoir'],'Biografi'),(['business','technology','computer','management'],'Fag og teknologi'),(['history','politic','social','self help','self-help','personal'],'Sakprosa'),(['literary','classic','fiction'],'Romaner')]:
        if any(w in text for w in words):return label
    return 'Uavklart sjanger'
def enrich():
    with connect() as c:
        rows=all_books(c);changed=0
        for b in rows:
            original=json.dumps(b,sort_keys=True)
            if b['cover'] and not b.get('cover_color'):
                try:b['cover_color'],b['cover_hue'],b['cover_saturation']=color(ROOT/'static'/b['cover'].lstrip('/'))
                except (OSError,ValueError):pass
            if not b.get('genre'):
                tags=[]
                for a in b['assets']:
                    if a['format']=='M4B':
                        try:tags+=read_metadata(Path(a['path'])).get('genres',[])
                        except (OSError,ValueError):pass
                if not tags:
                    ids=[a.get('calibre_id') for a in b['assets'] if a.get('calibre_id')]
                    if ids:
                        src=sqlite3.connect((CALIBRE/'metadata.db').as_uri()+'?mode=ro',uri=True)
                        for id in ids:tags += [r[0] for r in src.execute('select t.name from tags t join books_tags_link l on t.id=l.tag where l.book=?',(id,))]
                        src.close()
                b['genre']=genre(tags);b['genre_tags']=sorted(set(tags));b['genre_source']='Lokale sjangertagger' if tags else 'Uavklart'
            if json.dumps(b,sort_keys=True)!=original:save(c,b);changed+=1
        snapshot(c);print('Visuelle metadata oppdatert:',changed)
if __name__=='__main__':enrich()
