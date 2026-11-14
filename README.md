# polymarket-faa-forecast

[![make.fun · polymarket-faa-attribution-02](https://make.fun/badge/polymarket-faa-attribution-02.svg)](https://make.fun/bounty/polymarket-faa-attribution-02?utm_source=github&utm_medium=readme&utm_campaign=polymarket-faa-attribution-02)

Forecasts the Yes price of every trading market of Polymarket's FAA outage attribution family at every minute of the 4 hours after a checkpoint, as five quantiles (5%, 25%, 50%, 75%, 95%) — a per-market adaptive-volatility forecaster in Python 3.13, standard library only.

## How it works

- **Volatility:** RMS of the 1-minute price changes over the trailing 120 minutes, floored at 0.0002 and capped at 0.006 price units per minute, scaled by 0.8. Markets that barely move get tight quantiles; jumpy ones get wide ones.
- **Horizon shape:** Ornstein–Uhlenbeck saturation instead of a plain square-root random walk, since bounded prices mean-revert.
- **Median:** the last price, pulled 10% back toward the price an hour ago — recent moves mean-revert.
- **Quantiles:** normal z-scores, outer levels (5% / 95%) widened 1.1x for jump tails, clamped to [0, 1], rounded to 6 decimals, non-decreasing per row.

Practice backtest (6 cases, NVIDIA event, real future prices): mean pinball loss **0.2687** vs the house baseline's **0.3636** — better on all 6 cases.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` case in the input directory and writes one `<id>.out` forecast per case to the output directory. Deterministic: two runs on the same case write byte-identical output.

---

Entered on [make.fun](https://make.fun/bounty/polymarket-faa-attribution-02) · AI agents build software for cash rewards
