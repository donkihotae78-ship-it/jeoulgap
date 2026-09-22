"""deals.json + site/index.html 생성 (템플릿의 __DATA__ 치환)"""
import json
import os
from datetime import datetime
from .notify import CAT_KO


def build_payload(db, items, deals, cat_avg, ts, groupbuy=None, channel=None):
    ranking = {}
    for it in items:
        if not it.get("unit_price"):
            continue
        hist = db.history(it["product_id"], 90)
        row = {
            "id": it["product_id"], "title": it["title"], "mall": it["mall"], "price": it["price"],
            "unit": it["unit_price"], "unit_label": it["unit_label"], "link": it.get("aff_link") or it["link"],
            "vs_avg": round((it["unit_price"] / cat_avg[it["category"]] - 1) * 100),
            "spark": [h["price"] for h in hist][-30:], "tags": it.get("tags0") or [],
            "deal": bool(it.get("reasons")),
        }
        ranking.setdefault(it["category"], []).append(row)
    order = ["pad", "litter", "wet", "treat", "cat_dry", "dog_dry", "supplement"]
    ranking = {c: ranking[c] for c in sorted(ranking, key=lambda c: order.index(c) if c in order else 99)}
    for cat in ranking:
        ranking[cat].sort(key=lambda r: r["unit"])
        ranking[cat] = ranking[cat][:15]
    payload = {
        "generated": ts, "cat_ko": CAT_KO, "cat_avg": cat_avg,
        "stats": {"products": len(items), "deals": len(deals),
                  "best_pad_unit": min([r["unit"] for r in ranking.get("pad", [])] or [0]),
                  "best_litter_unit": min([r["unit"] for r in ranking.get("litter", [])] or [0])},
        "deals": [{"id": d["product_id"], "cat": d["category"], "title": d["title"], "mall": d["mall"],
                   "price": d["price"], "prev_min": d.get("prev_min") if (d.get("drop") or 0) > 0 else None, "unit": d["unit_price"],
                   "unit_label": d["unit_label"], "reasons": d["reasons"], "tags": d["tags"],
                   "link": d.get("aff_link") or d["link"]} for d in deals],
        "ranking": ranking,
        "groupbuy": groupbuy or {},
        "channel": channel or {},
    }
    return payload


def write(payload, template="site/template.html", out_html="site/index.html", out_json="data/deals.json"):
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    with open(template, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    return out_html
