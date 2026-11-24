"""Cleaning pipeline for the mobile money agent network extract.

Usage:
    from cleaning_pipeline import clean_agent_data
    clean_df, log = clean_agent_data(txns, agents)
"""

import pandas as pd

# Lower-case, stripped transaction types mapped to their standard labels.
TXN_TYPE_MAP = {"deposit": "Deposit", "withdrawal": "Withdrawal"}

# Label used for transactions whose agent is not in the agent register.
UNKNOWN_COUNTY = "Unknown"


def clean_agent_data(txns, agents):
    """Audit, clean and merge the agent transaction extract.

    Cleaning rules, applied in this order:
        1. Uniqueness: drop repeated txn_id values, keeping the first row.
        2. Consistency: standardise txn_type to "Deposit" or "Withdrawal"
           (strip spaces, ignore case).
        3. Validity: parse txn_date to datetime, accepting both "-" and "/"
           separators.
        4. Validity and completeness: convert amount to numeric. Missing,
           non-numeric (for example "N/A") and non-positive amounts are
           imputed with the median of the valid amounts for the same txn_type
           and flagged in amount_imputed.
        5. Accuracy: flag amounts outside the IQR fences (Q1 - 1.5 * IQR,
           Q3 + 1.5 * IQR, using observed amounts only) in is_outlier. Outliers
           are flagged, not removed.
        6. Consistency: left-join the agent register to add county.
           Transactions with an agent_id missing from the register are kept,
           given the county "Unknown" and marked with agent_registered = False.

    Args:
        txns (pandas.DataFrame): Raw transactions with the columns txn_id,
            agent_id, txn_type, amount and txn_date.
        agents (pandas.DataFrame): Agent register with the columns agent_id
            and county.

    Returns:
        tuple: (clean_df, log) where clean_df is the cleaned and merged
            DataFrame (one row per unique txn_id) and log is a DataFrame with
            one row per cleaning step (columns: step, dimension, issue,
            rows_affected, action).
    """
    log = []

    def record(step, dimension, issue, rows, action):
        log.append({"step": step, "dimension": dimension, "issue": issue,
                    "rows_affected": int(rows), "action": action})

    df = txns.copy()
    rows_in = len(df)

    # 1. Uniqueness ---------------------------------------------------------
    dup_mask = df["txn_id"].duplicated(keep="first")
    df = df.loc[~dup_mask].copy()
    record(1, "Uniqueness", "Duplicate txn_id rows", dup_mask.sum(),
           "Dropped repeated txn_id values, keeping the first occurrence")

    # 2. Consistency: txn_type ---------------------------------------------
    original_type = df["txn_type"].astype(str)
    clean_type = original_type.str.strip().str.lower().map(TXN_TYPE_MAP)
    record(2, "Consistency", "txn_type not already 'Deposit' or 'Withdrawal'",
           (original_type != clean_type).sum(),
           "Stripped spaces, ignored case and mapped to Deposit/Withdrawal")
    record(2, "Consistency", "txn_type values that could not be mapped",
           clean_type.isna().sum(), "None expected; any would be left as missing")
    df["txn_type"] = clean_type

    # 3. Validity: txn_date -------------------------------------------------
    original_date = df["txn_date"].astype(str).str.strip()
    parsed_date = pd.to_datetime(original_date.str.replace("/", "-", regex=False),
                                 format="%Y-%m-%d", errors="coerce")
    record(3, "Validity", "txn_date written with '/' instead of '-'",
           original_date.str.contains("/", regex=False).sum(),
           "Replaced '/' with '-' and parsed as datetime")
    record(3, "Validity", "txn_date that could not be parsed",
           parsed_date.isna().sum(), "None expected; any would be left as NaT")
    df["txn_date"] = parsed_date

    # 4. Validity and completeness: amount ---------------------------------
    raw_amount = df["amount"]
    numeric_amount = pd.to_numeric(raw_amount, errors="coerce")
    not_numeric = raw_amount.notna() & numeric_amount.isna()
    non_positive = numeric_amount <= 0
    numeric_amount = numeric_amount.where(~non_positive)
    imputed = numeric_amount.isna()

    record(4, "Completeness", "Missing amount (blank, or 'N/A' read as NaN by pandas)",
           raw_amount.isna().sum(), "Flagged for imputation")
    record(4, "Validity", "Non-numeric amount text", not_numeric.sum(),
           "Coerced to missing and flagged for imputation")
    record(4, "Validity", "Zero or negative amount", non_positive.sum(),
           "Treated as invalid and flagged for imputation")

    median_by_type = numeric_amount.groupby(df["txn_type"]).transform("median")
    fill_values = median_by_type.fillna(numeric_amount.median())
    df["amount"] = numeric_amount.fillna(fill_values)
    df["amount_imputed"] = imputed
    record(4, "Completeness", "Amounts imputed with the median for the txn_type",
           imputed.sum(), "Filled and flagged in amount_imputed")

    # 5. Accuracy: IQR outliers --------------------------------------------
    observed = df.loc[~df["amount_imputed"], "amount"]
    q1, q3 = observed.quantile(0.25), observed.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df["is_outlier"] = ((df["amount"] > upper) | (df["amount"] < lower)) & ~df["amount_imputed"]
    record(5, "Accuracy",
           f"Amounts outside IQR fences ({lower:,.0f} to {upper:,.1f} KES)",
           df["is_outlier"].sum(), "Flagged in is_outlier; not removed")

    # 6. Consistency: merge with the agent register ------------------------
    register = agents[["agent_id", "county"]].drop_duplicates("agent_id")
    rows_before_merge = len(df)
    df = df.merge(register, on="agent_id", how="left", validate="many_to_one")
    assert len(df) == rows_before_merge, "Merge changed the number of transactions"

    df["agent_registered"] = df["county"].notna()
    unknown_agents = ~df["agent_registered"]
    df["county"] = df["county"].fillna(UNKNOWN_COUNTY)
    record(6, "Consistency", "Transactions whose agent_id is not in the agent register",
           unknown_agents.sum(),
           f"Kept (left join), county set to '{UNKNOWN_COUNTY}', agent_registered = False")

    record(0, "Summary", f"Rows in {rows_in:,} -> rows out {len(df):,}",
           rows_in - len(df), "Only exact txn_id duplicates were removed")

    clean_df = df[["txn_id", "agent_id", "txn_type", "amount", "txn_date",
                   "amount_imputed", "is_outlier", "county", "agent_registered"]]
    log_df = pd.DataFrame(log).sort_values("step", kind="stable").reset_index(drop=True)
    return clean_df.reset_index(drop=True), log_df
