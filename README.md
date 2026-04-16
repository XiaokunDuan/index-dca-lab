# Index DCA Lab

A clean, scriptable research toolkit for studying long-horizon dollar-cost averaging (DCA) in equity indexes and ETFs.

It supports:

- Weekly and monthly DCA backtests
- Rolling-window studies across multiple holding periods
- Fixed buy-day comparisons, such as Monday through Friday or the nth trading day of each month
- Optional drawdown-triggered add-on purchases
- Local CSV workflows for verified historical index data
- Report and chart generation for research outputs

## Example Research Outputs

Normalized spot-index paths from a common start date:

![Normalized index paths](docs/assets/plot_indices_normalized_since_1985.png)

Positive-return rate by holding horizon:

![Positive return rate](docs/assets/plot_positive_rate.png)

Median versus worst rolling-window CAGR:

![CAGR summary](docs/assets/plot_cagr_summary.png)

Weekly buy-day sensitivity for SPY:

![SPY weekday curves](docs/assets/plot_spy_weekly_weekday_curves.png)

## Design Goals

- Keep the backtest engine simple and auditable
- Separate local data from source control
- Support both ETF-based studies and spot index studies
- Make long-run DCA research repeatable from the command line

## Repository Policy

This repository does **not** include local datasets or generated report artifacts.

- `data/` is ignored by Git
- Place your own datasets under `data/processed/`
- Generated CSV reports and PNG charts are written under `data/reports/`

Expected local CSV schema:

```text
date,open,high,low,close,adj_close,volume,symbol
```

Example local paths:

```text
data/processed/sp500_daily.csv
data/processed/ndx100_daily.csv
```

## Installation

```bash
git clone <your-repo-url>
cd index-dca-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Quick Start

Fetch ETF history through Yahoo Finance:

```bash
python -m dca_backtest.cli fetch \
  --symbol SPY \
  --start 1993-01-22 \
  --end 2026-04-15
```

Run a basic DCA backtest from local spot index data:

```bash
python -m dca_backtest.cli backtest \
  --provider local-csv \
  --csv-path data/processed/sp500_daily.csv \
  --symbol SP500 \
  --start 1927-12-30 \
  --end 2026-04-10 \
  --frequency monthly \
  --base-contribution 1000 \
  --monthly-anchor 1
```

Run a rolling DCA study with progress bars:

```bash
python -m dca_backtest.cli study-dca \
  --dataset SP500=data/processed/sp500_daily.csv \
  --dataset NDX100=data/processed/ndx100_daily.csv \
  --frequencies monthly weekly \
  --horizons 5 10 15 20 30 \
  --contribution 1000 \
  --start 1985-10-01 \
  --end 2026-04-10 \
  --output-dir data/reports_aligned
```

Render charts from those reports:

```bash
python -m dca_backtest.cli plot-dca \
  --reports-dir data/reports_aligned \
  --sp500-csv data/processed/sp500_daily.csv \
  --ndx100-csv data/processed/ndx100_daily.csv \
  --start 1985-10-01 \
  --end 2026-04-10
```

## CLI Commands

`fetch`
- Fetch and cache ETF history from Yahoo Finance

`backtest`
- Run a single DCA or DCA-plus-drawdown strategy

`scan`
- Run a grid scan over drawdown thresholds and multipliers

`study-dca`
- Run rolling-window DCA studies with terminal progress bars

`plot-dca`
- Generate PNG charts from rolling-study outputs

## Core Rules

- Execution price: `adj_close`
- Weekly mode: buy on a fixed weekday
- Monthly mode: buy on the nth trading day of each month
- Drawdown rule: current `adj_close` relative to the running peak
- Each drawdown threshold triggers only once per drawdown cycle
- Threshold state resets after a new high

## Outputs

Typical study outputs include:

- Total contributed capital
- Final portfolio value
- Total return
- Approximate CAGR proxy
- Rolling-window positive-return rate
- Median, worst, and best outcome by horizon
- Cashflow and trigger logs

## Notes

- This is a research tool, not investment advice.
- If you use price indexes instead of total return indexes, long-run return estimates will be conservative.
- ETF `adj_close` is useful, but still not identical to real-world after-tax investor outcomes.
- For strict DCA performance measurement, prefer `XIRR` over a simple aggregate CAGR proxy.

## Project Layout

```text
dca_backtest/   core engine, providers, CLI, study and plotting modules
scripts/        one-off data cleaning and chart scripts
tests/          unit tests
data/           local-only datasets and generated reports (ignored by Git)
```
