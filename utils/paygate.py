#MADE_BY_NOBITA
"""BETA BOT HUB payment gateway (auto-verified UPI).

Docs: https://betapaymentgateway.up.railway.app/#docs
  POST /api/v1/payments/create   -> create order (QR + pay link)
  GET  /api/v1/payments/<id>     -> {"verified": bool, "order": {"status": PENDING|PAID|EXPIRED}}
"""
import os
import aiohttp

PAYGATE_URL = os.getenv("PAYGATE_URL", "https://betapaymentgateway.up.railway.app").rstrip("/")
_DEFAULT_KEY = "ANJALI_7cd6a2d345c8ff37784fa0d97167792994af2661c724fbef"


def _key() -> str:
    """Admin /setpaykey (saved in DB) > env PAYGATE_API_KEY > built-in key."""
    try:
        from database import cur
        row = cur.execute("SELECT value FROM settings WHERE key='paygate_key'").fetchone()
        if row and row[0]: return row[0].strip()
    except Exception:
        pass
    return (os.getenv("PAYGATE_API_KEY") or _DEFAULT_KEY).strip()

PAYGATE_API_KEY = _key()

_TIMEOUT = aiohttp.ClientTimeout(total=20)


class PayGateError(Exception):
    pass


def _headers():
    k = _key()
    if not k:
        raise PayGateError("PAYGATE_API_KEY is not set")
    return {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}


def is_enabled() -> bool:
    return bool(_key())


async def create_payment(amount: int, note: str = "", customer_email: str = "") -> dict:
    """Returns the order dict: orderId, payAmount, qrImageUrl, upiUri, payUrl, expiresAt ..."""
    body = {"amount": amount, "note": note}
    if customer_email:
        body["customerEmail"] = customer_email
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.post(f"{PAYGATE_URL}/api/v1/payments/create", json=body, headers=_headers()) as r:
            data = await r.json(content_type=None)
    if not data.get("success") or not data.get("order", {}).get("orderId"):
        raise PayGateError(str(data.get("error") or data.get("message") or data))
    return data["order"]


async def get_status(order_id: str) -> tuple[str, bool, dict]:
    """Returns (status, verified, order)."""
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
        async with s.get(f"{PAYGATE_URL}/api/v1/payments/{order_id}", headers=_headers()) as r:
            data = await r.json(content_type=None)
    order = data.get("order") or {}
    return str(order.get("status", "PENDING")).upper(), bool(data.get("verified")), order
