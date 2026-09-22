"""상품명 → 총중량·개수 추정 → 단위가 환산 (반려동물 소모품).

단위가 정의(채널의 핵심 차별점):
  dog_dry / cat_dry : 원 / kg          (같은 SKU 가격이력 중심. 등급 다른 사료끼리 단위가 순위는 참고용)
  wet               : 원 / 100g        (캔·파우치 g 환산)
  treat             : 원 / 100g
  pad               : 원 / 1장         (배변패드; 규격(소·중·대) 태그)
  litter            : 원 / kg  (kg 표기) 또는 원 / L (L 표기)
  supplement        : 원 / 100g 또는 원 / 정
"""
import re
import html

_W = r"(\d+(?:[.,]\d+)?)\s*(kg|g|킬로|그램|㎏|ｇ|ml|㎖|l|리터)"
_C = r"(\d+)\s*(개|팩|입|캔|봉|포|매|장|정|알|스틱|ea|EA|p|P)"
_X = r"(?:x|X|×|\*)\s*(\d+)"
RE_W = re.compile(_W, re.I)
RE_C = re.compile(_C)
RE_X = re.compile(_X)
RE_SIZE = re.compile(r"(초대형|특대형|대형|중형|소형|점보|XL|L|M|S)\b")
RE_PROTEIN = re.compile(r"조단백\s*(\d{2})\s*%")


def clean_title(t: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "", t or ""))
    return re.sub(r"\s+", " ", t).strip()


def _to_base(v, unit):
    """g 또는 L 로 환산. 반환 (값, 'g'|'l')"""
    v = float(v.replace(",", "."))
    u = unit.lower()
    if u in ("kg", "킬로", "㎏"):
        return v * 1000, "g"
    if u in ("l", "리터"):
        return v, "l"
    return v, "g"  # g, ml(습식 ≈ g)


def parse(title: str, category: str) -> dict:
    t = clean_title(title)
    units = None
    m = RE_X.search(t)
    if m:
        units = int(m.group(1))
    else:
        m = RE_C.search(t)
        if m:
            units = int(m.group(1))

    total_g, total_l = None, None
    ws = RE_W.findall(t)
    if ws:
        per, kind = _to_base(ws[0][0], ws[0][1])
        mult = units if (units and (RE_X.search(t) or (category in ("wet", "treat") and per <= 500))) else 1
        if kind == "l":
            total_l = per * mult
        else:
            total_g = per * mult
    tags = []
    m = RE_SIZE.search(t)
    if m and category == "pad":
        tags.append(m.group(1))
    m = RE_PROTEIN.search(t)
    protein_pct = int(m.group(1)) if m else None
    if "고양이" in t or "캣" in t or "cat" in t.lower():
        tags.append("고양이")
    elif "강아지" in t or "독" in t or "dog" in t.lower() or "퍼피" in t:
        tags.append("강아지")
    return {"title": t, "total_g": total_g, "total_l": total_l, "units": units,
            "protein_pct": protein_pct, "tags": tags}


def unit_price(price: int, category: str, total_g, units, total_l=None):
    """(값, 라벨). 환산 불가 시 (None, 사유)"""
    if category in ("dog_dry", "cat_dry"):
        if total_g:
            return round(price / total_g * 1000), "원/kg"
        return None, "중량 미상"
    if category in ("wet", "treat"):
        if total_g:
            return round(price / total_g * 100), "원/100g"
        return None, "중량 미상"
    if category == "pad":
        if units:
            return round(price / units), "원/장"
        return None, "매수 미상"
    if category == "litter":
        if total_g:
            return round(price / total_g * 1000), "원/kg"
        if total_l:
            return round(price / total_l), "원/L"
        return None, "용량 미상"
    if category == "supplement":
        if units and not total_g:
            return round(price / units), "원/정"
        if total_g:
            return round(price / total_g * 100), "원/100g"
        return None, "규격 미상"
    return None, "카테고리 미정의"
