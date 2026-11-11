const $=s=>document.querySelector(s);
const labels={oa4:'오네가이 4탄',oa3:'오네가이 3탄',oa2:'오네가이 2탄',oa1:'오네가이 1탄',special:'스페셜',...Object.fromEntries(Array.from({length:6},(_,i)=>[`ring${i+1}`,`링 ${i+1}탄`])),...Object.fromEntries(Array.from({length:6},(_,i)=>[`${i+1}`,`아이프리 ${i+1}탄`]))};
let all=[],series='all',query='',onlyFavorites=false,sortMode='latest',visible=40;
let imagePolls=0, imagePollTimer=null;
const STORAGE='aipri-favorites-v1';
let favorites=new Set();try{favorites=new Set(JSON.parse(localStorage.getItem(STORAGE)||'[]'));}catch{}
const saveFavorites=()=>{try{localStorage.setItem(STORAGE,JSON.stringify([...favorites]));}catch{}};
const keyOf=x=>`${x.series}|${x.name_ja}`;
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function norm(s){return (s||'').normalize('NFKC').replace(/\s/g,'').toLocaleLowerCase();}
function imageEl(x){
  const p=el('div','photo');
  if(x.image_url){
    const im=el('img'); im.loading='lazy'; im.alt=x.name_ja;
    // The server checks actual image dimensions and refuses wide title banners.
    im.src='/api/image/'+encodeURIComponent(x.id);
    im.onerror=async()=>{
      im.remove();
      // Only remove the entire card when the server has confirmed a wide banner.
      // A broken/blocked image is not proof that the outfit is promotional.
      try {
        const r=await fetch('/api/image/'+encodeURIComponent(x.id),{cache:'no-store'});
        if(r.status===410){
          const card=p.closest('.item');
          if(card){card.remove();return;}
        }
      } catch {}
      p.prepend(el('div','placeholder','✦'));
    };
    p.append(im);
  }else p.append(el('div','placeholder','✦'));
  return p;
}
function toggleFavorite(x){const k=keyOf(x);favorites.has(k)?favorites.delete(k):favorites.add(k);saveFavorites();render();}
function favoriteButton(x){const liked=favorites.has(keyOf(x));const b=el('button',`heart ${liked?'liked':''}`,liked?'♥':'♡');b.type='button';b.title=liked?'즐겨찾기 해제':'즐겨찾기 추가';b.setAttribute('aria-label',b.title);b.setAttribute('aria-pressed',String(liked));b.onclick=e=>{e.stopPropagation();toggleFavorite(x)};return b;}
function showModal(x){const b=$('#modalBody');b.replaceChildren();const photo=imageEl(x);photo.classList.add('modalphoto');b.append(photo);b.append(el('h2','',x.name_ko||x.name_ja));if(x.name_ko)b.append(el('p','',x.name_ja));else b.append(el('p','', '한국어 이름은 파파고 번역 등록 후 제공됩니다.'));b.append(el('p','',labels[x.series]||x.series));const fav=favoriteButton(x);fav.classList.add('modal-favorite');b.append(fav);const a=el('a','','일본 공식 코디 페이지 보기 ↗');a.href=x.source_url;a.target='_blank';a.rel='noopener noreferrer';b.append(a);$('#modal').hidden=false;$('#closeModal').focus();}
// Exclude only confirmed promotional placeholder cards; preserve actual Birthday color outfits.
const HIDDEN_PROMOTIONAL_NAMES=new Set(['ハッピーバースデー！コーデ']);
const isHiddenPromotional=x=>HIDDEN_PROMOTIONAL_NAMES.has((x.name_ja||'').normalize('NFKC').trim());
function results(){const q=norm(query);let arr=all.filter(x=>!isHiddenPromotional(x)&&(series==='all'||x.series===series)&&(!onlyFavorites||favorites.has(keyOf(x)))&&(!q||norm(x.name_ko).includes(q)||norm(x.name_ja).includes(q)));
if(sortMode==='az')arr.sort((a,b)=>(a.name_ko||a.name_ja).localeCompare(b.name_ko||b.name_ja,'ko'));else if(sortMode==='za')arr.sort((a,b)=>(b.name_ko||b.name_ja).localeCompare(a.name_ko||a.name_ja,'ko'));return arr;}
function render(){const arr=results();$('#count').textContent=arr.length;$('#favoritesCount').textContent=favorites.size;$('#favoritesOnly').classList.toggle('active',onlyFavorites);$('#favoritesOnly').setAttribute('aria-pressed',String(onlyFavorites));const grid=$('#grid');grid.replaceChildren();$('#empty').hidden=!!arr.length;$('#emptyDescription').textContent=onlyFavorites?'즐겨찾기를 해제하거나 다른 조건으로 검색해 보세요.':'다른 키워드나 일본어 이름으로 검색해 보세요.';
for(const x of arr.slice(0,visible)){const c=el('article','item');c.tabIndex=0;c.setAttribute('role','button');c.setAttribute('aria-label',(x.name_ko||x.name_ja)+' 상세 보기');const p=imageEl(x);p.append(el('span','tag',labels[x.series]||x.series),favoriteButton(x));const t=el('div','itemtext');t.append(el('div','ko',x.name_ko||x.name_ja),el('div','ja',x.name_ko?x.name_ja:'한국어 번역 미등록'));const foot=el('div','itemfoot');foot.append(el('span','',x.translation_source==='Papago'?'파파고 번역':'공식 일본어명'),el('span','','자세히 ↗'));t.append(foot);c.append(p,t);c.onclick=()=>showModal(x);c.onkeydown=e=>{if(e.target===c&&(e.key==='Enter'||e.key===' ')){e.preventDefault();showModal(x);}};grid.append(c)}
$('#more').hidden=visible>=arr.length;$('#more').textContent=`더 보기 (${Math.min(visible,arr.length)} / ${arr.length})`;}
async function load(){try{
  const res=await fetch('/api/outfits',{cache:'no-store'});if(!res.ok)throw new Error('HTTP '+res.status);
  const d=await res.json();all=(d.items||[]).filter(x=>!isHiddenPromotional(x));render();
  const withImages=all.filter(x=>x.image_url).length;
  const busy=Boolean(d.status?.running);
  $('#notice').textContent=all.length
    ? (busy ? `공식 코디 이미지를 불러오는 중이에요 (${withImages}/${all.length}개 연결). 잠시 후 자동 갱신됩니다.` : `일본어 코디명과 등록된 한국어명으로 검색할 수 있어요. 이미지 연결 ${withImages}/${all.length}개.`)
    : '코디 데이터를 아직 등록하지 못했어요.';
  if(busy && imagePolls<24){
    imagePolls++;
    clearTimeout(imagePollTimer);
    imagePollTimer=setTimeout(load,5000);
  }
}catch{$('#notice').textContent='검색 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.';}}
$('#query').addEventListener('input',e=>{query=e.target.value.trim();visible=40;render();});$('#searchbtn').onclick=()=>{query=$('#query').value.trim();visible=40;render();};$('#clear').onclick=()=>{$('#query').value='';query='';visible=40;render();$('#query').focus();};document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{$('#query').value=b.dataset.q;query=b.dataset.q;visible=40;render();});
$('#chips').onclick=e=>{const b=e.target.closest('[data-series]');if(!b)return;series=b.dataset.series;visible=40;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));$('#series').value=series;render();};
const select=$('#series');for(const [id,name] of Object.entries(labels)){const o=el('option','',name);o.value=id;select.append(o);}select.onchange=()=>{series=select.value;visible=40;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x.dataset.series===series));render();};
$('#favoritesOnly').onclick=()=>{onlyFavorites=!onlyFavorites;visible=40;render()};$('#sort').onchange=e=>{sortMode=e.target.value;render()};$('#more').onclick=()=>{visible+=40;render()};
function closeModal(){$('#modal').hidden=true;}
$('#closeShade').onclick=$('#closeModal').onclick=closeModal;document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});load();
