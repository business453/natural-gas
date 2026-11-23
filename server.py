"""Local-only market-data bridge for the MCX Natural Gas dashboard.

Read-only integration: Angel One SmartAPI streams the selected MCX Natural Gas
future; Yahoo Finance's public chart endpoint supplies a delayed NYMEX NG=F
reference quote. No order-placement endpoints are implemented.
"""
from __future__ import annotations

import os
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="MCX Natural Gas Dashboard Local Data Bridge", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

STATE_LOCK = threading.RLock()
STATE: dict[str, Any] = {
    "angel": {
        "status": "disconnected",
        "message": "Not connected. Configure the local .env file first.",
        "connected": False,
        "contract": None,
        "quote": None,
        "last_error": None,
    },
    "henry_hub": {"status": "not_loaded", "quote": None, "last_error": None},
}
ANGEL_SESSION: dict[str, Any] = {"smart": None, "ws": None, "thread": None}
CONTRACTS_CACHE: dict[str, Any] = {"loaded_at": 0.0, "contracts": []}
HH_CACHE: dict[str, Any] = {"loaded_at": 0.0, "quote": None}
# Intraday history is intentionally held in memory for the currently selected
# Angel One contract. It is cleared when a different contract is connected.
OI_HISTORY: list[dict[str, Any]] = []
MAX_OI_HISTORY = 20000

# Angel One's current SmartAPI docs publish the angelone.in host. Keep the
# legacy angelbroking.com host as a fallback because both have been used by
# SmartAPI clients and the instrument-master service has had intermittent 502/504s.
MASTER_URLS = [
    "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json",
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
]
MASTER_CACHE_FILE = BASE_DIR / "data" / "angel_instrument_master.json"
MASTER_CACHE_META: dict[str, Any] = {"source": None, "cached_at": None, "stale": False}
YAHOO_CHART_URLS = [
    "https://query1.finance.yahoo.com/v8/finance/chart/NG%3DF",
    "https://query2.finance.yahoo.com/v8/finance/chart/NG%3DF",
]


def _expiry_sort_value(raw: str) -> datetime:
    raw = (raw or "").strip().upper()
    for fmt in ("%d%b%Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.max.replace(tzinfo=timezone.utc)


def _validate_instrument_master(payload: Any) -> list[dict[str, Any]]:
    """Validate the downloaded master before it is trusted or cached."""
    if not isinstance(payload, list) or not payload:
        raise ValueError("Instrument master response was not a non-empty JSON array.")
    if not isinstance(payload[0], dict) or not {"token", "symbol", "exch_seg"}.issubset(payload[0]):
        raise ValueError("Instrument master JSON did not contain expected Angel One instrument fields.")
    return payload


def _extract_natgas_contracts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    contracts: list[dict[str, Any]] = []
    for row in rows:
        # Angel One's instrument master has used several MCX segment labels
        # over time: MCX, mcx_fo and (in some master dumps) NCO. SmartAPI's
        # WebSocket exchangeType for MCX remains 5 for all of these aliases.
        exch = str(row.get("exch_seg", "")).strip().upper().replace("-", "_")
        name = str(row.get("name", "")).upper()
        symbol = str(row.get("symbol", "")).upper()
        instrument_type = str(row.get("instrumenttype", "")).upper()
        if exch not in {"MCX", "MCX_FO", "NCO"}:
            continue
        if name != "NATURALGAS" and not symbol.startswith("NATURALGAS"):
            continue
        if instrument_type not in ("FUTCOM", "FUT") and not symbol.endswith("FUT"):
            continue
        expiry_raw = str(row.get("expiry", ""))
        expiry_dt = _expiry_sort_value(expiry_raw)
        if expiry_dt.year < 9000 and expiry_dt.date() < today:
            continue
        token = str(row.get("token", ""))
        if not token:
            continue
        try:
            lot_size = int(float(row.get("lotsize", 0) or 0))
        except (TypeError, ValueError):
            lot_size = 0
        try:
            tick_size = float(row.get("tick_size", 0) or 0)
        except (TypeError, ValueError):
            tick_size = 0.0
        contracts.append({
            "token": token,
            "symbol": str(row.get("symbol", "")),
            "expiry": expiry_raw or "Unknown",
            "expiry_sort": expiry_dt.isoformat(),
            "lot_size": lot_size,
            "tick_size": tick_size,
        })
    contracts.sort(key=lambda x: x["expiry_sort"])
    return contracts


def _read_disk_master() -> tuple[list[dict[str, Any]] | None, str | None]:
    try:
        if not MASTER_CACHE_FILE.exists():
            return None, None
        payload = json.loads(MASTER_CACHE_FILE.read_text(encoding="utf-8"))
        return _validate_instrument_master(payload), datetime.fromtimestamp(
            MASTER_CACHE_FILE.stat().st_mtime, tz=timezone.utc
        ).isoformat()
    except Exception:
        return None, None


def get_natgas_contracts(force: bool = False) -> list[dict[str, Any]]:
    """Load current Angel One MCX NG futures; use a dated local cache on outages."""
    now = time.time()
    if CONTRACTS_CACHE["contracts"] and not force and now - CONTRACTS_CACHE["loaded_at"] < 6 * 3600:
        return CONTRACTS_CACHE["contracts"]

    errors: list[str] = []
    rows: list[dict[str, Any]] | None = None
    loaded_from: str | None = None
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MCX-NG-Dashboard/1.1)",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    # Retry each official host once. The Angel One master endpoint has had
    # intermittent gateway timeouts, so do not fail after a single request.
    for url in MASTER_URLS:
        for attempt in range(2):
            try:
                response = session.get(url, timeout=(10, 35), headers=headers)
                if response.status_code != 200:
                    body_hint = " ".join(response.text[:180].split())
                    raise RuntimeError(f"HTTP {response.status_code} from {url}; response: {body_hint or 'empty body'}")
                try:
                    payload = response.json()
                except ValueError as exc:
                    body_hint = " ".join(response.text[:180].split())
                    raise RuntimeError(f"Angel One returned non-JSON content from {url}: {body_hint}") from exc
                rows = _validate_instrument_master(payload)
                loaded_from = url
                break
            except Exception as exc:
                errors.append(f"{url} (attempt {attempt + 1}): {exc}")
                if attempt == 0:
                    time.sleep(1.0)
        if rows is not None:
            break

    if rows is not None:
        try:
            MASTER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = MASTER_CACHE_FILE.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
            tmp_file.replace(MASTER_CACHE_FILE)
        except Exception as exc:
            # Downloaded data is still usable even if the local disk is read-only.
            errors.append(f"Could not save local instrument cache: {exc}")
        MASTER_CACHE_META.update({
            "source": loaded_from,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "stale": False,
        })
    else:
        rows, cached_at = _read_disk_master()
        if rows is None:
            detail = " | ".join(errors[-4:]) or "No response from Angel One instrument-master endpoints."
            raise RuntimeError(
                "Angel One's instrument-master download failed on both official hosts and no local cache exists. "
                "This is a contract-list service issue, not an Angel One login error. " + detail
            )
        MASTER_CACHE_META.update({
            "source": "Local cached Angel One instrument master (offline fallback)",
            "cached_at": cached_at,
            "stale": True,
        })

    contracts = _extract_natgas_contracts(rows)
    if not contracts:
        # Give a useful diagnosis instead of a generic empty-list message.
        seen_segments: dict[str, int] = {}
        natural_gas_candidates: list[str] = []
        for row in rows:
            seg = str(row.get("exch_seg", "<missing>")).strip().upper()
            seen_segments[seg] = seen_segments.get(seg, 0) + 1
            symbol = str(row.get("symbol", "")).upper()
            name = str(row.get("name", "")).upper()
            if name.startswith("NATURALGAS") or symbol.startswith("NATURALGAS"):
                natural_gas_candidates.append(
                    f"{symbol or '<no symbol>'} [segment={seg}, type={row.get('instrumenttype', '<missing>')}, expiry={row.get('expiry', '<missing>')}]"
                )
        segment_summary = ", ".join(f"{k}:{v}" for k, v in sorted(seen_segments.items())[:12])
        candidate_summary = "; ".join(natural_gas_candidates[:5]) or "none found"
        raise RuntimeError(
            "Instrument master loaded, but no upcoming MCX Natural Gas futures passed the contract filter. "
            f"Segments seen: {segment_summary}. Natural Gas rows: {candidate_summary}. "
            "The contract may be expired, or Angel One may have changed its instrument fields."
        )
    CONTRACTS_CACHE.update({"loaded_at": now, "contracts": contracts})
    return contracts


def fetch_henry_hub_quote(force: bool = False) -> dict[str, Any]:
    """Fetch Yahoo Finance's public NG=F chart quote. This is delayed reference data."""
    now = time.time()
    if HH_CACHE["quote"] and not force and now - HH_CACHE["loaded_at"] < 45:
        return HH_CACHE["quote"]

    errors: list[str] = []
    for url in YAHOO_CHART_URLS:
        try:
            resp = requests.get(
                url,
                params={"range": "1d", "interval": "1m", "includePrePost": "true"},
                headers={"User-Agent": "Mozilla/5.0 MCX-NG-Dashboard/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            payload = resp.json()
            result = payload.get("chart", {}).get("result")
            if not result:
                raise RuntimeError(payload.get("chart", {}).get("error", {}).get("description", "No quote returned"))
            result = result[0]
            meta = result.get("meta", {})
            timestamps = result.get("timestamp") or []
            closes = result.get("indicators", {}).get("quote", [{}])[0].get("close") or []
            last_pair = next(((ts, px) for ts, px in zip(reversed(timestamps), reversed(closes)) if px is not None), None)
            price = meta.get("regularMarketPrice")
            quote_ts = meta.get("regularMarketTime")
            if last_pair:
                ts_last, close_last = last_pair
                if price is None:
                    price = close_last
                if not quote_ts:
                    quote_ts = ts_last
            previous = meta.get("chartPreviousClose") or meta.get("previousClose")
            if price is None or previous in (None, 0):
                raise RuntimeError("Quote response did not include a usable price and previous close")
            price = float(price)
            previous = float(previous)
            quote_ts = int(quote_ts or now)
            age_seconds = max(0, int(now - quote_ts))
            quote = {
                "symbol": "NG=F",
                "name": meta.get("longName") or meta.get("shortName") or "Henry Hub Natural Gas futures",
                "price": price,
                "previous_close": previous,
                "change": price - previous,
                "change_pct": ((price - previous) / previous) * 100.0,
                "timestamp": datetime.fromtimestamp(quote_ts, tz=timezone.utc).isoformat(),
                "age_seconds": age_seconds,
                "stale": age_seconds > 30 * 60,
                "source": "Yahoo Finance public quote · NYMEX delayed reference",
                "delay_note": "Delayed quote, not an exchange-authorised real-time feed. Verify the timestamp before relying on it.",
            }
            HH_CACHE.update({"loaded_at": now, "quote": quote})
            with STATE_LOCK:
                STATE["henry_hub"] = {"status": "ok", "quote": quote, "last_error": None}
            return quote
        except Exception as exc:  # try the secondary Yahoo endpoint
            errors.append(str(exc))
    message = " | ".join(errors[-2:]) or "Henry Hub quote unavailable"
    with STATE_LOCK:
        STATE["henry_hub"] = {"status": "error", "quote": HH_CACHE.get("quote"), "last_error": message}
    if HH_CACHE.get("quote"):
        return HH_CACHE["quote"]
    raise RuntimeError(message)


class ConnectRequest(BaseModel):
    token: str


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "MCX Natural Gas local data bridge"}


@app.get("/api/angel/contracts")
def angel_contracts(refresh: bool = Query(default=False)):
    try:
        contracts = get_natgas_contracts(force=refresh)
        cached_at = MASTER_CACHE_META.get("cached_at")
        age_hours = None
        if cached_at:
            try:
                age_hours = round((datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)).total_seconds() / 3600, 1)
            except Exception:
                pass
        return {
            "contracts": [{k: v for k, v in c.items() if k != "expiry_sort"} for c in contracts],
            "master_source": MASTER_CACHE_META.get("source"),
            "master_cached_at": cached_at,
            "master_age_hours": age_hours,
            "master_is_stale": bool(MASTER_CACHE_META.get("stale")),
            "warning": (
                "Angel One's instrument-master service is currently unreachable. Contracts are being shown from a local cached copy; verify symbol and expiry in Angel One before subscribing."
                if MASTER_CACHE_META.get("stale") else None
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not load Angel One instrument master: {exc}")


def _save_tick(data: dict[str, Any], contract: dict[str, Any]) -> None:
    try:
        raw_ltp = float(data.get("last_traded_price", 0))
        if raw_ltp <= 0:
            return
        quote = {
            "symbol": contract["symbol"],
            "token": contract["token"],
            "expiry": contract["expiry"],
            "lot_size": contract.get("lot_size", 0),
            "price": raw_ltp / 100.0,
            "average_traded_price": float(data.get("average_traded_price", 0) or 0) / 100.0,
            "open": float(data.get("open_price_of_the_day", 0) or 0) / 100.0,
            "high": float(data.get("high_price_of_the_day", 0) or 0) / 100.0,
            "low": float(data.get("low_price_of_the_day", 0) or 0) / 100.0,
            "previous_close": float(data.get("closed_price", 0) or 0) / 100.0,
            "volume": int(data.get("volume_trade_for_the_day", 0) or 0),
            "open_interest": int(data.get("open_interest", 0) or 0),
            "exchange_timestamp": int(data.get("exchange_timestamp", 0) or 0),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "source": "Angel One SmartAPI WebSocket v2 · MCX",
        }
        with STATE_LOCK:
            STATE["angel"]["quote"] = quote
            STATE["angel"]["connected"] = True
            STATE["angel"]["status"] = "connected"
            STATE["angel"]["message"] = "Streaming market data"
            STATE["angel"]["last_error"] = None
            point = {
                "timestamp_ms": int(time.time() * 1000),
                "price": quote["price"],
                "open_interest": quote["open_interest"],
                "volume": quote["volume"],
            }
            # Keep at most one sample per second to avoid storing redundant
            # high-frequency WebSocket ticks while preserving the trend.
            if OI_HISTORY and point["timestamp_ms"] - OI_HISTORY[-1]["timestamp_ms"] < 1000:
                OI_HISTORY[-1] = point
            else:
                OI_HISTORY.append(point)
            if len(OI_HISTORY) > MAX_OI_HISTORY:
                del OI_HISTORY[: len(OI_HISTORY) - MAX_OI_HISTORY]
    except Exception as exc:
        with STATE_LOCK:
            STATE["angel"]["last_error"] = f"Could not parse market tick: {exc}"


@app.post("/api/angel/connect")
def angel_connect(body: ConnectRequest):
    required = ["ANGEL_API_KEY", "ANGEL_CLIENT_CODE", "ANGEL_PIN", "ANGEL_TOTP_SECRET"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Missing local .env settings: " + ", ".join(missing) + ". Do not send credentials in the browser or chat.",
        )

    try:
        contracts = get_natgas_contracts()
        contract = next((c for c in contracts if c["token"] == body.token), None)
        if not contract:
            raise HTTPException(status_code=400, detail="Selected MCX Natural Gas contract token is not in the current instrument master. Refresh the contract list.")

        # Disconnect any previous stream before creating a new login/session.
        _disconnect_angel(silent=True)

        import pyotp
        from SmartApi import SmartConnect
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2

        api_key = os.environ["ANGEL_API_KEY"].strip()
        client_code = os.environ["ANGEL_CLIENT_CODE"].strip()
        smart = SmartConnect(api_key)
        totp_value = os.environ["ANGEL_TOTP_SECRET"].strip()
        totp_generator = pyotp.parse_uri(totp_value) if totp_value.lower().startswith("otpauth://") else pyotp.TOTP(totp_value)
        login = smart.generateSession(client_code, os.environ["ANGEL_PIN"].strip(), totp_generator.now())
        if not login or not login.get("status") or not login.get("data", {}).get("jwtToken"):
            raise RuntimeError((login or {}).get("message", "Angel One login failed. Check API app, PIN and TOTP settings."))
        auth_token = login["data"]["jwtToken"]
        feed_token = login["data"].get("feedToken") or smart.getfeedToken()
        if not feed_token:
            raise RuntimeError("Angel One login succeeded but no feed token was returned.")

        with STATE_LOCK:
            OI_HISTORY.clear()
            STATE["angel"].update({
                "status": "connecting", "message": "Login successful; opening MCX market-data stream…",
                "connected": False, "contract": {k: v for k, v in contract.items() if k != "expiry_sort"},
                "quote": None, "last_error": None,
            })

        sws = SmartWebSocketV2(auth_token, api_key, client_code, feed_token, max_retry_attempt=8, retry_strategy=1, retry_delay=5)

        def on_open(wsapp):
            with STATE_LOCK:
                STATE["angel"]["status"] = "subscribing"
                STATE["angel"]["message"] = "WebSocket connected; subscribing to MCX quote…"
            sws.subscribe(
                "NGMCX0001",
                3,  # SNAP_QUOTE includes price, volume, average price and OI fields
                [{"exchangeType": 5, "tokens": [contract["token"]]}],
            )

        def on_data(wsapp, message):
            if isinstance(message, dict) and str(message.get("token", "")) == contract["token"]:
                _save_tick(message, contract)

        def on_error(*args):
            err = " ".join(str(x) for x in args[-2:])
            with STATE_LOCK:
                STATE["angel"]["last_error"] = err[:500]
                if not STATE["angel"].get("connected"):
                    STATE["angel"]["status"] = "error"
                    STATE["angel"]["message"] = "Angel One WebSocket reported an error"

        def on_close(wsapp):
            with STATE_LOCK:
                STATE["angel"]["connected"] = False
                if STATE["angel"]["status"] not in ("disconnected", "stopping"):
                    STATE["angel"]["status"] = "disconnected"
                    STATE["angel"]["message"] = "Angel One market-data stream closed"

        sws.on_open = on_open
        sws.on_data = on_data
        sws.on_error = on_error
        sws.on_close = on_close

        thread = threading.Thread(target=sws.connect, name="angel-smartapi-mcx-stream", daemon=True)
        ANGEL_SESSION.update({"smart": smart, "ws": sws, "thread": thread})
        thread.start()
        return {"ok": True, "message": "Angel One login accepted. Waiting for the MCX stream.", "contract": {k: v for k, v in contract.items() if k != "expiry_sort"}}
    except HTTPException:
        raise
    except Exception as exc:
        with STATE_LOCK:
            STATE["angel"].update({"status": "error", "connected": False, "message": "Angel One connection failed", "last_error": str(exc)[:500]})
        raise HTTPException(status_code=502, detail=f"Angel One connection failed: {exc}")


def _disconnect_angel(silent: bool = False):
    ws = ANGEL_SESSION.get("ws")
    smart = ANGEL_SESSION.get("smart")
    try:
        if ws:
            with STATE_LOCK:
                STATE["angel"]["status"] = "stopping"
            ws.close_connection()
    except Exception:
        pass
    try:
        if smart and os.getenv("ANGEL_CLIENT_CODE"):
            smart.terminateSession(os.environ["ANGEL_CLIENT_CODE"].strip())
    except Exception:
        pass
    ANGEL_SESSION.update({"smart": None, "ws": None, "thread": None})
    with STATE_LOCK:
        STATE["angel"].update({"status": "disconnected", "connected": False, "message": "Disconnected", "quote": None})
    if not silent:
        return {"ok": True}


@app.post("/api/angel/disconnect")
def angel_disconnect():
    return _disconnect_angel(silent=False)


@app.get("/api/henry-hub")
def henry_hub():
    try:
        return fetch_henry_hub_quote(force=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Henry Hub public delayed quote unavailable: {exc}")


@app.get("/api/status")
def status():
    with STATE_LOCK:
        angel = dict(STATE["angel"])
        hh = dict(STATE["henry_hub"])
        # Downsample the in-memory tick history for the two-second dashboard poll.
        history = list(OI_HISTORY)
        stride = max(1, (len(history) + 899) // 900)
        oi_history = history[::stride]
        if history and (not oi_history or oi_history[-1] is not history[-1]):
            oi_history = [*oi_history, history[-1]]
    # Strip any non-serialisable values defensively.
    return {"angel": angel, "henry_hub": hh, "oi_history": oi_history}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False, log_level="info")
