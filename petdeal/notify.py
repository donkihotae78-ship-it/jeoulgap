"""발송: 텔레그램(즉시) / 카카오 친구톡(주간, 딜러사 API) / 콘솔(데모)"""
import requests

CAT_KO = {"dog_dry": "강아지 사료", "cat_dry": "고양이 사료", "wet": "습식·캔", "treat": "간식",
          "pad": "배변패드", "litter": "고양이 모래", "supplement": "영양제"}


def render(deal, link, disclosure):
    head = f"[{CAT_KO.get(deal['category'], deal['category'])}] {deal['title'][:60]}"
    price = f"{deal['price']:,}원"
    if deal.get("prev_min") and (deal.get("drop") or 0) > 0:
        price = f"{deal['prev_min']:,}→{deal['price']:,}원"
    lines = [head, f"💰 {price}  ({deal['mall']})"]
    for r in deal["reasons"]:
        lines.append(f"· {r}")
    if deal.get("tags"):
        lines.append("· " + " ".join(f"#{t}" for t in deal["tags"]))
    lines.append(f"구매 → {link}")
    lines.append(disclosure)
    return "\n".join(lines)


class Telegram:
    def __init__(self, cfg):
        self.url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        self.chat = cfg["chat_id"]

    def send(self, text):
        r = requests.post(self.url, json={"chat_id": self.chat, "text": text, "disable_web_page_preview": False}, timeout=15)
        r.raise_for_status()
        return r.json()


class Console:
    def send(self, text):
        print("-" * 60)
        print(text)
        return {"ok": True}


class OneSignal:
    """웹푸시(PWA). 실행당 1건 다이제스트, 일 상한(push_per_day)은 data/push_state.json으로 관리.
    REST 키는 신형('Key ...')·구형('Basic ...') 인증을 순서대로 시도."""
    URL = "https://onesignal.com/api/v1/notifications"

    def __init__(self, app_id, cfg, state_path="data/push_state.json"):
        self.app_id = app_id
        self.key = cfg.get("rest_api_key") or ""
        self.segment = cfg.get("segment") or "Total Subscriptions"
        self.per_day = int(cfg.get("push_per_day") or 1)
        self.state_path = state_path

    def _state(self):
        import json, os
        if os.path.exists(self.state_path):
            try:
                return json.load(open(self.state_path, encoding="utf-8"))
            except Exception:
                pass
        return {}

    def allowed(self, today):
        s = self._state()
        return s.get("date") != today or int(s.get("count", 0)) < self.per_day

    def _mark(self, today):
        import json, os
        s = self._state()
        s = {"date": today, "count": (int(s.get("count", 0)) + 1) if s.get("date") == today else 1}
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        json.dump(s, open(self.state_path, "w", encoding="utf-8"))

    def send_digest(self, deals, site_url, today):
        if not deals or not self.allowed(today):
            return {"skipped": True}
        top = deals[0]
        head = f"저울값 펫 · 오늘의 딜 {len(deals)}건"
        body = " / ".join(f"{d['title'][:28]} {d['price']:,}원" for d in deals[:2])
        payload = {"app_id": self.app_id, "included_segments": [self.segment],
                   "headings": {"en": head, "ko": head}, "contents": {"en": body, "ko": body},
                   "url": site_url or None}
        last = None
        for scheme in ("Key", "Basic"):
            r = requests.post(self.URL, json=payload, timeout=15,
                              headers={"Authorization": f"{scheme} {self.key}", "Content-Type": "application/json"})
            if r.status_code < 400:
                self._mark(today)
                return r.json()
            last = (r.status_code, r.text[:200])
        raise RuntimeError(f"OneSignal 실패 {last}")


def digest_text(deals):
    """블로그·카페·카카오 홈 붙여넣기용 텍스트(수동 게시 보조)"""
    if not deals:
        return ""
    lines = ["[저울값 펫 · 오늘의 단위가 TOP]"]
    for d in deals[:10]:
        lines.append(f"- {CAT_KO.get(d['category'], d['category'])} | {d['title'][:40]} | {d['price']:,}원 | {d['unit_price']:,}{d['unit_label']} | {d['mall']}")
    return "\n".join(lines)


class Kakao:
    """친구톡은 카카오 공식 딜러사(솔라피·비즈고 등) API 경유. 채널 심사·템플릿 승인 후 사용.
    여기서는 인터페이스만 고정 — provider 별 구현은 계약 후 1시간 작업."""
    def __init__(self, cfg):
        self.cfg = cfg

    def send(self, text):
        raise NotImplementedError("카카오 딜러사 계약 후 provider 구현 필요 (config.kakao.provider)")
