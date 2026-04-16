# Index DCA Lab

A public, scriptable research repository for studying long-horizon index investing, dollar-cost averaging, drawdowns, recovery cycles, inflation-adjusted returns, valuation regimes, and lump-sum versus DCA tradeoffs.

This repository is designed for one purpose: make long-run equity-index research reproducible, visual, and easy to extend.

## What This Repository Covers

This project currently includes research workflows for:

- Spot index path comparison
- Weekly and monthly DCA studies
- Buy-and-hold rolling-window studies
- Fixed weekday and monthly trading-day sensitivity
- Drawdown depth and recovery-cycle analysis
- Worst-start-date stress tests
- DCA frequency comparison
- Real-return analysis using CPI
- Wealth-path analysis for ongoing DCA
- CAPE regime analysis for future SP500 returns
- Lump sum versus DCA comparisons

The core focus is:

- `SP500`
- `NDX100`
- `SPY`
- `QQQ`

with local CSV support so research can be run against verified local datasets rather than fragile online endpoints.

## Research Questions

This repo is built around questions that matter for real investors:

- How often does long-term index investing actually work?
- How much does the starting date matter?
- How painful are the worst drawdowns?
- How long do major crashes take to recover?
- Does DCA materially improve survival in bad regimes?
- Does contribution frequency matter enough to optimize?
- How much of nominal return survives inflation?
- Does starting valuation meaningfully shape long-run outcomes?
- When does lump sum beat DCA, and when does DCA protect the investor?

## Data Policy

This repository is public, but **local datasets are not committed**.

- `data/` is ignored by Git
- Put your own local datasets under `data/processed/`
- Generated reports and charts are written to `data/reports/`
- Presentation-ready images are copied into `docs/assets/` for the public repository

Expected local CSV schema:

```text
date,open,high,low,close,adj_close,volume,symbol
```

Typical local files:

```text
data/processed/sp500_daily.csv
data/processed/ndx100_daily.csv
```

## Installation

```bash
git clone https://github.com/XiaokunDuan/index-dca-lab.git
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

Run a basic local-CSV backtest:

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

Render the standard DCA report charts:

```bash
python -m dca_backtest.cli plot-dca \
  --reports-dir data/reports_aligned \
  --sp500-csv data/processed/sp500_daily.csv \
  --ndx100-csv data/processed/ndx100_daily.csv \
  --start 1985-10-01 \
  --end 2026-04-10
```

## Research Gallery

### 1. Spot Index Behavior

Normalized SP500 versus NDX100 from a common start date:

![Normalized index paths](docs/assets/plot_indices_normalized_since_1985.png)

Direct SP500 versus NDX100 spot-index comparison:

![SP500 vs NDX100](docs/assets/plot_sp500_vs_ndx100_index.png)

SP500 long-run history:

![SP500 long run](docs/assets/plot_sp500_long_run.png)

NDX100 long-run history:

![NDX100 long run](docs/assets/plot_ndx100_long_run.png)

Bridge from long index history to ETFs:

![Index to ETF bridge](docs/assets/plot_index_etf_bridge.png)

### 2. DCA Rolling-Window Studies

Positive-return rate by holding horizon:

![Positive return rate](docs/assets/plot_positive_rate.png)

Median versus worst rolling-window CAGR:

![CAGR summary](docs/assets/plot_cagr_summary.png)

Full-period DCA summary:

![Full period summary](docs/assets/plot_full_period_summary.png)

### 3. Drawdowns and Recovery Cycles

SP500 versus NDX100 drawdown comparison:

![Drawdown comparison](docs/assets/plot_sp500_vs_ndx100_drawdowns.png)

NDX100 versus SPY drawdown comparison:

![NDX100 vs SPY drawdowns](docs/assets/plot_ndx100_vs_spy_drawdowns.png)

Recovery math after large losses:

![Drawdown recovery math](docs/assets/plot_drawdown_recovery_math.png)

Major recovery cycles, ranked by severity:

![Recovery cycles top](docs/assets/plot_drawdown_recovery_cycles_top.png)

Recovery-cycle scatter plot:

![Recovery cycles scatter](docs/assets/plot_drawdown_recovery_cycles_scatter.png)

The 2000 bubble peak through eventual recovery:

![2000 recovery comparison](docs/assets/plot_2000_ndx100_vs_sp500_recovery.png)

### 4. Buy-and-Hold at Arbitrary Start Dates

Buy-and-hold positive-return rate by horizon:

![Buy and hold positive rate](docs/assets/plot_buy_hold_positive_rate.png)

Buy-and-hold median versus worst CAGR:

![Buy and hold CAGR](docs/assets/plot_buy_hold_cagr_summary.png)

Shared-horizon comparison between SP500 and NDX100:

![Buy and hold holding periods](docs/assets/plot_buy_hold_holding_periods.png)

### 5. Timing Sensitivity Inside the Calendar

SPY weekday sensitivity:

![SPY weekday curves](docs/assets/plot_spy_weekly_weekday_curves.png)

SPY monthly trading-day sensitivity:

![SPY monthly trading day curves](docs/assets/plot_spy_monthly_trading_day_curves.png)

### 6. Worst Start Dates

Worst historical start dates: lump sum versus DCA:

![Worst start lump sum vs DCA](docs/assets/plot_worst_start_lump_vs_dca.png)

Worst-start median outcome summary:

![Worst start summary](docs/assets/plot_worst_start_summary.png)

### 7. DCA Frequency Comparison

Positive-return rate across weekly, monthly, quarterly, and yearly schedules:

![DCA frequency positive rate](docs/assets/plot_dca_frequency_positive_rate.png)

Median CAGR across DCA frequencies:

![DCA frequency CAGR](docs/assets/plot_dca_frequency_cagr.png)

Full-period comparison of DCA frequencies:

![DCA frequency full period](docs/assets/plot_dca_frequency_full_period.png)

### 8. Inflation-Adjusted Real Returns

Nominal versus real positive-return rates:

![Real positive rate](docs/assets/plot_real_buy_hold_positive_rate.png)

Nominal versus real median CAGR:

![Real CAGR summary](docs/assets/plot_real_buy_hold_cagr_summary.png)

Nominal versus real long-run index growth:

![Real vs nominal growth](docs/assets/plot_real_vs_nominal_index_growth.png)

### 9. Wealth Paths Instead of Endpoints

SP500 monthly DCA wealth path:

![SP500 wealth path](docs/assets/plot_sp500_dca_wealth_path.png)

NDX100 monthly DCA wealth path:

![NDX100 wealth path](docs/assets/plot_ndx100_dca_wealth_path.png)

### 10. CAPE and Forward Returns

SP500 CAPE buckets versus future returns:

![CAPE bucket forward returns](docs/assets/plot_cape_bucket_forward_returns.png)

SP500 starting CAPE versus subsequent forward returns:

![CAPE scatter forward returns](docs/assets/plot_cape_scatter_forward_returns.png)

### 11. Lump Sum Versus DCA

Median outcome:

![Lump sum vs DCA median](docs/assets/plot_lump_sum_vs_dca_median.png)

Positive-return rate:

![Lump sum vs DCA positive rate](docs/assets/plot_lump_sum_vs_dca_positive_rate.png)

Worst-case outcome:

![Lump sum vs DCA worst case](docs/assets/plot_lump_sum_vs_dca_worst_case.png)

### 12. Compounding Intuition

Real SP500 long-run growth from the actual historical series:

![SP500 real 99y growth](docs/assets/plot_sp500_real_99y_growth.png)

Why 8%, 9%, and 10% compound so differently:

![Compounding comparison](docs/assets/plot_compounding_8_9_10_comparison.png)

Single-rate compounding intuition at 9%:

![Compounding 9pct](docs/assets/plot_compounding_9pct_99years.png)

## Main Findings So Far

### Long-horizon equity exposure is powerful, but the path matters

- SP500 and NDX100 both delivered strong long-run outcomes
- NDX100 historically compounded faster, but with much deeper drawdowns
- SP500 generally offered a better holding experience

### Drawdowns are survivability problems, not just temporary losses

- NDX100 experienced an `-82.9%` drawdown after the 2000 bubble
- That episode took about `15.6 years` from peak to full recovery
- SP500 suffered less in the same broad era and recovered materially earlier

### DCA is usually not the return-maximizing choice, but it improves robustness

- Lump sum often wins on median return because capital gets invested earlier
- DCA often improves positive-return odds and worst-case outcomes
- DCA is especially valuable when starting points are unlucky

### Frequency matters less than consistency

- Weekly, monthly, quarterly, and yearly DCA do not produce radically different long-run results
- The investor’s ability to keep contributing matters more than optimizing the schedule

### Inflation materially changes the story

- Nominal returns overstate purchasing-power growth
- SP500 looks meaningfully weaker once returns are deflated by CPI
- NDX100 remains strong in real terms, but its path remains harsher

### Starting valuation matters, especially over 10 to 20 years

- Low starting CAPE regimes produced materially higher forward returns
- High CAPE regimes still worked over very long windows, but usually at lower rates
- This does not turn valuation into a precise timing tool, but it clearly affects forward return expectations

## Repository Layout

```text
dca_backtest/   engine, providers, CLI, rolling-study logic, plotting helpers
scripts/        standalone research scripts for one-off studies and charts
tests/          unit tests
data/           local-only datasets and generated reports (ignored by Git)
docs/assets/    public chart assets embedded in the README
```

## Core CLI Commands

`fetch`
- Fetch and cache ETF history through Yahoo Finance

`backtest`
- Run a single DCA or DCA-plus-drawdown strategy

`scan`
- Run a threshold and multiplier grid scan for drawdown-buy logic

`study-dca`
- Run rolling-window DCA studies with terminal progress bars

`plot-dca`
- Generate standard study plots from rolling-window DCA outputs

## Core Research Scripts

Key scripts under `scripts/`:

- `clean_excel_indices.py`
- `plot_sp500_vs_ndx100.py`
- `plot_sp500_vs_ndx100_drawdowns.py`
- `plot_drawdown_recovery_cycles.py`
- `plot_drawdown_recovery_math.py`
- `plot_buy_hold_win_rates.py`
- `plot_worst_start_study.py`
- `plot_dca_frequency_comparison.py`
- `plot_real_return_study.py`
- `plot_dca_wealth_paths.py`
- `plot_cape_forward_return_study.py`
- `plot_lump_sum_vs_dca_study.py`
- `plot_spy_schedule_curves.py`
- `plot_2000_recovery_compare.py`

## Reproducibility Notes

- Price-index studies are conservative relative to true total-return studies
- ETF `adj_close` captures splits and distributions but is still not a full after-tax investor experience
- Real-return studies use CPI and therefore begin only where CPI coverage is available
- Some charts compare spot indexes and ETFs separately; those are related but not identical objects

## Notes and Limitations

- This is a research repository, not investment advice
- Results depend on data quality and return convention
- Long-run U.S. equity success should not be blindly generalized to every market
- Median outcomes and worst-case outcomes should always be read together

## License

MIT
