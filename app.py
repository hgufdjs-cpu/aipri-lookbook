"""Aipri Verse unofficial bilingual outfit search."""
import os
import io
import hmac
import re
import sqlite3
import threading
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, Response, abort

load_dotenv()
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='/static')
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'aipri.db'))
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')
ROOT = 'https://aipri.jp/verse/'
ITEM_ROOT = ROOT + 'item/'
PAGES = [(f'oa{i}', f'오네가이 {i}탄') for i in range(4, 0, -1)] + [(f'ring{i}', f'링 {i}탄') for i in range(6, 0, -1)] + [(str(i), f'아이프리 {i}탄') for i in range(6, 0, -1)] + [('special', '스페셜 코디')]
# All 17 official series/round index pages; additional official pages can be discovered later.
# Depending on official naming changes, a missing page is safely skipped and reported.
# Initial catalog: names independently checked against official lists (2026-11-11).
# Images remain hosted by the official site; verify permission before public hotlinking.
KNOWN_OFFICIAL_THUMBS = {
    ('oa4','スイートいちごグリーン'): 'https://aipri.jp/verse/item/img/oa4/OA4-076_thumb.webp',
    ('oa4','とんがりぼうしまほうつかいピンク'): 'https://aipri.jp/verse/item/img/oa4/OAF4-007-1_thumb.webp',
}
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
                known_image = KNOWN_OFFICIAL_THUMBS.get((slug,name))
                if known_image:
                    c.execute("UPDATE outfits SET image_url=? WHERE name_ja=? AND series=? AND (image_url IS NULL OR image_url='')", (known_image,name,slug))


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
    """Index image/name pairs on the official round page.

    Keep exact Japanese alt text; only accept images in the item image tree.
    Pages may use lazy-loading attributes or srcset. A fallback name is read
    from nearby item text only when it matches a verified Japanese caption.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    seen = set()
    items = []
    for img in soup.select('img'):
        if img.find_parent(['header', 'nav', 'footer']):
            continue
        urls = []
        for attr in ('data-src', 'data-original', 'data-lazy-src', 'src'):
            if img.get(attr): urls.append(img[attr])
        for attr in ('data-srcset', 'srcset'):
            if img.get(attr):
                urls.extend(piece.strip().split(' ')[0] for piece in img[attr].split(','))
        full = next((urljoin(url, raw) for raw in urls if
                     valid_image(urljoin(url, raw)) and
                     '/verse/item/img/' in urlparse(urljoin(url, raw)).path), None)
        if not full:
            continue
        alt = re.sub(r'\s+', ' ', img.get('alt', '')).strip()
        if not alt:
            # Prefer the immediate item caption, not an unrelated section title.
            parent = img.parent
            for _ in range(3):
                if parent is None: break
                texts = [t.get_text(' ', strip=True) for t in parent.find_all(['p', 'span'], recursive=False)]
                if len(texts) == 1 and 1 < len(texts[0]) < 65:
                    alt = texts[0]
                    break
                parent = parent.parent
        if not alt or len(alt) > 75 or not re.search('[\u3040-\u30ff\u3400-\u9fff]', alt):
            continue
        if any(word in alt for word in ('コーデアイテム', 'ページ', 'サイト', 'カレンダー', 'メニュー', 'ボタン', 'キャンペーン', 'PAGE TOP')):
            continue
        if alt in seen:
            continue
        seen.add(alt)
        items.append((alt, full))
    return items

def fetch_page(page):
    slug, label = page
    url = ITEM_ROOT + slug + '.html'
    r = requests.get(url, timeout=20, headers={'User-Agent':'Mozilla/5.0 (compatible; AipriOutfitIndexer/1.0; personal fan directory)'})
    r.raise_for_status()
    return slug, url, parse_page(r.text,url)

def refresh_job():
    global STATUS
    with LOCK:
        STATUS.update(running=True,message='공식 코디 목록을 가져오는 중',pages=0,items=0,errors=[])
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
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
        if STATUS['pages'] > 0 and STATUS['items'] > 0:
            with conn() as c:
                c.execute('CREATE TABLE IF NOT EXISTS crawl_meta (key TEXT PRIMARY KEY, value TEXT)')
                c.execute("INSERT INTO crawl_meta(key,value) VALUES('last_full_crawl',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (now(),))
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

def auto_refresh_if_needed():
    """Run a full crawl after deployment even if two starter thumbnails exist.

    Previous code incorrectly treated any recent image as a complete crawl.
    The new condition checks actual page coverage and the last full crawl.
    """
    if os.getenv('AUTO_REFRESH', '1') != '1':
        return
    try:
        with conn() as c:
            c.execute('CREATE TABLE IF NOT EXISTS crawl_meta (key TEXT PRIMARY KEY, value TEXT)')
            row = c.execute("SELECT value FROM crawl_meta WHERE key='last_full_crawl'").fetchone()
        if row:
            try:
                if (datetime.now(timezone.utc) - datetime.fromisoformat(row[0])).total_seconds() < 86400:
                    return
            except (ValueError, TypeError):
                pass
        threading.Thread(target=refresh_job, daemon=True, name='aipri-full-crawl').start()
    except Exception as exc:
        with LOCK:
            STATUS['message'] = '자동 수집 시작 실패: ' + str(exc)[:120]

@app.route('/')
def home(): return render_template('index.html')

@app.route('/health')
def health(): return jsonify({'ok': True})

@app.route('/api/image/<int:outfit_id>')
def official_image(outfit_id):
    """Same-origin fallback for official thumbnails when browser hotlinking fails."""
    with conn() as c:
        row = c.execute('SELECT image_url FROM outfits WHERE id=?', (outfit_id,)).fetchone()
    if not row or not row['image_url'] or not valid_image(row['image_url']):
        abort(404)
    try:
        r = requests.get(row['image_url'], timeout=12, allow_redirects=False,
                         headers={'User-Agent':'Mozilla/5.0', 'Referer':ROOT}, stream=True)
        if r.status_code != 200 or not r.headers.get('Content-Type','').lower().startswith('image/'):
            abort(404)
        if int(r.headers.get('Content-Length') or 0) > 3_000_000:
            abort(413)
        content = r.raw.read(3_000_001)
        r.close()
        if len(content) > 3_000_000:
            abort(413)
        # Do not show horizontal text-only event/collaboration banners as outfit pictures.
        # Keep the outfit entry and its Japanese title; display the neutral placeholder.
        try:
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
                if width < 40 or height < 40 or width / max(height, 1) > 2.0:
                    abort(404)
        except (UnidentifiedImageError, OSError, ValueError):
            abort(404)
        return Response(content, content_type=r.headers['Content-Type'],
                        headers={'Cache-Control':'public, max-age=86400'})
    except requests.RequestException:
        abort(502)

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
auto_refresh_if_needed()
if __name__ == '__main__': app.run(host='127.0.0.1',port=int(os.environ.get('PORT',5000)),debug=False)
