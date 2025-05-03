// DEBUG: duplicar console.log en pantalla
(function(){
  const orig = console.log;
  document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('debug-log');
    console.log = (...args) => {
      orig.apply(console, args);
      const div = document.createElement('div'),
            txt = args.map(a=>typeof a==='object'?JSON.stringify(a):a).join(' ');
      div.textContent = txt; panel.appendChild(div);
      panel.scrollTop = panel.scrollHeight;
    };
    console.log('[DEBUG] panel iniciado');
  });
})();

document.addEventListener('DOMContentLoaded', ()=>{
  console.log('[INIT] inicio principal');
  runIntro();
});

function runIntro(){
  console.log('[INTRO] cargando lista de categorías');
  // mostramos sólo fondo amarillo 1s
  const introImg = document.getElementById('intro-img'),
        intro = document.getElementById('intro');
  introImg.src = ''; // no hero-image fijo
  setTimeout(()=>{
    console.log('[INTRO] ocultando intro');
    intro.style.transition='opacity 1s'; intro.style.opacity='0';
    setTimeout(()=>{
      intro.remove();
      loadCategories();
    },1000);
  },1000);
}

function loadCategories(){
  console.log('[CAT] fetch /fotos/');
  fetch('fotos/')
    .then(r=>{
      console.log('[CAT] status',r.status);
      return r.text();
    })
    .then(txt=>{
      const doc=new DOMParser().parseFromString(txt,'text/html'),
            links=Array.from(doc.querySelectorAll('a'))
                   .map(a=>a.getAttribute('href'))
                   .filter(h=>h.endsWith('/'));
      console.log('[CAT] carpetas encontradas:',links);
      buildCategoryList(links);
    })
    .catch(e=>console.log('[CAT][ERROR]',e));
}

function buildCategoryList(cats){
  const container=document.getElementById('categories');
  const ul=document.getElementById('cat-list');
  cats.forEach(cat=>{
    const li=document.createElement('li');
    const name=cat.replace(/\/$/,'');
    li.innerHTML=`<span>${name}</span>`;
    li.onclick=()=>enterCategory(name);
    ul.appendChild(li);
  });
  container.classList.remove('hidden');
  console.log('[CAT] lista renderizada');
}

function enterCategory(name){
  console.log('[CAT] entrando en',name);
  document.getElementById('categories').classList.add('hidden');
  const view=document.getElementById('category-view');
  view.classList.remove('hidden');
  document.getElementById('back-btn').onclick=()=>{
    view.classList.add('hidden');
    document.getElementById('cat-list').innerHTML='';
    loadCategories();
  };
  categoryCinematic(name);
}

function categoryCinematic(cat){
  const url = `fotos/${cat}/`;
  console.log('[CINEMA] fetch imágenes de',url);
  fetch(url)
    .then(r=>r.text())
    .then(txt=>{
      const doc=new DOMParser().parseFromString(txt,'text/html'),
            imgs=Array.from(doc.querySelectorAll('a'))
                  .map(a=>a.getAttribute('href'))
                  .filter(h=>/\.(jpe?g|png|gif)$/i.test(h));
      console.log('[CINEMA] imágenes:',imgs);
      showCoverflow(url,imgs);
    });
}

function showCoverflow(base,imgs){
  const cf=document.getElementById('coverflow');
  cf.innerHTML='';
  // crear coverflow
  imgs.forEach((src,i)=>{
    const div=document.createElement('div');
    div.className='cflow-item';
    div.style.backgroundImage=`url('${base+src}')`;
    // rotación inicial
    const angle = (i - (imgs.length-1)/2) * 15;
    div.style.transform=`rotateY(${angle}deg) translateZ(200px)`;
    cf.appendChild(div);
  });
  console.log('[CINEMA] coverflow listo');
  // tras 2s, animar a apilar
  setTimeout(()=>{
    console.log('[CINEMA] animando apilado');
    Array.from(cf.children).forEach((el,i)=>{
      el.style.transform = `translateX(50vw) translateY(${i*2}px) scale(.8)`;
      el.style.opacity = i === 0 ? '1' : '0.8';
    });
    // luego activamos scroll lateral
    setTimeout(()=>initHorizontalScroll(base,imgs),1200);
  },2000);
}

function initHorizontalScroll(base,imgs){
  console.log('[SCROLL] inicializando galería lateral');
  document.getElementById('coverflow').classList.add('hidden');
  const hg = document.getElementById('h-gallery');
  hg.innerHTML='';
  imgs.forEach(src=>{
    const div=document.createElement('div');
    div.className='h-item';
    div.style.backgroundImage=`url('${base+src}')`;
    hg.appendChild(div);
  });
  hg.classList.remove('hidden');
  // mapear scrollY → translateX
  window.addEventListener('wheel', e=>{
    const delta = e.deltaY;
    const cur = getTranslateX(hg) - delta;
    const max = hg.scrollWidth - window.innerWidth;
    const x = Math.max(-max, Math.min(0, cur));
    hg.style.transform = `translateX(${x}px)`;
  }, {passive:true});
  console.log('[SCROLL] listo: usa la rueda para navegar');
}

// helper
function getTranslateX(el){
  const st = window.getComputedStyle(el);
  const m = st.transform.match(/matrix.*\((.+)\)/);
  if(!m) return 0;
  const vals = m[1].split(', ');
  return parseFloat(vals[4]);
}
