"""ユニクロ商品の値下げを検知して LINE に通知する。

- 価格取得: ユニクロ公式サイトが内部で使っている商品API
- 状態保存: price.json（GitHub Actionsが自動コミット）
- 通知: LINE Messaging API（push）
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

PRODUCT_ID = "E486425-000"
COLOR = "53"
SIZE = "100"
PRODUCT_URL = (
    f"https://www.uniqlo.com/jp/ja/products/{PRODUCT_ID}/00"
    f"?colorDisplayCode={COLOR}&sizeDisplayCode={SIZE}"
)
API_URL = (
    "https://www.uniqlo.com/jp/api/commerce/v5/ja/products"
    f"?productIds={PRODUCT_ID}&withPrices=true&withStocks=false&httpFailure=true"
)
STATE = Path(__file__).parent / "price.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def fetch_price():
    """(商品名, 現在価格) を返す。期間限定価格(promo)があればそちらを優先。"""
    body = json.loads(http(API_URL, headers={"Accept": "application/json"}))
    items = body["result"]["items"]
    if not items:
        raise RuntimeError("商品が見つかりません（品番変更・販売終了の可能性）")
    item = items[0]
    prices = item["prices"]
    promo = prices.get("promo")
    base = prices.get("base")
    current = (promo or base)["value"]
    return item.get("name", PRODUCT_ID), int(current)


def line_push(text):
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user = os.environ["LINE_USER_ID"]
    payload = json.dumps({"to": user, "messages": [{"type": "text", "text": text}]}).encode()
    http(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )


def main():
    if os.environ.get("TEST_NOTIFY") == "true":
        line_push("✅ ユニクロ値下げ通知のテストです。LINE連携は正常です。")
        print("test message sent")

    name, price = fetch_price()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    last = state.get("price")
    print(f"{name}: 今回 {price}円 / 前回 {last}円")

    if last is not None and price < last:
        line_push(
            f"🔻 値下げ！\n{name}\n{last:,}円 → {price:,}円（-{last - price:,}円）\n{PRODUCT_URL}"
        )
        print("notified")

    # 値上がり時も基準を更新（再値下げを検知するため）
    if price != last:
        STATE.write_text(json.dumps({"price": price, "name": name}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
