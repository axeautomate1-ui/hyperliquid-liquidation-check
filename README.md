# hyperliquid-liquidation-check

**How far is each of your Hyperliquid positions from liquidation?** One command, read-only, no API key.

```
$ python hlcheck.py 0x0000000000000000000000000000000000000000
0x0000…0000  (main)  account value $413
coin         side      notional         mark   liq. price   distance    lev
BTC          long        $7,068     63,920.0    60,945.38      4.65%   i22x  <-- within 5%
```

Your liquidation price is not fixed. Funding accrues, you add or remove margin, another cross position gains or loses, and the level moves underneath you. A stop you placed once does not follow it. This tool tells you where it is **now**.

## Install

Nothing to install beyond Python 3.8+. It uses the standard library only.

```
git clone https://github.com/axeautomate1-ui/hyperliquid-liquidation-check
cd hyperliquid-liquidation-check
python hlcheck.py 0xYourAddress
```

## Usage

```
python hlcheck.py 0xYourAddress                     # table of positions, closest to liquidation first
python hlcheck.py 0xYourAddress --watch 60          # re-check every 60 s, beep when a position is close
python hlcheck.py 0xYourAddress --alert 10          # flag positions within 10% instead of 5%
python hlcheck.py 0xYourAddress --json              # machine-readable output
python hlcheck.py 0xYourAddress --dex xyz           # HIP-3 markets (stocks, commodities on trade.xyz)
```

## What it shows

| column | meaning |
|---|---|
| `mark` | the exchange's mark price, the price liquidations are based on |
| `liq. price` | the liquidation price Hyperliquid reports for that position right now |
| `distance` | how far the mark price has to move to reach it, as a percentage of mark |
| `lev` | `c` cross or `i` isolated, then the leverage |
| cross maintenance margin used | for cross positions: liquidation happens when this reaches 100% |

## Safety

It only calls Hyperliquid's public `info` endpoint (`clearinghouseState`). It never asks for a private key, never signs anything and cannot place or cancel an order. Your address is sent to Hyperliquid and nowhere else.

## Want something that acts, not just warns?

A warning at 3 a.m. does not help if you are asleep. [PerpGuard](https://perpguard.com) is a trade-only agent wallet that trims a leveraged Hyperliquid position before the exchange liquidates it. The agent can place and cancel orders but can never withdraw, which Hyperliquid enforces. The first 10 accounts are free for 30 days.

No terminal? The same check runs in the browser, with a calculator for positions you have not opened yet: <https://perpguard.com/calculator>

There is also a free public feed of how much Hyperliquid open interest sits near liquidation, by asset, no key needed: <https://perpguard.com/api/v1/market/danger>

*This tool is made by the PerpGuard team. It works on its own and does not require PerpGuard.*

## License

MIT
