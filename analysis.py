import pandas as pd
from datetime import timedelta

# ─── CONFIG ────────────────────────────────────────────────────────────────
PUNCH_IN_FILE  = "punch_in.xlsx"   # ← your punch-in Excel
PUNCH_OUT_FILE = "punch_out.xlsx"  # ← your punch-out Excel

# Column names (adjust if your sheets use different names)
IN_COLS  = ["Persno", "in_date", "punchinsec", "tm_ev_type", "punchin_time", "emp_date_key"]
OUT_COLS = ["Emp_date_key", "punch_out_sec", "persno", "tm_ev_type", "Date", "punch_out_time"]

# Night-shift: any punch-out at or before this time is treated as the *next day* belonging to the previous day’s shift
time_threshold = pd.to_timedelta("10:00:00")
# ────────────────────────────────────────────────────────────────────────────


def load_and_prepare():
    # 1. Load data
    df_in = pd.read_excel(PUNCH_IN_FILE, usecols=IN_COLS)
    df_out = pd.read_excel(PUNCH_OUT_FILE, usecols=OUT_COLS)

    # 2. Parse in_datetimes
    #    in_date: "ddmmyyyy", punchin_time: "H:M:S"
    df_in["in_datetime"] = (
        pd.to_datetime(df_in["in_date"], format="%d%m%Y") +
        pd.to_timedelta(df_in["punchin_time"].astype(str))
    )
    
    # 3. Parse out_datetimes
    #    Date: "ddmmyyyy", punch_out_time: "H:M:S"
    df_out["out_datetime_raw"] = (
        pd.to_datetime(df_out["Date"], format="%d%m%Y") +
        pd.to_timedelta(df_out["punch_out_time"].astype(str))
    )
    # 4. Adjust overnight: if out_time ≤ 10 AM, subtract 1 day to assign to the prior shift
    mask_night = df_out["out_datetime_raw"].dt.time <= (time_threshold)
    df_out.loc[mask_night, "out_datetime"] = df_out.loc[mask_night, "out_datetime_raw"] - timedelta(days=1)
    df_out.loc[~mask_night, "out_datetime"] = df_out.loc[~mask_night, "out_datetime_raw"]

    # 5. Derive a “shift_date” for grouping: date of the shift (use the date part of in_datetime or adjusted out_datetime)
    df_in["shift_date"]  = df_in["in_datetime"].dt.normalize()
    df_out["shift_date"] = df_out["out_datetime"].dt.normalize()

    return df_in, df_out


def classify_records(df_in, df_out):
    # 1. Merge in & out on Persno and shift_date (outer to capture all cases)
    merged = (
        pd.merge(
            df_in[["Persno", "shift_date", "in_datetime"]],
            df_out[["persno", "shift_date", "out_datetime"]],
            left_on=["Persno", "shift_date"],
            right_on=["persno", "shift_date"],
            how="outer"
        )
        .rename(columns={"Persno": "Persno", "persno": "Persno"})
    )

    # 2. Classify
    def label(row):
        if pd.notna(row["in_datetime"]) and pd.notna(row["out_datetime"]):
            return "both"
        if pd.notna(row["in_datetime"]) and pd.isna(row["out_datetime"]):
            return "in_only"
        if pd.isna(row["in_datetime"]) and pd.notna(row["out_datetime"]):
            return "out_only"
        return "unknown"

    merged["status"] = merged.apply(label, axis=1)
    return merged


def main():
    df_in, df_out = load_and_prepare()
    result = classify_records(df_in, df_out)

    # 3. Split into separate DataFrames if you like:
    in_only  = result[result["status"] == "in_only"]
    out_only = result[result["status"] == "out_only"]
    both     = result[result["status"] == "both"]

    # 4. Export or inspect:
    in_only.to_excel("in_without_out.xlsx", index=False)
    out_only.to_excel("out_without_in.xlsx", index=False)
    both.to_excel("with_both.xlsx", index=False)

    print("Done! Reports:")
    print(f" • In without out:  {len(in_only)} rows → in_without_out.xlsx")
    print(f" • Out without in:  {len(out_only)} rows → out_without_in.xlsx")
    print(f" • Both in+out:     {len(both)} rows → with_both.xlsx")


if __name__ == "__main__":
    main()