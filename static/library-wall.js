let coverView=false,wallAnimations=[],dragId='',moving=false,resizeTimer;
const colorNames=['Rubin og kobber','Rav og gull','Mose og oliven','Smaragd og petrol','Blekk og indigo','Plomme og fiolett'];
function spineStyle(b){
 const hash=[...b.id].reduce((a,c)=>a+c.charCodeAt(0),0);
 const bg=/^#[0-9a-f]{6}$/i.test(b.cover_color||'')?b.cover_color:colors[hash%colors.length][0];
 const rgb=bg.slice(1).match(/../g).map(x=>parseInt(x,16));
 const light=(.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2])>145;
 return {bg,fg:light?'#251c12':'#f7edd3',width:48+hash%24,height:180+hash%51};
}
function colorGroup(b){if(b.cover_hue==null)return 'Uten omslagsfarge';if(b.cover_saturation<.12)return 'Sølv og kull';return colorNames[Math.min(5,Math.floor(b.cover_hue/60))];}
function groupLabel(b,sort){
 if(sort==='author')return b.author.replace(/George R\.R\. Martin/g,'George R. R. Martin').replace(/Brandon\s*,\s*Sanderson/g,'Brandon Sanderson').replace(/Ravens Dagger/g,'Ravensdagger');
 if(sort==='series')return b.series||'Uten serie';
 if(sort==='genre')return b.genre||'Uavklart sjanger';
 if(sort==='custom')return b.user_shelf||'Ikke plassert';
 if(sort==='color')return colorGroup(b);
 return 'A–Å';
}
function compareBooks(a,b,sort){
 const coll=(x,y)=>String(x).localeCompare(String(y),'nb',{numeric:true});
 if(sort==='title')return coll(a.title,b.title);
 if(sort==='color'){const groups=[...colorNames,'Sølv og kull','Uten omslagsfarge'];return groups.indexOf(colorGroup(a))-groups.indexOf(colorGroup(b))||(a.cover_hue??999)-(b.cover_hue??999)||coll(a.title,b.title);}
 if(sort==='custom'){
  const shelves=[...arrangement.shelves,...new Set(books.map(x=>x.user_shelf).filter(Boolean)),'Ikke plassert'];
  const pos=x=>{let n=arrangement.order.indexOf(x.id);return n<0?100000+books.indexOf(x):n;};
  return shelves.indexOf(groupLabel(a,sort))-shelves.indexOf(groupLabel(b,sort))||pos(a)-pos(b);
 }
 return coll(groupLabel(a,sort),groupLabel(b,sort))||(sort==='series'?(a.series_index??999)-(b.series_index??999):0)||coll(a.title,b.title);
}
function renderLegacyWall(filtered){
 const host=$('#shelf'),old=new Map();
 host.querySelectorAll('[data-book]').forEach(el=>old.set(el.dataset.book,el.getBoundingClientRect()));
 wallAnimations.forEach(a=>a.cancel());wallAnimations=[];
 const sort=$('#sort').value;filtered.sort((a,b)=>compareBooks(a,b,sort));visibleIds=filtered.map(b=>b.id);
 $('#result-count').textContent=filtered.length+(filtered.length===1?' bok':' bøker');
 const descriptions={author:'Samlet etter forfatter',title:'Fra A til Å',series:'Samlet i serier · nummerert der vi vet rekkefølgen',genre:'Sjanger fra bokmetadata · kan endres på bokkortet',color:'Fargene er hentet fra omslagene',custom:'Dra bøker mellom hyller · rekkefølgen lagres på Mac-en'};
 $('#arrange-description').textContent=descriptions[sort];
 host.classList.toggle('covers-view',coverView);host.classList.toggle('manual-order',sort==='custom');
 const groups=new Map();
 if(sort==='custom')arrangement.shelves.forEach(s=>groups.set(s,[]));
 filtered.forEach(b=>{let label=groupLabel(b,sort);if(!groups.has(label))groups.set(label,[]);groups.get(label).push(b);});
 let html='';
 const capacity=Math.max(2,Math.floor((host.clientWidth-48)/(coverView?142:70)));
 for(const [name,list] of groups){
  html+=`<section class="shelf-group" data-shelf="${esc(name)}"><div class="shelf-label"><h3>${esc(name)}</h3><span>${list.length} ${list.length===1?'bok':'bøker'}</span></div>`;
  if(!list.length)html+='<div class="shelf-row empty-shelf">Dra en bok hit, eller velg hyllen på bokkortet.</div>';
  for(let i=0;i<list.length;i+=capacity){
   html+='<div class="shelf-row">';
   for(const b of list.slice(i,i+capacity)){
    const s=spineStyle(b);
    html+=`<button class="book volume ${selected.has(b.id)&&selectionMode?'selected':''}" data-book="${b.id}" ${sort==='custom'&&!selectionMode?'draggable="true"':''} ${selectionMode?`aria-pressed="${selected.has(b.id)}"`:''} aria-label="${selectionMode?'Marker':'Åpne'} ${esc(b.title)}" style="--spine:${s.bg};--letter:${s.fg};--book-width:${s.width}px;--book-height:${s.height}px">${selectionMode?`<span class="selection-mark">${selected.has(b.id)?'✓':''}</span>`:''}<span class="spine"><span class="spine-author">${esc(b.author)}</span><span class="spine-title">${esc(b.title)}</span><span class="spine-foot">${b.series_index!=null?esc(b.series_index):'◆'}</span></span><span class="face">${cover(b)}</span><span class="book-peek"><strong>${esc(b.title)}</strong><span>${esc(b.author)}</span><span>${esc(statusNames[b.status])} · ${esc(progress(b))}</span></span></button>`;
   }
   html+='</div>';
  }
  html+='</section>';
 }
 host.innerHTML=html||'<div class="empty">Ingen bøker passer til dette søket.</div>';
 host.querySelectorAll('[data-book]').forEach((el,i)=>{
  el.onclick=()=>{if(moving||bulkBusy)return;if(selectionMode){let id=el.dataset.book;selected.has(id)?selected.delete(id):selected.add(id);render();}else openBook(el.dataset.book);};
  el.ondragstart=e=>{dragId=el.dataset.book;e.dataTransfer.setData('text/plain',dragId);e.dataTransfer.effectAllowed='move';el.classList.add('dragging');};
  el.ondragend=()=>{dragId='';el.classList.remove('dragging');host.querySelectorAll('.drop-target').forEach(x=>x.classList.remove('drop-target'));};
  const before=old.get(el.dataset.book),after=el.getBoundingClientRect();
  if(before&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
   const dx=before.left-after.left,dy=before.top-after.top;
   if((Math.abs(dx)>1||Math.abs(dy)>1)&&((before.bottom>0&&before.top<innerHeight)||(after.bottom>0&&after.top<innerHeight))){
    el.style.zIndex=30;
    const animation=el.animate([{transform:`translate(${dx}px,${dy}px) rotate(0deg)`},{offset:.22,transform:`translate(${dx*.9}px,${dy*.9-24}px) rotate(${i%2?2:-2}deg)`},{offset:.88,transform:'translate(0,-5px) rotate(0)'},{transform:'translate(0,0) rotate(0)'}],{duration:800,delay:(i%9)*22,easing:'cubic-bezier(.22,.65,.25,1)'});
    animation.onfinish=()=>{el.style.zIndex='';};wallAnimations.push(animation);
   }
  }
 });
 host.querySelectorAll('.shelf-group').forEach(group=>{
  group.ondragover=e=>{if(sort!=='custom'||!dragId||moving)return;e.preventDefault();e.dataTransfer.dropEffect='move';group.classList.add('drop-target');};
  group.ondragleave=e=>{if(!group.contains(e.relatedTarget))group.classList.remove('drop-target');};
  group.ondrop=async e=>{e.preventDefault();if(!dragId||moving)return;const target=e.target.closest('[data-book]');await placeBook(dragId,group.dataset.shelf==='Ikke plassert'?'':group.dataset.shelf,target?.dataset.book);dragId='';};
 });
}
async function changeArrangement(){
 const sort=$('#sort').value;render();
 try{arrangement=await api('/api/arrangement',{sort});}catch(e){toast(e.message);}
}
function fullOrder(){return [...new Set([...arrangement.order.filter(id=>books.some(b=>b.id===id)),...books.map(b=>b.id)])];}
async function placeBook(id,shelf,beforeId){
 if(id===beforeId)return;
 moving=true;
 try{
  let order=fullOrder().filter(x=>x!==id),at=beforeId?order.indexOf(beforeId):-1;
  if(at<0)order.push(id);else order.splice(at,0,id);
  // One transaction saves both the shelf and the order.
  arrangement=await api('/api/place',{id,shelf,order});
  books.find(b=>b.id===id).user_shelf=shelf;render();toast('Plasseringen er lagret');
 }catch(e){toast(e.message);}finally{moving=false;}
}
async function moveBookBy(id,delta){
 const b=books.find(b=>b.id===id),same=books.filter(x=>(x.user_shelf||'')===(b.user_shelf||'')).sort((a,b)=>compareBooks(a,b,'custom'));
 const at=same.findIndex(x=>x.id===id),next=at+delta;
 if(next<0||next>=same.length){toast('Boka er allerede ytterst på hyllen');return;}
 const order=fullOrder(),a=order.indexOf(id),z=order.indexOf(same[next].id);[order[a],order[z]]=[order[z],order[a]];
 try{arrangement=await api('/api/arrangement',{order,sort:'custom'});$('#sort').value='custom';render();toast('Rekkefølgen er lagret');}catch(e){toast(e.message);}
}
$('#new-shelf').onclick=()=>$('#shelf-dialog').showModal();
$('#shelf-form').onsubmit=async e=>{e.preventDefault();let name=new FormData(e.target).get('name').trim();if(!name)return;try{arrangement=await api('/api/arrangement',{shelves:[...arrangement.shelves,name],sort:'custom'});$('#sort').value='custom';$('#shelf-dialog').close();e.target.reset();render();toast('Hyllen er opprettet');}catch(e){toast(e.message);}};
$('#view-toggle').onclick=()=>{coverView=!coverView;$('#view-toggle').textContent=coverView?'Vis bokrygger':'Vis omslag';$('#view-toggle').setAttribute('aria-pressed',String(coverView));render();};
window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,180);});
