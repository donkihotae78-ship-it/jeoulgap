import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from petdeal.normalizer import parse, unit_price

CASES = [  # (title, cat, total_g, total_l, units)
    ("로얄캐닌 미니 어덜트 강아지 사료 8kg", "dog_dry", 8000, None, None),
    ("오리젠 캣 앤 키튼 5.4kg", "cat_dry", 5400, None, None),
    ("쉬바 고양이 파우치 85g x 24개", "wet", 2040, None, 24),
    ("캐츠랑 고양이 습식캔 160g × 24캔", "wet", 3840, None, 24),
    ("이나바 챠오츄르 14g x 50개", "wet", 700, None, 50),
    ("바잇미 강아지 배변패드 대형 100매", "pad", None, None, 100),
    ("페티즌 배변패드 중형 200매", "pad", None, None, 200),
    ("에버클린 벤토나이트 고양이 모래 11.3kg", "litter", 11300, None, None),
    ("라이프캣 두부모래 7L x 3개", "litter", None, 21, 3),
    ("조인트맥스 강아지 관절영양제 60정", "supplement", None, None, 60),
    ("<b>굿데이</b> 강아지 육포 오리 1kg", "treat", 1000, None, None),
]
fail = 0
for title, cat, g, l, u in CASES:
    r = parse(title, cat)
    ok = (g is None or abs((r["total_g"] or 0) - g) < 1) and (l is None or abs((r["total_l"] or 0) - l) < 0.01) and (u is None or r["units"] == u)
    print("OK " if ok else "FAIL", title, "->", r["total_g"], r["total_l"], r["units"], r["tags"])
    fail += not ok
print(unit_price(98000, "dog_dry", 8000, None))      # 원/kg
print(unit_price(23900, "wet", 2040, 24))             # 원/100g
print(unit_price(29900, "pad", None, 100))            # 원/장
print(unit_price(26900, "litter", None, 3, 21))       # 원/L
print(unit_price(35900, "supplement", None, 60))      # 원/정
print("실패", fail)
sys.exit(1 if fail else 0)
