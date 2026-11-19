#!/usr/bin/env python3
"""hyperliquid-liquidation-check: how far is each Hyperliquid position from liquidation?

Read-only. No API key, no wallet, no signature: it only calls Hyperliquid's
public info endpoint. Standard library only, Python 3.8+.

    python hlcheck.py 0xYourAddress
    python hlcheck.py 0xYourAddress --watch 60 --alert 5
    python hlcheck.py 0xYourAddress --json
    python hlcheck.py 0xYourAddress --dex xyz        # HIP-3 markets (stocks, commodities)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request

API = "https://api.hyperliquid.xyz/info"
UA = "hyperliquid-liquidation-check/1.0"


def info(payload: dict, timeout: float = 20.0) -> dict:
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def read_account(address: str, dex: str = "") -> dict:
    """Positions with mark price, liquidation price and distance to it."""
    payload = {"type": "clearinghouseState", "user": address}
    if dex:
        payload["dex"] = dex
    state = info(payload)
    positions = []
    for item in state.get("assetPositions", []):
        p = item.get("position", {})
        size = _f(p.get("szi")) or 0.0
        if size == 0:
            continue
        value = abs(_f(p.get("positionValue")) or 0.0)
        mark = value / abs(size) if size else None
        liq = _f(p.get("liquidationPx"))
        distance = abs(mark - liq) / mark if (mark and liq) else None
        lev = p.get("leverage") or {}
        positions.append({
            "coin": p.get("coin"),
            "side": "long" if size > 0 else "short",
            "size": abs(size),
            "notional": value,
            "entry": _f(p.get("entryPx")),
            "mark": mark,
            "liquidation": liq,
            "distance": distance,           # fraction of mark price, None = no liquidation price
            "leverage": "%s%sx" % (lev.get("type", "")[:1], lev.get("value", "")),
            "unrealized_pnl": _f(p.get("unrealizedPnl")),
        })
    positions.sort(key=lambda x: (x["distance"] is None, x["distance"] or 0))
    cross = state.get("crossMarginSummary") or {}
    value = _f(cross.get("accountValue")) or 0.0
    maint = _f(state.get("crossMaintenanceMarginUsed")) or 0.0
    return {
        "address": address,
        "dex": dex or "main",
        "time": int(time.time()),
        "account_value": _f((state.get("marginSummary") or {}).get("accountValue")),
        # Cross positions are liquidated when account value falls to the
        # maintenance margin, so this ratio is how close the cross account is.
        "cross_maintenance_used": (maint / value) if value > 0 else None,
        "positions": positions,
    }


def _money(x) -> str:
    return "-" if x is None else ("$%s" % format(round(x), ","))


def _px(x) -> str:
    if x is None:
        return "-"
    return ("%.6g" % x) if x < 100 else format(round(x, 2), ",")


def render(acc: dict, alert: float) -> str:
    out = ["%s  (%s)  account value %s"
           % (acc["address"], acc["dex"], _money(acc["account_value"]))]
    cm = acc["cross_maintenance_used"]
    if cm is not None and cm > 0:
        out.append("cross maintenance margin used: %.1f%% (liquidation at 100%%)" % (cm * 100))
    if not acc["positions"]:
        out.append("no open positions")
        return "\n".join(out)
    out.append("%-12s %-5s %12s %12s %12s %10s %6s" %
               ("coin", "side", "notional", "mark", "liq. price", "distance", "lev"))
    for p in acc["positions"]:
        d = p["distance"]
        flag = "  <-- within %.0f%%" % alert if (d is not None and d * 100 < alert) else ""
        out.append("%-12s %-5s %12s %12s %12s %10s %6s%s" % (
            p["coin"], p["side"], _money(p["notional"]), _px(p["mark"]),
            _px(p["liquidation"]), "-" if d is None else "%.2f%%" % (d * 100),
            p["leverage"], flag))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address", help="Hyperliquid account address (0x...)")
    ap.add_argument("--dex", default="", help="HIP-3 dex name, e.g. xyz")
    ap.add_argument("--watch", type=int, default=0, metavar="SECONDS",
                    help="re-check every N seconds (minimum 15)")
    ap.add_argument("--alert", type=float, default=5.0, metavar="PCT",
                    help="flag positions closer than PCT%% to liquidation (default 5)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", a.address):
        ap.error("address must be 0x followed by 40 hex characters")
    while True:
        try:
            acc = read_account(a.address, a.dex)
        except Exception as e:  # network or API error: report, keep watching
            print("error reading Hyperliquid: %s" % e, file=sys.stderr)
            if not a.watch:
                return 1
        else:
            if a.json:
                print(json.dumps(acc))
            else:
                print(render(acc, a.alert))
            near = [p for p in acc["positions"]
                    if p["distance"] is not None and p["distance"] * 100 < a.alert]
            if a.watch and near:
                print("\a!! %d position(s) within %.0f%% of liquidation" % (len(near), a.alert))
        if not a.watch:
            return 0
        print()
        time.sleep(max(15, a.watch))


if __name__ == "__main__":
    sys.exit(main())
