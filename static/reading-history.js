/* Audible evidence is separate from user-entered reading status and dates. */
function audibleCompletions(b){return (b.audible_history||[]).flatMap(h=>h.completions.map(c=>({...c,asin:h.asin,edition:h.title,source:'Audible',estimated:true,book:b})));}
function readingEvents(b){
 const events=audibleCompletions(b);
 // A manual completion in the same year is treated as the same reading unless
 // the user supplied a different exact date. Undated counts remain separate.
 if(b.status==='finished'&&b.year&&!b.year_uncertain&&!events.some(e=>Number(e.date.slice(0,4))===b.year&&(!b.finished_date||e.date===b.finished_date))){
  events.push({book:b,date:b.finished_date||'',year:b.year,estimated:false,source:b.source||'Manuelt',edition:b.title});
 }
 return events.sort((a,b)=>(a.date||a.year+'-00-00').localeCompare(b.date||b.year+'-00-00'));
}
function hasFinishedInYear(b,year){return readingEvents(b).some(e=>Number(e.date.slice(0,4)||e.year)===year);}
function historyDate(d){return d?new Date(d+'T12:00:00').toLocaleDateString('nb-NO'):'Dato ukjent';}
function undatedReadings(b){
 const events=readingEvents(b);const original=b.audible_import_original;
 const supplied=original?((original.status==='finished'||Number(original.read_count)>1)?Number(original.read_count||1):0):((b.status==='finished'||Number(b.read_count)>1)?Number(b.read_count||1):0);
 return Math.max(0,Math.max(supplied,b.status==='finished'?Number(b.read_count||1):0)-events.length);
}
function bookAudiblePanel(b){
 if(!b.audible_history?.length)return '';
 const cs=audibleCompletions(b).sort((a,b)=>a.date.localeCompare(b.date));
 const days=b.audible_history.flatMap(h=>h.days.map(d=>({...d,edition:h.title}))).sort((a,b)=>b.date.localeCompare(a.date));
 return `<section class="audible-evidence"><h3>Lyttehistorikk fra Audible</h3><p>${cs.length} sannsynlige gjennomlyttinger · ${days.length} registrerte lyttedager per utgave</p><p class="muted">Fullføringer og datoer er anslått fra lytteposisjoner. Manglende historikk kan gi for lave antall. Dine manuelle oppføringer beholdes.</p>${cs.length?`<ol>${cs.map(c=>`<li><strong>Ca. ${historyDate(c.date)}</strong> · ${esc(c.edition)}<br><small>${c.coverage.toLocaleString('nb-NO')} % av lydposisjonene dokumentert${c.certainty==='lower'?' · Mer usikkert':''}</small></li>`).join('')}</ol>`:'<p>Ingen tilstrekkelig dokumentert fullføring. Dette betyr ikke nødvendigvis at boka er ulest.</p>'}<details><summary>Alle registrerte lyttedager (${days.length})</summary><div class="history-table-wrap"><table><thead><tr><th>Dato</th><th>Registrert tid</th><th>Nådd posisjon</th></tr></thead><tbody>${days.map(d=>`<tr><td>${historyDate(d.date)}</td><td>${Math.round(d.recorded_hours*60)} min</td><td>${d.position_percent==null?'Ukjent':d.position_percent+' %'}</td></tr>`).join('')}</tbody></table></div></details></section>`;
}
const statsButton=document.createElement('button');statsButton.className='nav';statsButton.id='reading-statistics-button';statsButton.innerHTML='<span>▥</span> Historikk og statistikk';document.querySelector('aside nav').append(statsButton);
const statsDialog=document.createElement('dialog');statsDialog.id='reading-statistics';statsDialog.innerHTML=`<button class="close" aria-label="Lukk statistikk">×</button><div class="dialog-pad"><div class="eyebrow">ALLE LESEÅRENE DINE</div><h2>Historikk og statistikk</h2><p>Audible: 8. november 2015–23. september 2026, sammen med dine manuelle leseoppføringer.</p><div class="stats-controls"><label>Periode<select id="stats-year"><option value="all">Hele historikken</option></select></label><label>Finn en bok<input type="search" id="stats-query" placeholder="Tittel eller forfatter"></label></div><div id="stats-content" aria-live="polite"></div></div>`;document.body.append(statsDialog);statsDialog.querySelector('.close').onclick=()=>statsDialog.close();
function openReadingStatistics(){
 const years=[...new Set(books.flatMap(b=>[...readingEvents(b).map(e=>String(e.year||e.date.slice(0,4))),...(b.audible_history||[]).flatMap(h=>h.days.map(d=>d.date.slice(0,4)))]))].sort().reverse();
 const selected=$('#stats-year').value;$('#stats-year').innerHTML='<option value="all">Hele historikken</option>'+years.map(y=>`<option value="${y}">${y}</option>`).join('');$('#stats-year').value=selected||'all';renderReadingStatistics();statsDialog.showModal();
}
statsButton.onclick=openReadingStatistics;$('#stats-year').onchange=renderReadingStatistics;$('#stats-query').oninput=renderReadingStatistics;
function audibleRereadRanking(chosen){
 const ranked=chosen.map(b=>({b,events:audibleCompletions(b)})).filter(x=>x.events.length>1).sort((a,b)=>b.events.length-a.events.length||a.b.title.localeCompare(b.b.title,'nb'));
 const cutoff=ranked[9]?.events.length||2;
 const leaders=ranked.filter(x=>x.events.length>=cutoff);
 return `<section class="reread-ranking" aria-labelledby="reread-heading"><h3 id="reread-heading">Mest gjenlyttet</h3><p class="muted">Kun Audible · hele historikken 2015–2026, uavhengig av valgt år. Antallet inkluderer første gjennomlytting. Anslått fra lyttehistorikken; påbegynte runder teller ikke.</p>${leaders.length?`<ol class="reread-list">${leaders.map(({b,events},i)=>{const rank=ranked.findIndex(x=>x.events.length===events.length)+1;return `<li><span class="reread-rank" aria-label="Plass ${rank}">${rank}</span><div><button class="history-book" data-history-book="${b.id}">${esc(b.title)}</button><small>${esc(b.author)}</small></div><strong>${events.length}<small>ganger</small></strong></li>`;}).join('')}</ol><p class="muted">${ranked.length} bokkort er gjenlyttet. Topp 10 vises, inkludert alle som deler siste plass. Utgaver på samme bokkort er samlet.</p>`:'<p>Ingen bøker med flere dokumenterte gjennomlyttinger i dette søket.</p>'}</section>`;
}
function renderReadingStatistics(){
 const year=$('#stats-year').value,query=$('#stats-query').value.toLocaleLowerCase('nb');
 const chosen=books.filter(b=>(b.title+' '+b.author).toLocaleLowerCase('nb').includes(query));
 const events=chosen.flatMap(readingEvents).filter(e=>year==='all'||String(e.year||e.date.slice(0,4))===year).sort((a,b)=>(b.date||b.year+'-00-00').localeCompare(a.date||a.year+'-00-00'));
 const days=chosen.flatMap(b=>(b.audible_history||[]).flatMap(h=>h.days)).filter(d=>year==='all'||d.date.startsWith(year));
 const hours=days.reduce((s,d)=>s+d.recorded_hours,0),uncertain=events.filter(e=>e.estimated).length,undated=year==='all'?chosen.reduce((s,b)=>s+undatedReadings(b),0):0;
 const allEvents=chosen.flatMap(readingEvents),years=[...new Set(allEvents.map(e=>String(e.year||e.date.slice(0,4))))].sort().reverse();
 const counts=chosen.map(b=>({b,count:readingEvents(b).filter(e=>year==='all'||String(e.year||e.date.slice(0,4))===year).length+(year==='all'?undatedReadings(b):0)})).filter(x=>x.count).sort((a,b)=>b.count-a.count||a.b.title.localeCompare(b.b.title));
 $('#stats-content').innerHTML=`<div class="reading-metrics"><div><strong>${events.length+undated}</strong><span>gjennomføringer${undated?' inkl. '+undated+' uten kjent år':''}</span></div><div><strong>${counts.length}</strong><span>bokkort / utgaver fullført</span></div><div><strong>${Math.round(hours).toLocaleString('nb-NO')}</strong><span>registrerte timer i Audible</span></div><div><strong>${new Set(days.map(d=>d.date)).size}</strong><span>dager med Audible-lytting</span></div></div><p class="stats-method">${uncertain} av gjennomføringene med kjent år er Audible-anslag. Gjentatt lesing telles hver gang; ulike utgaver kan ha hvert sitt bokkort. Lyttetid inkluderer også påbegynte bøker. Eldre lyttehistorikk har hull, så dette er ikke et sikkert livstidsantall.</p>${audibleRereadRanking(chosen)}${year==='all'?`<details open><summary>Gjennomføringer per år</summary><div class="annual-stats">${years.map(y=>{let n=allEvents.filter(e=>String(e.year||e.date.slice(0,4))===y).length;return `<button data-stats-year="${y}"><strong>${y}</strong><span>${n} gjennomføringer</span></button>`;}).join('')}</div></details>`:''}<details open><summary>Antall ganger per bok</summary><div class="history-table-wrap"><table><thead><tr><th>Bok</th><th>Antall</th><th>Fullføringer</th></tr></thead><tbody>${counts.map(({b,count})=>`<tr><td><button class="history-book" data-history-book="${b.id}">${esc(b.title)}</button><small>${esc(b.author)}</small></td><td>${count}</td><td>${readingEvents(b).filter(e=>year==='all'||String(e.year||e.date.slice(0,4))===year).map(e=>(e.estimated?'ca. ':'')+(e.date?historyDate(e.date):e.year+' (dato ukjent)')).join(' · ')}${year==='all'&&undatedReadings(b)?' · '+undatedReadings(b)+' uten kjent år':''}</td></tr>`).join('')||'<tr><td colspan="3">Ingen fullføringer funnet.</td></tr>'}</tbody></table></div></details><details><summary>Tidslinje – gjennomføringer med kjent år (${events.length})</summary><div class="history-table-wrap"><table><thead><tr><th>Dato</th><th>Bok</th><th>Grunnlag</th></tr></thead><tbody>${events.map(e=>`<tr><td>${e.estimated?'Ca. ':''}${e.date?historyDate(e.date):e.year+' · dato ukjent'}</td><td><button class="history-book" data-history-book="${e.book.id}">${esc(e.book.title)}</button></td><td>${e.estimated?(e.certainty==='lower'?'Audible · mer usikkert':'Audible · anslag'):esc(e.source)}</td></tr>`).join('')}</tbody></table></div></details>`;
 statsDialog.querySelectorAll('[data-stats-year]').forEach(btn=>btn.onclick=()=>{$('#stats-year').value=btn.dataset.statsYear;renderReadingStatistics();});
 statsDialog.querySelectorAll('[data-history-book]').forEach(btn=>btn.onclick=()=>{statsDialog.close();openBook(btn.dataset.historyBook);});
}
const openBookBeforeHistory=openBook;openBook=function(id){openBookBeforeHistory(id);const b=books.find(x=>x.id===id);$('#detail .detail-top').insertAdjacentHTML('afterend',bookAudiblePanel(b));};

load().catch(e=>{$('#shelf').innerHTML='<p>Kunne ikke laste bokhylla. Start appen og last siden på nytt.</p>';toast(e.message);});
