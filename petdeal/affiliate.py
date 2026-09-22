"""제휴 링크 변환.
  - 쿠팡파트너스 딥링크 API (누적 수익 15만 원 후 승인, 키 입력 시 자동)
  - 네이버 쇼핑커넥트: 자동화 링크 제재 → 수동 발급 후 CSV 매핑
  - 매핑 없으면 원본 링크 그대로 (수익 0, 노출은 유지)
"""
import csv
import hmac
import hashlib
import os
import time
import requests

COUPANG_HOST = "https://api-gateway.coupang.com"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"


def _coupang_auth(method, path, secret, access):
    dt = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    msg = dt + method + path
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access}, signed-date={dt}, signature={sig}"


class Affiliate:
    def __init__(self, cfg):
        self.cfg = cfg
        self.manual = {}
        p = cfg.get("manual_links_csv")
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self.manual[row["product_id"]] = row["link"]
        c = cfg.get("coupang", {})
        self.coupang_ok = bool(c.get("access_key") and c.get("secret_key"))

    def coupang_deeplink(self, urls):
        c = self.cfg["coupang"]
        h = {"Authorization": _coupang_auth("POST", DEEPLINK_PATH, c["secret_key"], c["access_key"]),
             "Content-Type": "application/json"}
        r = requests.post(COUPANG_HOST + DEEPLINK_PATH, headers=h, json={"coupangUrls": urls}, timeout=15)
        r.raise_for_status()
        return {d["originalUrl"]: d["shortenUrl"] for d in r.json().get("data", [])}

    def convert(self, item):
        pid, link = item["product_id"], item["link"]
        if pid in self.manual:
            return self.manual[pid], "manual"
        if self.coupang_ok and "coupang.com" in (link or ""):
            try:
                return self.coupang_deeplink([link]).get(link, link), "coupang"
            except Exception as e:
                print("[affiliate] coupang:", e)
        return link, "raw"
