# Duka Sales Exploration and Agent Network Clean-Up

**Analyst:** Timothy Kerre | **Cohort:** 1milliondevs 2026 | **Assignment:** PLP Data Analytics A3

This repository holds two client engagements: an exploration of half-year sales for a retailer (Duka Electronics), and an audit and clean-up of an unreliable mobile money agent transaction extract.

## Summary of the two engagements

**Engagement 1: Duka Electronics.** The Head of Sales wanted "answers, not just tables" for the January to June 2026 review. `duka_sales_exploration.ipynb` inspects 1,000 orders, adds derived columns (`revenue`, `month`, `weekday`, `is_weekend`, `price_band`), and answers questions on branch and product performance, weekend versus weekday orders and the best and worst month. It exports the Premium online orders from Nairobi and Mombasa, and reconciles the pandas results with an Excel workbook (`SUMIFS` revenue table, `XLOOKUP` region column and a PivotTable of revenue by branch and channel).

**Engagement 2: Mobile money agent network.** The regional manager wanted to know which agents and counties handle the most deposits and withdrawals, but the legacy extract has deliberately injected problems. `agent_cleanup.ipynb` audits the raw data across six data-quality dimensions, calls the reusable `clean_agent_data()` function from `cleaning_pipeline.py` (which returns the clean data plus a cleaning log), validates the merge with the agent register, and produces a county summary, a weekly pivot table and a Data Quality Report with a privacy paragraph.

## Duka Executive Summary

- Duka Electronics earned KES 71,792,500 from 1,000 orders between 1 January and 29 June 2026, an average of KES 71,792.50 per order.
- Nairobi is the strongest branch, with KES 26,106,100 in revenue (36.4% of the total, almost double Mombasa's 19.5%) and the most orders (376 of 1,000).
- Laptops generate 57.9% of revenue (KES 41,535,000) from only 22.0% of orders, while Tablets sell the most units (691 against 639 for Laptops).
- Premium online orders from Nairobi and Mombasa total 83 orders worth KES 10,218,000 (14.2% of all revenue), and online orders are worth as much as in-store ones (KES 71,207 against KES 70,759 on average), so growing online sales is worthwhile.
- Revenue peaked in April at KES 13,518,300 and was lowest in June at KES 10,903,400, a 24.0% gap, so promotions should target the May to June slowdown.

## Agent data: before and after cleaning

| | Rows |
|---|---|
| Raw `agent_transactions.csv` | **612** |
| After cleaning (`outputs/agent_transactions_clean.csv`) | **600** |
| Removed | 12 (duplicate `txn_id` values only) |

Every other issue was corrected, imputed or flagged rather than deleted: 20 missing amounts were imputed with the median for the transaction type (flagged in `amount_imputed`), 5 dates written with `/` were parsed, `txn_type` was reduced from 5 spellings to `Deposit` and `Withdrawal`, 7 transactions from the unregistered agent `AG099` were kept with county `Unknown`, and 40 amounts outside the IQR fences were flagged in `is_outlier`. Five of these are exactly KES 250,000 and make up 46.5% of total value, so they should be verified against the source ledger.

## How to regenerate the data and run the notebooks

The raw CSV files are **not** committed to this repository. They are recreated from `generate_data.py`, which contains both dataset generators exactly as provided (Duka Electronics with seed 2026, the agent network with seed 44).

```bash
git clone https://github.com/kerre-star/plp-da-a3-duka-sales-and-agent-cleanup.git
cd plp-da-a3-duka-sales-and-agent-cleanup
pip install -r requirements.txt

python generate_data.py          # writes duka_sales.csv, agents.csv, agent_transactions.csv
jupyter notebook                 # then open and run each notebook with Run All
```

| Notebook | Open in Colab | Needs |
|---|---|---|
| `duka_sales_exploration.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kerre-star/plp-da-a3-duka-sales-and-agent-cleanup/blob/main/duka_sales_exploration.ipynb) | `duka_sales.csv` (created by `generate_data.py`), `excel/duka_branch_summary.xlsx` |
| `agent_cleanup.ipynb` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kerre-star/plp-da-a3-duka-sales-and-agent-cleanup/blob/main/agent_cleanup.ipynb) | `agents.csv` and `agent_transactions.csv` (created by `generate_data.py`), `cleaning_pipeline.py` |

Each notebook's first code cell checks for the files it needs. It clones this repository when opened in Colab and runs `generate_data.py` when the raw CSVs are missing, so **Runtime > Run all** works from a fresh session.

## Repository contents

| Path | Purpose |
|---|---|
| `generate_data.py` | Both dataset generators, unchanged |
| `duka_sales_exploration.ipynb` | Engagement 1 notebook (Executive Summary, inspection, Tasks 1-8) |
| `excel/duka_branch_summary.xlsx` | `SUMIFS` branch revenue table, `XLOOKUP` region column, branch by channel PivotTable |
| `outputs/premium_online_coast_capital.csv` | Premium online orders from Nairobi and Mombasa (83 rows) |
| `cleaning_pipeline.py` | `clean_agent_data(txns, agents)` returning `(clean_df, log)` |
| `agent_cleanup.ipynb` | Engagement 2 notebook (audit, cleaning, merge validation, summaries, Data Quality Report) |
| `outputs/agent_transactions_clean.csv` | Cleaned and merged agent transactions (600 rows) |
| `requirements.txt` | Libraries used: pandas, numpy, openpyxl |
