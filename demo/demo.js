/* Static copy for GitHub Pages: answers the app's /api calls from library.json.
   Sorting and shelf placement work for the visitor's session; book edits and
   imports are turned off because there is no server behind the page. */
(()=>{
 const realFetch=window.fetch.bind(window);
 const readOnly='Dette er en visningskopi. Endringer lagres bare i den lokale appen.';
 let library=null;
 const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
 async function load(){
  if(!library){library=await realFetch('library.json').then(r=>r.json());library.arrangement={order:[],shelves:[],sort:'author',...library.arrangement};}
  return library;
 }
 window.fetch=async(input,opts={})=>{
  const path=typeof input==='string'?input:input.url;
  if(!path.startsWith('/api/'))return realFetch(input,opts);
  const lib=await load(),body=opts.body&&typeof opts.body==='string'?JSON.parse(opts.body):{};
  if(path==='/api/library')return json({books:lib.books,arrangement:lib.arrangement,token:'demo',year:2026,calibre:null});
  if(path.startsWith('/api/history/'))return json([]);
  if(path==='/api/arrangement'){Object.assign(lib.arrangement,body);return json(lib.arrangement);}
  if(path==='/api/place'){
   lib.arrangement.order=body.order;
   if(body.shelf&&!lib.arrangement.shelves.includes(body.shelf))lib.arrangement.shelves.push(body.shelf);
   const b=lib.books.find(b=>b.id===body.id);if(b)b.user_shelf=body.shelf;
   return json(lib.arrangement);
  }
  return json({error:readOnly},403);
 };
 document.addEventListener('DOMContentLoaded',()=>{
  for(const id of ['import-button','add-button','export-button']){const el=document.getElementById(id);if(el)el.hidden=true;}
  const note=document.querySelector('.aside-bottom');
  if(note)note.innerHTML='<span class="online-dot"></span> Visningskopi<br><small>Kode: <a href="https://github.com/espenbjork/bokhylla">github.com/espenbjork/bokhylla</a></small>';
 });
})();
