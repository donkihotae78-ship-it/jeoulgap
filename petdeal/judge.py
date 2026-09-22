"""판정 로직.
  규칙 A: 90일 최저가 대비 drop_threshold 이상 하락 (이력 3회 이상 있을 때만)
  규칙 B: 카테고리 내 단위가 하위 percentile (이력 없어도 통과 가능 → '신규' 태그)
  중복: dedupe_days 내 동일 상품 알림 금지 (단, 알림가보다 더 떨어지면 예외)
"""
from statistics import quantiles
from .normalizer import unit_price


def evaluate(db, items, ts, rules):
    # 카테고리별 단위가 분포
    by_cat = {}
    for it in items:
        up, label = unit_price(it["price"], it["category"], it.get("total_g"), it.get("units"), it.get("total_l"))
        it["unit_price"], it["unit_label"] = up, label
        if up:
            by_cat.setdefault(it["category"], []).append(up)
    cutoff = {}
    for cat, vals in by_cat.items():
        if len(vals) >= 5:
            q = quantiles(vals, n=100)
            cutoff[cat] = q[int(rules["unit_price_percentile"] * 100) - 1]
        else:
            cutoff[cat] = min(vals)
    cat_avg = {cat: round(sum(v) / len(v)) for cat, v in by_cat.items()}

    deals = []
    for it in items:
        reasons, tags = [], list(it.get("tags0") or [])
        mn, n = db.min_price_before(it["product_id"], ts, rules["history_days"])
        drop = None
        if mn and n >= 3:
            drop = 1 - it["price"] / mn
            if drop >= rules["drop_threshold"]:
                reasons.append(f"{rules['history_days']}일 최저가 대비 -{drop*100:.0f}%")
        elif n < 3:
            tags.append("신규")
        up = it["unit_price"]
        if up and it["category"] in rules.get("unit_rank_categories", []) and up <= cutoff.get(it["category"], 0):
            reasons.append(f"단위가 하위 {int(rules['unit_price_percentile']*100)}% ({up:,}{it['unit_label']}, 평균 {cat_avg[it['category']]:,})")
        if not reasons:
            continue
        # 규칙B 단독: 현재가가 90일 최저가 근처(+3%)가 아니면 "지금 사라"가 아님 → 제외
        if drop is not None and drop < rules["drop_threshold"] and it["price"] > mn * 1.03:
            continue
        # 규칙B 단독 + 신규는 통과, 규칙A 단독은 단위가 평균 이상이면 제외(미끼 방지)
        if up and up > cat_avg[it["category"]] * 1.2:
            continue
        prev = db.recently_alerted(it["product_id"], ts, rules["dedupe_days"])
        if prev is not None and it["price"] >= prev:
            continue
        it.update({"reasons": reasons, "tags": tags, "drop": drop, "prev_min": mn,
                   "cat_avg_unit": cat_avg[it["category"]]})
        # 점수: 하락률 + 단위가 우위
        score = (drop or 0) * 100 + (1 - up / cat_avg[it["category"]]) * 100 if up else (drop or 0) * 100
        it["score"] = round(score, 1)
        deals.append(it)
    deals.sort(key=lambda d: -d["score"])
    return deals[: rules["max_alerts_per_run"]], cat_avg
