"""ユニクロ商品（色・サイズ指定）の値下げを検知して LINE に通知する。

- 価格取得: ユニクロ公式サイトが内部で使っている商品API（色×サイズ単位の価格）
- 状態保存: price.json（GitHub Actionsが自動コミット）
- 通知: LINE Messaging API（push）
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

PRODUCT_ID = "E486425-000"
PRICE_GROUP = "00"
COLOR = "53"
SIZE = "090"  # サイズ90（表示コードは3桁）
PRODUCT_URL = (
    f"https://www.uniqlo.com/jp/ja/products/{PRODUCT_ID}/{PRICE_GROUP}"
    f"?colorDisplayCode={COLOR}&sizeDisplayCode={SIZE}"
)
BASE = "https://www.uniqlo.com/jp/api/commerce/v5/ja/products"
L2S_URL = (
    f"{BASE}/{PRODUCT_ID}/price-groups/{PRICE_GROUP}/l2s"
    "?withPrices=true&withStocks=false&includePreviousPrice=false"
)
NAME_URL = f"{BASE}?productIds={PRODUCT_ID}&withPrices=false&withStocks=false"
STATE = Path(__file__).parent / "price.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def norm(code):
    """'090' と '90'、'053' と '53' を同じものとして比較する。"""
    s = str(code).strip()
    return str(int(s)) if s.isdigit() else s


def fetch_name():
    try:
        body = json.loads(http(NAME_URL, headers={"Accept": "application/json"}))
        return body["result"]["items"][0].get("name", PRODUCT_ID)
    except Exception:
        return PRODUCT_ID


def fetch_price():
    """(商品名, 現在価格) を返す。色・サイズに一致する行の価格。期間限定価格があれば優先。"""
    body = json.loads(http(L2S_URL, headers={"Accept": "application/json"}))
    l2s = body["result"]["l2s"]
    found = []
    for row in l2s:
        c = row.get("color", {}).get("displayCode")
        s = row.get("size", {}).get("displayCode")
        found.append(f"色{c}/サイズ{s}")
        if norm(c) == norm(COLOR) and norm(s) == norm(SIZE):
            prices = row["prices"]
            current = (prices.get("promo") or prices["base"])["value"]
            return fetch_name(), int(current)
    raise RuntimeError(
        f"色{COLOR}・サイズ{SIZE}が見つかりません。取得できた組み合わせ: {sorted(set(found))}"
    )


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
        line_push("✅ UNIQLO 絵本コレクション パジャマ/ミッフィーの値下げ通知のテストです。LINE連携は正常です。")
        print("test message sent")

    name, price = fetch_price()
    variant = f"{PRODUCT_ID}/{COLOR}/{SIZE}"
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    # 監視対象（色・サイズ）が変わったら、前回価格は比較に使わない
    last = state.get("price") if state.get("variant") == variant else None
    print(f"{name} [色{COLOR}/サイズ{SIZE}]: 今回 {price}円 / 前回 {last}円")

    if last is not None and price < last:
        line_push(
            f"🔻 値下げ！\n{name}（色{COLOR}/サイズ{SIZE}）\n"
            f"{last:,}円 → {price:,}円（-{last - price:,}円）\n{PRODUCT_URL}"
        )
        print("notified")

    if price != last:
        STATE.write_text(
            json.dumps({"variant": variant, "price": price, "name": name}, ensure_ascii=False, indent=2) + "\n"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
