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

// Offline Korean naming layer. This is NOT Papago and is intentionally labeled as provisional.
// Keep Japanese originals and any verified server-provided Korean translation intact.
const KO_WORDS = Object.entries({
 'ジュリア':'쥬리아','じゅりあ':'쥬리아','すばる':'스바루','おとめ':'오토메','ビビ':'비비','ハッピーバースデー':'해피 버스데이','サイリウム':'사이리움','スイート':'스위트','いちご':'딸기',
 'グリーン':'그린','ピンク':'핑크','ブルー':'블루','レッド':'레드','ホワイト':'화이트','ブラック':'블랙',
 'イエロー':'옐로','パープル':'퍼플','オレンジ':'오렌지','ミント':'민트','クリーム':'크림',
 'レインボー':'레인보우','ナイト':'나이트','ローズ':'로즈','リボン':'리본','ハート':'하트',
 'スマイル':'스마일','ピュア':'퓨어','バズリウム':'버즈리움','クリスタル':'크리스털',
 'エレガント':'엘레강트','ゴシック':'고딕','パンプキン':'펌킨','ハロウィン':'할로윈',
 'トランプ':'트럼프','レディ':'레이디','メゾ ピアノ':'메조 피아노','エンジェル':'엔젤',
 'ポップ':'팝','デニム':'데님','メモリアル':'메모리얼','クロック':'클록',
 'テディベア':'테디베어','フリル':'프릴','スポーツ':'스포츠','ピクニック':'피크닉',
 'バスケット':'바스켓','フレッシュ':'프레시','トロピカル':'트로피컬','スクール':'스쿨',
 'チェック':'체크','アンティーク':'앤티크','ラブリー':'러블리','ステージ':'스테이지',
 'デザート':'디저트','フェス':'페스티벌','シャンデリア':'샹들리에','バブル':'버블',
 'ゼリー':'젤리','マーメイド':'머메이드','グランプリ':'그랑프리','ミルキー':'밀키',
 'ロイヤル':'로열','ミステリアス':'미스터리어스','クォーツ':'쿼츠','エプロン':'에이프런',
 'ブーケ':'부케','フレア':'플레어','ジューシー':'주시','サマー':'서머',
 'パステル':'파스텔','パッチワーク':'패치워크','バタフライ':'버터플라이',
 'クレッセント':'크레센트','ムーン':'문','シーサイド':'시사이드','シューティング':'슈팅',
 'スター':'스타','コーデ':'코디','アイプリ':'아이프리','ときめき':'두근두근',
 'ゆめかわ':'꿈결','まほうつかい':'마법사','ぼうし':'모자','とんがり':'뾰족',
 'がくえん':'학원','せいふく':'교복','なつふく':'여름 교복','きぼう':'희망',
 'じょうねつ':'열정','だいすき':'정말 좋아','ナンバーワン':'넘버원',
 'きん':'금빛','ぷるるん':'탱글탱글','うらない':'점술','たれぱんだ':'타레판다',
 'すみっコぐらし':'스밋코구라시','リラックマ':'리락쿠마',
 'センチメンタルサーカス':'센티멘털 서커스','メルティ':'멜티','リリィ':'릴리'
}).sort((a,b)=>b[0].length-a[0].length);
const KANA_ROMA = {'ジャ':'쟈','ジュ':'쥬','ジョ':'죠','ジェ':'제','ジィ':'지','ギャ':'갸','ギュ':'규','ギョ':'교','ビャ':'뱌','ビュ':'뷰','ビョ':'뵤','ピャ':'퍄','ピュ':'퓨','ピョ':'표','キャ':'캬','キュ':'큐','キョ':'쿄','シャ':'샤','シュ':'슈','ショ':'쇼','チャ':'차','チュ':'추','チョ':'초','ニャ':'냐','ニュ':'뉴','ニョ':'뇨','ミャ':'먀','ミュ':'뮤','ミョ':'묘','リャ':'랴','リュ':'류','リョ':'료','ファ':'파','フィ':'피','フェ':'페','フォ':'포','ティ':'티','ディ':'디','ウィ':'위','ウェ':'웨','ウォ':'워',
 'ア':'아','イ':'이','ウ':'우','エ':'에','オ':'오','カ':'카','キ':'키','ク':'쿠','ケ':'케','コ':'코','サ':'사','シ':'시','ス':'스','セ':'세','ソ':'소','タ':'타','チ':'치','ツ':'츠','テ':'테','ト':'토','ナ':'나','ニ':'니','ヌ':'누','ネ':'네','ノ':'노','ハ':'하','ヒ':'히','フ':'후','ヘ':'헤','ホ':'호','マ':'마','ミ':'미','ム':'무','メ':'메','モ':'모','ヤ':'야','ユ':'유','ヨ':'요','ラ':'라','リ':'리','ル':'루','レ':'레','ロ':'로','ワ':'와','ヲ':'오','ン':'ㄴ','ガ':'가','ギ':'기','グ':'구','ゲ':'게','ゴ':'고','ザ':'자','ジ':'지','ズ':'즈','ゼ':'제','ゾ':'조','ダ':'다','ヂ':'지','ヅ':'즈','デ':'데','ド':'도','バ':'바','ビ':'비','ブ':'부','ベ':'베','ボ':'보','パ':'파','ピ':'피','プ':'푸','ペ':'페','ポ':'포','ッ':'','ー':''};
function roughKo(ja){
  let t=ja, placeholders=[];
  for(const [jp,ko] of KO_WORDS){if(t.includes(jp)){const mark=`§${placeholders.length}§`;placeholders.push(ko);t=t.split(jp).join(mark);}}
  t=t.replace(/[ぁ-ゖ]/g,ch=>String.fromCharCode(ch.charCodeAt(0)+96));
  t=t.replace(/[ァ-ヴ][ャュョ]|[ァ-ヴーッン]/g,ch=>KANA_ROMA[ch]??ch);
  t=t.replace(/§(\d+)§/g,(_,i)=>placeholders[Number(i)]);
  return t.replace(/\s+/g,' ').trim();
}
function addKoreanNames(items){for(const x of items){if(x.name_ko)continue;const ko=roughKo(x.name_ja||'');if(ko&&ko!==x.name_ja){x.name_ko=ko;x.translation_source='Draft';}}}

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
function showModal(x){const b=$('#modalBody');b.replaceChildren();const photo=imageEl(x);photo.classList.add('modalphoto');b.append(photo);b.append(el('h2','',x.name_ko||x.name_ja));if(x.name_ko)b.append(el('p','',x.name_ja));else b.append(el('p','', '한국어 이름은 추후 파파고 기준으로 검수됩니다.'));b.append(el('p','',labels[x.series]||x.series));const fav=favoriteButton(x);fav.classList.add('modal-favorite');b.append(fav);const a=el('a','','일본 공식 코디 페이지 보기 ↗');a.href=x.source_url;a.target='_blank';a.rel='noopener noreferrer';b.append(a);$('#modal').hidden=false;$('#closeModal').focus();}
// Exclude only confirmed promotional placeholder cards; preserve actual Birthday color outfits.
const HIDDEN_PROMOTIONAL_NAMES=new Set(['ハッピーバースデー！コーデ']);
const isHiddenPromotional=x=>HIDDEN_PROMOTIONAL_NAMES.has((x.name_ja||'').normalize('NFKC').trim());
function results(){const q=norm(query);let arr=all.filter(x=>!isHiddenPromotional(x)&&(series==='all'||x.series===series)&&(!onlyFavorites||favorites.has(keyOf(x)))&&(!q||norm(x.name_ko).includes(q)||norm(x.name_ja).includes(q)||norm(x.name_ko).replaceAll('쥬','주').includes(q)));
if(sortMode==='az')arr.sort((a,b)=>(a.name_ko||a.name_ja).localeCompare(b.name_ko||b.name_ja,'ko'));else if(sortMode==='za')arr.sort((a,b)=>(b.name_ko||b.name_ja).localeCompare(a.name_ko||a.name_ja,'ko'));return arr;}
function render(){const arr=results();$('#count').textContent=arr.length;$('#favoritesCount').textContent=favorites.size;$('#favoritesOnly').classList.toggle('active',onlyFavorites);$('#favoritesOnly').setAttribute('aria-pressed',String(onlyFavorites));const grid=$('#grid');grid.replaceChildren();$('#empty').hidden=!!arr.length;$('#emptyDescription').textContent=onlyFavorites?'즐겨찾기를 해제하거나 다른 조건으로 검색해 보세요.':'다른 키워드나 일본어 이름으로 검색해 보세요.';
for(const x of arr.slice(0,visible)){const c=el('article','item');c.tabIndex=0;c.setAttribute('role','button');c.setAttribute('aria-label',(x.name_ko||x.name_ja)+' 상세 보기');const p=imageEl(x);p.append(el('span','tag',labels[x.series]||x.series),favoriteButton(x));const t=el('div','itemtext');t.append(el('div','ko',x.name_ko||x.name_ja),el('div','ja',x.name_ko?x.name_ja:'한국어 표기 검토 중'));const foot=el('div','itemfoot');foot.append(el('span','',x.translation_source==='Papago'?'파파고 번역':x.translation_source==='Draft'?'한국어 임시 표기':'공식 일본어명'),el('span','','자세히 ↗'));t.append(foot);c.append(p,t);c.onclick=()=>showModal(x);c.onkeydown=e=>{if(e.target===c&&(e.key==='Enter'||e.key===' ')){e.preventDefault();showModal(x);}};grid.append(c)}
$('#more').hidden=visible>=arr.length;$('#more').textContent=`더 보기 (${Math.min(visible,arr.length)} / ${arr.length})`;}
async function load(){try{
  const res=await fetch('/api/outfits',{cache:'no-store'});if(!res.ok)throw new Error('HTTP '+res.status);
  const d=await res.json();all=(d.items||[]).filter(x=>!isHiddenPromotional(x));addKoreanNames(all);
  // Verified translations override the provisional Korean names.
  try {
    const verifiedResponse=await fetch('/static/papago_verified.json?v=2',{cache:'no-store'});
    if(verifiedResponse.ok){
      const dictionary=await verifiedResponse.json();
      for(const x of all){
        const record=dictionary[x.name_ja];
        if(record && record.verified===true && typeof record.ko==='string' && record.ko.trim()){
          x.name_ko=record.ko.trim();
          x.translation_source='Papago verified';
        }
      }
    }
  }catch(error){console.warn('Verified translations unavailable',error);}
  render();
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
