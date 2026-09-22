"""네이버 쇼핑 검색 API 수집기. (공식 Open API — 일 25,000회 무료)
문서: https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md
"""
import time
import requests
from .normalizer import parse

API = "https://openapi.naver.com/v1/search/shop.json"


class NaverCollector:
    def __init__(self, cfg):
        self.h = {"X-Naver-Client-Id": cfg["client_id"], "X-Naver-Client-Secret": cfg["client_secret"]}
        self.display = cfg.get("display", 100)
        self.sort = cfg.get("sort", "sim")

    def search(self, query):
        r = requests.get(API, headers=self.h, params={"query": query, "display": self.display, "sort": self.sort}, timeout=15)
        r.raise_for_status()
        return r.json().get("items", [])

    def collect(self, keywords_by_cat, min_price=5000):
        """keywords_by_cat: {category: [query,...]} → 정규화된 상품 리스트"""
        out, seen = [], set()
        for cat, queries in keywords_by_cat.items():
            for q in queries:
                try:
                    items = self.search(q)
                except Exception as e:  # 네트워크·쿼터 오류는 건너뜀
                    print(f"[collect] {q}: {e}")
                    continue
                for it in items:
                    pid = it.get("productId")
                    price = int(it.get("lprice") or 0)
                    if not pid or pid in seen or price < min_price:
                        continue
                    seen.add(pid)
                    n = parse(it.get("title", ""), cat)
                    out.append({
                        "product_id": pid, "title": n["title"], "price": price,
                        "mall": it.get("mallName") or "네이버", "link": it.get("link"),
                        "image": it.get("image"), "brand": it.get("brand") or it.get("maker"),
                        "category": cat, "total_g": n["total_g"], "total_l": n["total_l"], "units": n["units"], "tags0": n["tags"],
                    })
                time.sleep(0.2)
        return out


class DemoCollector:
    """API 키 없이 파이프라인 검증용. data/sample_items.json 사용"""
    def __init__(self, path="data/sample_items.json"):
        import json
        with open(path, encoding="utf-8") as f:
            self.items = json.load(f)

    def collect(self, keywords_by_cat, min_price=5000):
        out = []
        for it in self.items:
            n = parse(it["title"], it["category"])
            out.append({**it, **n, "tags0": n["tags"]})
        return out
