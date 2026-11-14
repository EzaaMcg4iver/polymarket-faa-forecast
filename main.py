"""polymarket-faa-attribution-02 entry (Python 3.13, standard library only).

Per-market adaptive forecaster of Polymarket Yes prices, 240 minutes ahead,
as five quantiles a minute.

Method (tuned on the six practice cases, kept deliberately simple and robust):
  * Volatility: RMS of the 1-minute price changes over the trailing 120
    minutes, floored at 0.0002 and capped at 0.006 price units per minute,
    scaled by 0.8. The 120-minute window is what predicts the next hours
    (a 24-hour window is polluted by launch moves and hurts badly); markets
    that barely move get tight quantiles, jumpy ones get wide ones.
  * Horizon shape: Ornstein-Uhlenbeck saturation, sd(h) =
    sigma * sqrt(120 * (1 - exp(-h / 120))). Variance grows like a random
    walk at first, then saturates: prices are bounded and mean-revert, so a
    plain sqrt(h) spread is too wide at h = 240.
  * Median: last price, pulled 10% of the way back toward the price 60
    minutes ago, phased in linearly over the horizon. Recent moves
    mean-revert in the practice (corr -0.36 between the last hour's change
    and the next 4 hours' change), so the median leans against them.
  * Quantiles: normal z-scores, outer levels (5% / 95%) widened by 1.1x for
    the heavy jump tails, clamped to [0, 1], rounded to 6 decimals,
    enforced non-decreasing within each row.
  * Nothing depends on market names, the event, or the number of markets:
    only each case file's own prices, horizon and quantiles. Deterministic:
    no clock, no randomness, inputs read in name order.

Usage: MAKEFUN_INPUT_DIR=<dir> MAKEFUN_OUTPUT_DIR=<dir> python3 main.py
(defaults /input and /output).
"""

import json
import math
import os
from os import path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]

SIGMA_WINDOW = 120      # trailing minutes for the volatility estimate
SIGMA_FLOOR = 0.0002    # price units per minute
SIGMA_CAP = 0.006       # price units per minute
SIGMA_MULT = 0.8        # global shrink (practice-optimal, near-flat 0.7-0.9)
OU_TAU = 120.0          # minutes; OU saturation timescale
REVERSION = 0.1         # fraction of the last hour's move pulled back
REVERSION_WINDOW = 60   # minutes
Z_OUTER_MULT = 1.1      # extra width on the 5% / 95% quantiles


def round6(x):
    """Clamp to [0, 1] and round to 6 decimals (0, never -0)."""
    if x < 0.0:
        x = 0.0
    elif x > 1.0:
        x = 1.0
    return round(x, 6) + 0.0


def forecast_market(prices, horizon):
    """240 rows of five quantiles for one market's price list."""
    n = len(prices)
    if n == 0:
        # No history at all: flat 0.5 keeps the case valid.
        return [[0.5, 0.5, 0.5, 0.5, 0.5] for _ in range(horizon)]
    x = float(prices[-1])

    # Per-minute volatility from the trailing window (RMS of 1-minute changes).
    lo = n - 1 - SIGMA_WINDOW
    if lo < 0:
        lo = 0
    ss = 0.0
    cnt = 0
    for i in range(lo, n - 1):
        d = float(prices[i + 1]) - float(prices[i])
        ss += d * d
        cnt += 1
    sigma = math.sqrt(ss / cnt) if cnt > 0 else 0.0
    # Scale first, then floor/cap: the cap bounds the effective spread (0.006),
    # the floor keeps a never-moving market from collapsing to a point.
    sigma = min(max(sigma * SIGMA_MULT, SIGMA_FLOOR), SIGMA_CAP)

    # Mean reversion: how far the price moved in the last hour.
    k = REVERSION_WINDOW if n - 1 >= REVERSION_WINDOW else n - 1
    recent_move = x - float(prices[n - 1 - k]) if k > 0 else 0.0

    rows = []
    for h in range(1, horizon + 1):
        gh = h / horizon
        med = x - REVERSION * recent_move * gh
        sd = sigma * math.sqrt(OU_TAU * (1.0 - math.exp(-h / OU_TAU)))
        row = []
        for j, z in enumerate(Z):
            zz = z * Z_OUTER_MULT if j == 0 or j == 4 else z
            row.append(round6(med + zz * sd))
        for j in range(1, 5):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for fname in inputs:
        case_id = fname[: -len(".in")]
        with open(path.join(INPUT_DIR, fname), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        horizon = int(case["horizon_minutes"])
        forecasts = []
        for m in case["markets"]:
            forecasts.append({
                "id": m["id"],
                "q": forecast_market(m["prices"], horizon),
            })
        out = json.dumps({"forecasts": forecasts}, separators=(",", ":")) + "\n"
        with open(path.join(OUTPUT_DIR, case_id + ".out"), "w", encoding="utf-8") as fh:
            fh.write(out)


if __name__ == "__main__":
    main()
