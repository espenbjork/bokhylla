/* A photographic room with interactive volumes, all in one 1536 × 1024 plane. */
let roomSignature='',roomZoom=1,roomPan={x:0,y:0},roomScale=1,roomDragging=false,roomLastFocus=null;
// The room opens like a normal bookshelf: spines outward. Covers remain available in the drawer.
coverView=false;
const roomBayX=[300,626,960],roomBayW=[284,291,286],roomShelfY=[239,371,500,625];
const roomDrawer=document.createElement('section');
roomDrawer.id='library-drawer';roomDrawer.setAttribute('aria-label','Bibliotekverktøy');roomDrawer.inert=true;
roomDrawer.append(document.querySelector('aside'),document.querySelector('main'));
document.body.prepend(roomDrawer);
roomDrawer.insertAdjacentHTML('afterbegin','<button id="drawer-close" aria-label="Lukk bibliotekverktøy">×</button>');
roomDrawer.insertAdjacentHTML('beforeend','<p class="room-drawer-tip">Lukk panelet for å utforske rommet. Pek på en bok for tittel og omslag. Klikk for å åpne. I «Mine hyller» kan du dra en bok foran en annen; hylle kan også velges på bokkortet.<br><br>Rommet er et generert bilde. Bokrygger og størrelser er illustrerte.</p>');
document.body.insertAdjacentHTML('afterbegin',`<div id="room-viewport" aria-label="Espens bibliotekrom"><div id="room-stage"></div></div><div id="drawer-shade" hidden></div><div id="room-top" class="room-hud"><div class="room-signature">Espens bibliotek<small>ET ROM FOR HISTORIER</small></div><button id="room-tools" aria-controls="library-drawer" aria-expanded="false">Bibliotek &nbsp; ☰</button></div><div id="room-bottom" class="room-hud"><span id="room-position" aria-live="polite"></span><button id="room-zoom-out" aria-label="Zoom ut">−</button><button id="room-zoom-in" aria-label="Zoom inn">＋</button><button id="room-reset" aria-label="Se hele rommet">Rommet</button></div><div id="room-hint">Hele samlingen er i rommet · pek på en bok · zoom og dra for å se nærmere</div><div id="room-hover" aria-hidden="true"></div>`);
$('#room-stage').append($('#shelf'));
function setRoomDrawer(open){
 if(open)roomLastFocus=document.activeElement;
 roomDrawer.classList.toggle('open',open);roomDrawer.inert=!open;$('#drawer-shade').hidden=!open;$('#room-tools').setAttribute('aria-expanded',String(open));
 if(open)$('#drawer-close').focus();else if(roomLastFocus?.isConnected)roomLastFocus.focus();
}
$('#room-tools').onclick=()=>setRoomDrawer(!roomDrawer.classList.contains('open'));
$('#drawer-close').onclick=()=>setRoomDrawer(false);$('#drawer-shade').onclick=()=>setRoomDrawer(false);
roomDrawer.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();setRoomDrawer(false);}if(e.key==='Tab'){const nodes=[...roomDrawer.querySelectorAll('button,input,select,textarea,a,summary')].filter(n=>!n.disabled&&n.getClientRects().length);const first=nodes[0],last=nodes.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
function roomCamera(){
 const fit=Math.min(innerWidth/1536,innerHeight/1024);roomScale=fit*roomZoom;
 const maxX=Math.max(0,(1536*roomScale-innerWidth)/2),maxY=Math.max(0,(1024*roomScale-innerHeight)/2);
 roomPan.x=Math.max(-maxX,Math.min(maxX,roomPan.x));roomPan.y=Math.max(-maxY,Math.min(maxY,roomPan.y));
 $('#room-stage').style.transform=`translate(calc(-50% + ${roomPan.x}px),calc(-50% + ${roomPan.y}px)) scale(${roomScale})`;
 $('#room-zoom-out').disabled=roomZoom<=1;$('#room-zoom-in').disabled=roomZoom>=2.6;
}
function zoomRoom(delta){roomZoom=Math.max(1,Math.min(2.6,roomZoom+delta));roomCamera();}
$('#room-zoom-in').onclick=()=>zoomRoom(.3);$('#room-zoom-out').onclick=()=>zoomRoom(-.3);$('#room-reset').onclick=()=>{roomZoom=1;roomPan={x:0,y:0};roomCamera();};
let cameraPointer=null;
$('#room-viewport').addEventListener('pointerdown',e=>{if(e.target.closest('[data-book]'))return;cameraPointer={x:e.clientX,y:e.clientY,px:roomPan.x,py:roomPan.y};e.currentTarget.setPointerCapture(e.pointerId);});
$('#room-viewport').addEventListener('pointermove',e=>{if(!cameraPointer)return;roomPan={x:cameraPointer.px+e.clientX-cameraPointer.x,y:cameraPointer.py+e.clientY-cameraPointer.y};roomCamera();});
$('#room-viewport').addEventListener('pointerup',()=>cameraPointer=null);$('#room-viewport').addEventListener('pointercancel',()=>cameraPointer=null);
$('#room-viewport').addEventListener('wheel',e=>{e.preventDefault();zoomRoom(-Math.sign(e.deltaY)*.08);},{passive:false});
window.addEventListener('resize',roomCamera);roomCamera();
function roomHover(b){
 const fm=formats(b).map(x=>mediumNames[x]||x).join(' · ')||mediumNames.unknown;
 const rereads=(b.read_count||1)>1?` · +${b.read_count-1}`:'';
 $('#room-hover').innerHTML=`<div class="hover-cover">${cover(b)}</div><div><strong>${esc(b.title)}</strong><p>${esc(b.author)}</p><small>${esc(statusNames[b.status])} · ${esc(fm)}${rereads}${b.series?' · '+esc(b.series):''}${selectionMode?' · Klikk for å markere':''}</small></div>`;
 $('#room-hover').classList.add('visible');
}
function hideRoomHover(){$('#room-hover').classList.remove('visible');}
function roomBookMarkup(b,classes,style,draggable=false){
 const s=spineStyle(b);
 return `<button class="room-book ${classes} ${selectionMode&&selected.has(b.id)?'selected':''}" data-book="${b.id}" aria-label="${selectionMode?'Marker':'Åpne'} ${esc(b.title)} — ${esc(b.author)}" ${selectionMode?`aria-pressed="${selected.has(b.id)}"`:''} ${draggable?'draggable="true"':''} style="--spine:${s.bg};--letter:${s.fg};${style}">${b.cover?`<span class="room-spine-art"><img src="${esc(b.cover)}" alt="" loading="lazy"></span>`:''}<span class="room-spine-text"><strong>${esc(b.title)}</strong><small>${esc(b.author)}</small></span>${(b.read_count||1)>1?`<span class="repeat-mark">+${b.read_count-1}</span>`:''}<span class="face">${cover(b)}</span>${selectionMode?`<span class="selection-mark">${selected.has(b.id)?'✓':''}</span>`:''}</button>`;
}
function tablePlacement(scene,index,count){
 if(scene==='nightstand'){
  const width=Math.min(132,440/Math.max(1,count)),gap=count>1?(440-width)/(count-1):0;
  return {x:548+index*gap,y:505+(index%2)*14,w:width,h:184,rot:[-7,4,-3,6,-5][index%5],scale:1,z:12+index};
 }
 const columns=Math.min(5,Math.max(1,Math.ceil(Math.sqrt(count*1.35)))),rows=Math.ceil(count/columns);
 const col=index%columns,row=Math.floor(index/columns),gapX=1000/Math.max(1,columns-1),gapY=210/Math.max(1,rows-1);
 return {x:205+col*gapX,y:485+row*gapY,w:132,h:188,rot:[-5,3,-2,5,-4,2][index%6],scale:1-row*.035,z:10+row*columns+col};
}
function renderLibraryWall(filtered){
 const host=$('#shelf'),old=new Map([...host.querySelectorAll('[data-book]')].map(el=>[el.dataset.book,el.getBoundingClientRect()]));
 wallAnimations.forEach(a=>a.cancel());wallAnimations=[];hideRoomHover();
 const sort=$('#sort').value;filtered.sort((a,b)=>compareBooks(a,b,sort));
 const signature=[sort,view,format,$('#search').value,coverView].join('|');if(signature!==roomSignature)roomSignature=signature;
 const scene=view==='reading'?'nightstand':view==='year'?'coffee':'library';
 $('#room-stage').dataset.scene=scene;
 const pageBooks=filtered;visibleIds=pageBooks.map(b=>b.id);
 const perBay=Math.max(1,Math.ceil(filtered.length/12));
 $('#result-count').textContent=filtered.length+' bøker';
 $('#room-position').textContent=scene==='nightstand'?`${filtered.length} bøker · på nattbordet`:scene==='coffee'?`${filtered.length} bøker · på salongbordet`:`${filtered.length} bøker · hele samlingen`;
 $('#room-hint').textContent=scene==='nightstand'?'På nattbordet · bøkene du leser nå · klikk for å åpne':scene==='coffee'?'På salongbordet · lest i 2026 · klikk for å åpne':'Hele samlingen er i rommet · pek på en bok · zoom og dra for å se nærmere';
 $('#view-toggle').hidden=scene!=='library';
 $('#arrange-description').textContent={title:'Fra A til Å',author:'Samlet etter forfatter',series:'Samlet i serier',genre:'Samlet etter sjanger',color:'Sortert etter omslagsfarge',custom:'Dra en bok foran en annen for å flytte den'}[sort];
 host.className='shelf scene-'+scene+(coverView&&scene==='library'?' room-covers':'');
 let html='';
 if(scene!=='library'){
  pageBooks.forEach((b,i)=>{
   const p=tablePlacement(scene,i,pageBooks.length);
   html+=roomBookMarkup(b,'table-book',`--tx:${p.x}px;--ty:${p.y}px;--tw:${p.w}px;--th:${p.h}px;--trot:${p.rot}deg;--tscale:${p.scale};--tz:${p.z}`);
  });
 }else for(let bay=0;bay<12;bay++){
  const col=bay%3,row=Math.floor(bay/3),list=pageBooks.slice(bay*perBay,(bay+1)*perBay),width=roomBayW[col];
  const hashes=list.map(b=>[...b.id].reduce((a,c)=>((a*31+c.charCodeAt(0))>>>0),7));
  const widths=hashes.map(h=>coverView?57:10+h%10),total=widths.reduce((a,b)=>a+b,0)+Math.max(0,list.length-1);
  const shrink=Math.min(1,(width-10)/total);
  html+=`<div class="room-bay" style="left:${roomBayX[col]}px;top:${roomShelfY[row]-114}px;width:${width}px" aria-label="Hylle ${bay+1}">`;
  list.forEach((b,i)=>{
   const h=hashes[i],height=coverView?97:87+h%25;
   const lean=i===list.length-1&&list.length<perBay?-3:0;
   html+=roomBookMarkup(b,'',`--w:${widths[i]*shrink}px;--h:${height}px;--lean:${lean}deg`,sort==='custom'&&!selectionMode);
  });html+='</div>';
 }
 host.innerHTML=html+(!filtered.length?'<div class="room-empty">Ingen bøker passer til søket.</div>':'');
 host.querySelectorAll('[data-book]').forEach((el,i)=>{
  const b=books.find(x=>x.id===el.dataset.book);
  el.onmouseenter=()=>roomHover(b);el.onmouseleave=hideRoomHover;el.onfocus=()=>roomHover(b);el.onblur=hideRoomHover;
  el.onclick=()=>{if(roomDragging||moving||bulkBusy)return;hideRoomHover();if(selectionMode){selected.has(b.id)?selected.delete(b.id):selected.add(b.id);render();}else openBook(b.id);};
  el.ondragstart=e=>{roomDragging=true;dragId=b.id;e.dataTransfer.setData('text/plain',b.id);e.dataTransfer.effectAllowed='move';el.classList.add('dragging');hideRoomHover();};
  el.ondragend=()=>{dragId='';setTimeout(()=>roomDragging=false,0);el.classList.remove('dragging');host.querySelectorAll('.drop-target').forEach(x=>x.classList.remove('drop-target'));};
  el.ondragover=e=>{if(!dragId||sort!=='custom'||moving)return;e.preventDefault();e.dataTransfer.dropEffect='move';el.classList.add('drop-target');};
  el.ondragleave=()=>el.classList.remove('drop-target');
  el.ondrop=async e=>{e.preventDefault();if(!dragId||moving)return;const id=dragId;dragId='';el.classList.remove('drop-target');await placeBook(id,b.user_shelf||'',b.id);roomDragging=false;};
  const before=old.get(b.id),after=el.getBoundingClientRect();
  if(!matchMedia('(prefers-reduced-motion: reduce)').matches){
   const dx=before?(before.left-after.left)/roomScale:0,dy=before?(before.top-after.top)/roomScale:-15;
   if(scene!=='library'){
    const a=el.animate([{opacity:0,translate:'0 28px',scale:'.92'},{opacity:1,translate:'0 0',scale:'1'}],{duration:520,delay:(i%10)*28,easing:'cubic-bezier(.22,.7,.2,1)'});
    wallAnimations.push(a);
   }else if(Math.abs(dx)>1||Math.abs(dy)>1){
    el.style.zIndex=25;
    const a=el.animate([{transform:`translate(${dx}px,${dy}px) rotate(0deg)`,opacity:before?1:0},{offset:.35,transform:`translate(${dx*.6}px,${dy*.6-22}px) rotate(${i%2?3:-3}deg)`,opacity:1},{transform:'translate(0,0) rotate(var(--lean))',opacity:1}],{duration:before?1050:650,delay:(i%perBay)*10,easing:'cubic-bezier(.22,.7,.2,1)'});
    a.onfinish=()=>el.style.zIndex='';wallAnimations.push(a);
   }
  }
 });
}
// Keep existing sorting, importing, selection, and book editing actions intact.
$('#view-toggle').onclick=()=>{coverView=!coverView;$('#view-toggle').textContent=coverView?'Vis bokrygger':'Vis omslag';$('#view-toggle').setAttribute('aria-pressed',String(coverView));render();};
