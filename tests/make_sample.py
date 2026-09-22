"""데모용 샘플 상품 + 30일 가격 이력 생성 (예시 데이터, 실제 시세 아님)"""
import json, os, random, sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from petdeal.db import DB
from petdeal.normalizer import parse

random.seed(11)
S = [
 ("dog_dry","로얄캐닌 미니 어덜트 강아지 사료 8kg",98000,"쿠팡"),
 ("dog_dry","오리젠 오리지널 독 11.4kg",139000,"네이버"),
 ("dog_dry","내추럴발란스 LID 오리 강아지 사료 10.9kg",89000,"펫프렌즈"),
 ("dog_dry","네추럴코어 에코 강아지 사료 6kg",42900,"쿠팡"),
 ("dog_dry","하림펫푸드 더리얼 강아지 사료 5.5kg",38900,"11번가"),
 ("cat_dry","로얄캐닌 인도어 고양이 사료 10kg",112000,"쿠팡"),
 ("cat_dry","오리젠 캣 앤 키튼 5.4kg",79000,"네이버"),
 ("cat_dry","네추럴코어 고양이 사료 7kg",49900,"핏펫"),
 ("cat_dry","캐츠랑 고양이 사료 6.5kg",24900,"쿠팡"),
 ("cat_dry","고 솔루션 카니보어 고양이 3.6kg",56000,"펫프렌즈"),
 ("wet","쉬바 고양이 파우치 85g x 24개",23900,"쿠팡"),
 ("wet","캐츠랑 고양이 습식캔 160g x 24캔",26900,"네이버"),
 ("wet","웰니스 코어 강아지 습식캔 354g x 12캔",39900,"펫프렌즈"),
 ("wet","이나바 챠오츄르 고양이 간식 14g x 50개",22900,"쿠팡"),
 ("treat","굿데이 강아지 육포 오리 1kg",15900,"쿠팡"),
 ("treat","페디그리 덴타스틱 대형견 28개 720g",18900,"네이버"),
 ("treat","동결건조 닭가슴살 강아지 간식 200g",12900,"핏펫"),
 ("treat","테비 고양이 동결건조 간식 100g",9900,"쿠팡"),
 ("pad","바잇미 강아지 배변패드 대형 100매",29900,"쿠팡"),
 ("pad","페티즌 배변패드 중형 200매",31900,"네이버"),
 ("pad","도그웨이 배변패드 특대형 50매",24900,"펫프렌즈"),
 ("pad","코스트코 커클랜드 배변패드 대형 100매",25900,"11번가"),
 ("pad","탐사 배변패드 중형 100매",13900,"쿠팡"),
 ("litter","에버클린 벤토나이트 고양이 모래 11.3kg",25900,"쿠팡"),
 ("litter","탐사 벤토나이트 고양이 모래 10kg",11900,"쿠팡"),
 ("litter","라이프캣 두부모래 7L x 3개",26900,"네이버"),
 ("litter","시크릿캣 카사바 모래 6L x 4개",39900,"핏펫"),
 ("litter","네이처스 미라클 벤토나이트 9kg",19900,"펫프렌즈"),
 ("supplement","조인트맥스 강아지 관절영양제 60정",35900,"쿠팡"),
 ("supplement","닥터독 강아지 유산균 30포",24900,"네이버"),
]
items = []
for i,(cat,title,price,mall) in enumerate(S):
    items.append({"product_id": f"demo{i:03d}", "title": title, "price": price, "mall": mall,
                  "link": f"https://example.com/p/{i}", "image": None, "brand": title.split()[0], "category": cat})
sale = {"demo000": 0.80, "demo007": 0.82, "demo018": 0.78, "demo024": 0.83, "demo013": 0.84, "demo011": 0.85}
os.makedirs("data", exist_ok=True)

dbp = os.environ.get("PD_DB", "data/petdeal.sqlite")
if os.path.exists(dbp): os.remove(dbp)
db = DB(dbp)
now = datetime.now()
for it in items:
    n = parse(it["title"], it["category"])
    for d in range(30, 0, -1):
        ts = (now - timedelta(days=d)).replace(microsecond=0).isoformat()
        p = int(it["price"] * random.uniform(0.97, 1.08) // 100 * 100)
        db.upsert_product({**it, **n, "price": p}, ts)
db.commit()
for it in items:
    if it["product_id"] in sale:
        it["price"] = int(it["price"] * sale[it["product_id"]] // 100 * 100)
json.dump(items, open("data/sample_items.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

if not os.path.exists("data/channel.json"):   # 운영자가 편집한 값은 덮어쓰지 않음
    json.dump({"name": "저울값 펫",
               "site": "https://donkihotae78-ship-it.github.io/jeoulgap/",
               "kakao": "https://pf.kakao.com/_jeoulgap",
               "instagram": "https://www.instagram.com/jeoulgap",
               "cafe": "",
               "ga_id": "",              # GA4 측정 ID (G-XXXXXXX) — 클릭 계측
               "onesignal_app_id": "",   # OneSignal App ID — 웹푸시
               "contact": "donkihotae78@gmail.com"},
              open("data/channel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"title":"(예시) 국산 벤토나이트 모래 10kg x 2 구독자 단독가", "brand":"브랜드 협의 중", "price":19900, "list_price":27800,
           "ends":(now+timedelta(days=3)).strftime("%Y-%m-%d 23:59"), "qty_goal":200, "qty_sold":0,
           "note":"브랜드 직배송·CS. 90일 판정 통과 후 개시"}, open("data/groupbuy.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("샘플 생성 완료", len(items))
