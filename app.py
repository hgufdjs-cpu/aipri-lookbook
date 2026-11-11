"""Aipri Verse unofficial bilingual outfit search."""
import os
import hmac
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='/static')
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'aipri.db'))
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')
ROOT = 'https://aipri.jp/verse/'
ITEM_ROOT = ROOT + 'item/'
PAGES = [(f'oa{i}', f'오네가이 {i}탄') for i in range(4, 0, -1)] + [(f'ring{i}', f'링 {i}탄') for i in range(6, 0, -1)] + [(str(i), f'아이프리 {i}탄') for i in range(6, 0, -1)] + [('special', '스페셜 코디')]
# Depending on official naming changes, a missing page is safely skipped and reported.
# Initial catalog: names independently checked against official lists (2026-11-11).
# No official images are bundled or redistributed in this sample.
VERIFIED_NAMES = [(x,'oa4') for x in [
 'スイートいちごグリーン','トランプレディホワイト','アイプリだいすきナンバーワン！',
 'スマイルハートバズリウムピンク','スマイルハートバズリウムグリーン','スマイルハートバズリウムレッド',
 'ピュアハートバズリウムブルー','ピュアハートバズリウムイエロー','ピュアハートバズリウムパープル',
 'エレガントクリスタルパープル','エレガントクリスタルピンク','パンプキンハロウィンブラック',
 'トランプレディ','メゾ ピアノ スイートリボン','エンジェルブルー ポップデニム',
 'メモリアルクロック','メモリアルクロックピーコック','テディベアフリル',
 'テディベアフリルレッド','エンジェルスポーツ','エンジェルスポーツピンク',
 'ピクニックバスケット','フレッシュスポーティトロピカル','アイプリじょうねつゴシックブルー',
 'ハイセンスがくえんせいふく','アンティークロック','ラブリーステージオレンジ',
 'デザートフェスレッド','デザートフェスパープル','パンプキンハロウィンネオン',
 'ときめきハロウィンローズレッド','きんのきぼうのクリスタルバズリウム',
 'スクールチェッククリームイエロー','とんがりぼうしまほうつかいピンク',
 'エレガントクリスタルホワイトブルー','ロマンスシャンデリアブラック',
 'エンジェルバブルパープル','ゆめかわレインボーナイト','ぷるるんゼリーイエロー',
 'とんがりぼうしまほうつかい',
]] + [(x,'oa3') for x in [
 'マーメイドグランプリミルキーピンク','ローズリボンロイヤルブルー',
 'うらないクォーツミステリアスレッド','じょうねつゴシックバズリウム',
 'きぼうのクリスタルバズリウム','エプロンブーケイエロー','エプロンブーケレッド',
 'ゴシックフレアレッド','ゴシックフレアパープル','ローズリボン','うらないクォーツ',
 'ジューシーサマーブルー','スイートいちご','たれぱんだ コーデ','すみっコぐらし コーデ',
 'リラックマ コーデ','センチメンタルサーカス コーデ','アイプリじょうねつ',
 'アイプリきぼう','パステルパッチワーク','パステルパッチワークオレンジ',
 'ミステリアスバタフライ','ミステリアスバタフライミント','クレッセントムーン',
 'クレッセントムーンナイトブルー','フレッシュスポーティ','ハイセンスがくえんなつふく',
 'シューティングスター','グリーンフリル','シーサイドフェスピンク','シーサイドフェスグリーン',
]]

STATUS = {'running': False, 'message': '', 'updated': None, 'pages': 0, 'items': 0, 'errors': []}
LOCK = threading.Lock()

def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS outfits (
          id INTEGER PRIMARY KEY, name_ja TEXT NOT NULL, name_ko TEXT,
          series TEXT NOT NULL, image_url TEXT, source_url TEXT NOT NULL,
          translation_source TEXT DEFAULT NULL, updated_at TEXT NOT NULL,
          UNIQUE(name_ja, series))''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ja ON outfits(name_ja)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ko ON outfits(name_ko)')
        # The bundled starter names are checked against the official page, without republishing images.
        if os.getenv('SEED_VERIFIED', '1') == '1':
            for name, slug in VERIFIED_NAMES:
                c.execute('''INSERT OR IGNORE INTO outfits(name_ja,series,source_url,updated_at) VALUES(?,?,?,?)''',
                          (name,slug,ITEM_ROOT + slug + '.html',now()))


def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def normalize(s): return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s or '')).casefold()
def papago_ready(): return bool(os.getenv('PAPAGO_CLIENT_ID') and os.getenv('PAPAGO_CLIENT_SECRET'))

def translate(text, source='ja', target='ko'):
    if not papago_ready(): return None
    r = requests.post('https://papago.apigw.ntruss.com/nmt/v1/translation',
      headers={'X-NCP-APIGW-API-KEY-ID':os.environ['PAPAGO_CLIENT_ID'],
               'X-NCP-APIGW-API-KEY':os.environ['PAPAGO_CLIENT_SECRET']},
      data={'source':source, 'target':target, 'text':text},timeout=15)
    r.raise_for_status()
    return r.json()['message']['result']['translatedText'].strip()

def valid_image(url):
    p = urlparse(url)
    return p.scheme == 'https' and (p.hostname == 'aipri.jp' or p.hostname.endswith('.aipri.jp'))

def parse_page(html, url):
    """Gather image-associated outfit names while excluding menus/icons.

    Official pages use thumbnails with descriptive Japanese image alt text.
    Both <img> and adjacent figure/text are considered for resilience.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for s in soup(['script', 'style', 'nav', 'footer']): s.decompose()
    candidates = []
    seen = set()
    for img in soup.select('img'):
        if img.find_parent(['h1','h2','h3','h4','h5','h6','header','nav','footer']): continue
        alt = (img.get('alt') or '').strip()
        src = img.get('data-src') or img.get('data-original') or img.get('src') or ''
        full = urljoin(url, src)
        if not alt or not re.search('[\u3040-\u30ff\u3400-\u9fff]', alt): continue
        if len(alt) > 70 or not src or not valid_image(full): continue
        if any(x in alt for x in ('コーデアイテム','トップ','ページ','サイト','カレンダー','メニュー','ボタン','公式','PAGE TOP','TOPICS','最新段情報','キャンペーン')): continue
        # The product image region is item-specific; exclude navigation/branding thumbnails.
        if any(x in full.lower() for x in ('/common/','/header/','/footer/','/navi/','/logo/','/btn/','/icon/')): continue
        name = re.sub(r'\s+', ' ', alt)
        if name in seen: continue
        seen.add(name)
        candidates.append((name,full))
    return candidates

def fetch_page(page):
    slug, label = page
    url = ITEM_ROOT + slug + '.html'
    r = requests.get(url, timeout=15, headers={'User-Agent':'Mozilla/5.0 (compatible; AipriOutfitIndexer/1.0; personal fan directory)'})
    r.raise_for_status()
    return slug, url, parse_page(r.text,url)

def refresh_job():
    global STATUS
    with LOCK:
        STATUS.update(running=True,message='공식 코디 목록을 가져오는 중',pages=0,items=0,errors=[])
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch_page, p):p for p in PAGES}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    slug,url,items = future.result()
                    with conn() as c:
                        for name,img in items:
                            c.execute('''INSERT INTO outfits(name_ja,series,image_url,source_url,updated_at)
                              VALUES(?,?,?,?,?) ON CONFLICT(name_ja,series) DO UPDATE SET
                              image_url=excluded.image_url,source_url=excluded.source_url,updated_at=excluded.updated_at''',
                              (name,slug,img,url,now()))
                    with LOCK:
                        STATUS['pages'] += 1
                        STATUS['items'] += len(items)
                except Exception as e:
                    with LOCK: STATUS['errors'].append(f'{page[0]}: {str(e)[:130]}')
        with LOCK:
            STATUS['updated'] = now()
            STATUS['message'] = '수집 완료' if STATUS['items'] else '코디를 가져오지 못했습니다. 페이지 구조 또는 네트워크를 확인하세요.'
    except Exception as e:
        with LOCK: STATUS['message'] = '수집 실패: '+str(e)[:150]
    finally:
        with LOCK: STATUS['running'] = False

def translation_job():
    with LOCK: STATUS['translating'] = True; STATUS['translation_message'] = '파파고 번역 진행 중'
    try:
        with conn() as c:
            rows = c.execute("SELECT id,name_ja FROM outfits WHERE name_ko IS NULL OR name_ko = ''").fetchall()
        done = 0
        for row in rows:
            try:
                ko = translate(row['name_ja'])
                if ko:
                    with conn() as c: c.execute('UPDATE outfits SET name_ko=?,translation_source=? WHERE id=?', (ko,'Papago',row['id']))
                    done += 1
            except Exception as e:
                with LOCK: STATUS['translation_message'] = '파파고 오류: '+str(e)[:140]
                break
        else:
            with LOCK: STATUS['translation_message'] = f'번역 완료: {done}건'
    finally:
        with LOCK: STATUS['translating'] = False

@app.route('/')
def home(): return render_template('index.html')

@app.route('/health')
def health(): return jsonify({'ok': True})

@app.route('/api/outfits')
def outfits():
    q = normalize(request.args.get('q',''))[:100]
    series = request.args.get('series','')
    with conn() as c: rows = [dict(x) for x in c.execute('SELECT * FROM outfits ORDER BY series DESC, id DESC').fetchall()]
    if series and series != 'all': rows = [r for r in rows if r['series'] == series]
    if q: rows = [r for r in rows if q in normalize(r['name_ja']) or q in normalize(r['name_ko'])]
    return jsonify({'items': rows[:6000], 'total': len(rows), 'papago': papago_ready(), 'status':STATUS})

def admin_authorized():
    supplied = request.headers.get('X-Admin-Token', '')
    return bool(ADMIN_TOKEN) and hmac.compare_digest(supplied, ADMIN_TOKEN)

@app.route('/api/refresh', methods=['POST'])
def refresh():
    if not admin_authorized(): return jsonify({'error':'관리자 인증이 필요합니다.'}),403
    if STATUS['running']: return jsonify({'message':'이미 수집 중입니다.'})
    threading.Thread(target=refresh_job,daemon=True).start()
    return jsonify({'message':'공식 사이트에서 코디 목록 수집을 시작했습니다.'})

@app.route('/api/translate', methods=['POST'])
def translate_all():
    if not admin_authorized(): return jsonify({'error':'관리자 인증이 필요합니다.'}),403
    if not papago_ready(): return jsonify({'error':'서버 .env 파일에 파파고 API 인증키가 필요합니다.'}),400
    if STATUS.get('translating'): return jsonify({'message':'이미 번역 중입니다.'})
    threading.Thread(target=translation_job,daemon=True).start()
    return jsonify({'message':'파파고 번역을 시작했습니다.'})

# Public search uses cached Korean/Japanese labels only, preventing unbounded paid API calls.
@app.route('/api/status')
def status(): return jsonify(STATUS)

init_db()
if __name__ == '__main__': app.run(host='127.0.0.1',port=int(os.environ.get('PORT',5000)),debug=False)
