"""실행: python run.py [--demo] [--dry] [--site-only]
  --demo   : API 키 없이 샘플 데이터로 전체 파이프라인 검증
  --dry    : 발송 없이 콘솔 출력
  cron 예시: 0 6,12,18,0 * * * cd /srv/petdeal && python run.py >> logs/run.log 2>&1
"""
import sys
import json
import os
from datetime import datetime
from petdeal.settings import load
from petdeal.db import DB
from petdeal.collector import NaverCollector, DemoCollector, ManualCollector
from petdeal.judge import evaluate
from petdeal.affiliate import Affiliate
from petdeal.notify import Telegram, Console, OneSignal, render, digest_text
from petdeal.publish import build_payload, write

args = set(sys.argv[1:])
cfg = load("config.yaml")
ts = datetime.now().replace(microsecond=0).isoformat()
db = DB(os.environ.get("PD_DB", "data/petdeal.sqlite"))

manual_path = "data/manual_items.json"
has_manual = os.path.exists(manual_path) and os.path.getsize(manual_path) > 2
if "--demo" in args:
    collector = DemoCollector()
elif has_manual:
    print("[정보] data/manual_items.json 수동 큐레이션 데이터로 실행")
    collector = ManualCollector(manual_path)
elif cfg["naver"]["client_id"]:
    collector = NaverCollector(cfg["naver"])
else:
    print("[주의] 수동 데이터·NAVER_CLIENT_ID 모두 없음 → 데모 데이터로 실행")
    if not os.path.exists("data/sample_items.json"):
        import subprocess; subprocess.run([sys.executable, "tests/make_sample.py"], check=True)
    collector = DemoCollector()
items = collector.collect(cfg["keywords"], cfg["rules"]["min_price_krw"])
print(f"[{ts}] 수집 {len(items)}건")

deals, cat_avg = evaluate(db, items, ts, cfg["rules"])
for it in items:
    db.upsert_product(it, ts)

groupbuy = json.load(open("data/groupbuy.json", encoding="utf-8")) if os.path.exists("data/groupbuy.json") else {}
channel = json.load(open("data/channel.json", encoding="utf-8")) if os.path.exists("data/channel.json") else {}

aff = Affiliate(cfg["affiliate"])
quiet = "--dry" in args or "--demo" in args
# 딜별 메시지: 텔레그램(선택, 토큰 있을 때만) 또는 콘솔
sender = Telegram(cfg["telegram"]) if (not quiet and cfg["telegram"]["bot_token"]) else Console()
for d in deals:
    link, src = aff.convert(d)
    d["aff_link"] = link
    text = render(d, link, cfg["affiliate"]["disclosure"])
    try:
        sender.send(text)
        db.log_alert(d["product_id"], ts, d["price"], "telegram" if isinstance(sender, Telegram) else "console")
    except Exception as e:
        print("[send]", e)
db.commit()
print(f"딜 {len(deals)}건 발송")

# 웹푸시 다이제스트(PWA): 실행당 1건, 일 상한은 config.onesignal.push_per_day
os_app = (channel.get("onesignal_app_id") or "").strip()
if deals and os_app and cfg["onesignal"]["rest_api_key"] and not quiet:
    try:
        r = OneSignal(os_app, cfg["onesignal"]).send_digest(deals, channel.get("site"), ts[:10])
        print("[push]", "건너뜀(일 상한)" if r.get("skipped") else f"발송 id={r.get('id')}")
    except Exception as e:
        print("[push]", e)
elif deals and not os_app:
    print("[push] data/channel.json 의 onesignal_app_id 미설정 → 웹푸시 생략")

# 수동 게시 보조: 블로그·카페·카카오 홈 붙여넣기용 텍스트
with open("data/digest.txt", "w", encoding="utf-8") as f:
    f.write(digest_text(deals))

payload = build_payload(db, items, deals, cat_avg, ts, groupbuy, channel)
out = write(payload)
import shutil; os.makedirs("docs", exist_ok=True); shutil.copy(out, "docs/index.html")
print("사이트 생성:", out, "→ docs/index.html")
