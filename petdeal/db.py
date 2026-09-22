import sqlite3
from datetime import datetime, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  product_id TEXT PRIMARY KEY,
  title TEXT, mall TEXT, link TEXT, image TEXT, brand TEXT,
  category TEXT, total_g REAL, units INTEGER, total_l REAL,
  first_seen TEXT
);
CREATE TABLE IF NOT EXISTS prices (
  product_id TEXT, ts TEXT, price INTEGER,
  PRIMARY KEY (product_id, ts)
);
CREATE TABLE IF NOT EXISTS alerts (
  product_id TEXT, ts TEXT, price INTEGER, channel TEXT
);
CREATE INDEX IF NOT EXISTS idx_prices_pid ON prices(product_id, ts);
"""


class DB:
    def __init__(self, path="data/petdeal.sqlite"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert_product(self, p, ts):
        self.conn.execute(
            """INSERT INTO products(product_id,title,mall,link,image,brand,category,total_g,units,total_l,first_seen)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(product_id) DO UPDATE SET title=excluded.title, mall=excluded.mall,
               link=excluded.link, image=excluded.image, brand=excluded.brand, category=excluded.category,
               total_g=excluded.total_g, units=excluded.units, total_l=excluded.total_l""",
            (p["product_id"], p["title"], p["mall"], p["link"], p.get("image"), p.get("brand"),
             p["category"], p.get("total_g"), p.get("units"), p.get("total_l"), ts),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO prices(product_id, ts, price) VALUES(?,?,?)",
            (p["product_id"], ts, p["price"]),
        )

    def min_price_before(self, product_id, ts, days):
        since = (datetime.fromisoformat(ts) - timedelta(days=days)).isoformat()
        row = self.conn.execute(
            "SELECT MIN(price) m, COUNT(*) n FROM prices WHERE product_id=? AND ts>=? AND ts<?",
            (product_id, since, ts),
        ).fetchone()
        return row["m"], row["n"]

    def history(self, product_id, days=90):
        since = (datetime.now() - timedelta(days=days)).isoformat()
        return [dict(r) for r in self.conn.execute(
            "SELECT ts, price FROM prices WHERE product_id=? AND ts>=? ORDER BY ts", (product_id, since))]

    def recently_alerted(self, product_id, ts, days):
        since = (datetime.fromisoformat(ts) - timedelta(days=days)).isoformat()
        row = self.conn.execute(
            "SELECT MIN(price) p FROM alerts WHERE product_id=? AND ts>=?", (product_id, since)).fetchone()
        return row["p"]  # None 이면 최근 알림 없음

    def log_alert(self, product_id, ts, price, channel):
        self.conn.execute("INSERT INTO alerts VALUES(?,?,?,?)", (product_id, ts, price, channel))

    def commit(self):
        self.conn.commit()
