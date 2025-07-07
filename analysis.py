import pandas as pd

# ======= STEP 1: Load your Excel files ========
# ✅ Change these paths to match your actual files
punch_in_file = r"C:\Users\analysis\Documents\My IDEA Documents\IDEA Projects UK Time Office\Exports\Lakomery.xlsx"
punch_out_file = r"C:\Users\analysis\Documents\My IDEA Documents\IDEA Projects UK Time Office\Exports\ELB\punch_out_summary.xlsx"

# ✅ Load punch in and punch out data
punch_in_df = pd.read_excel(punch_in_file, parse_dates=["IN DATE"])
punch_out_df = pd.read_excel(punch_out_file, parse_dates=["DATE"])

# ======= STEP 2: Rename columns for consistency =======
punch_in_df.rename(columns={
    "PERS_NO": "Persno",
    "IN DATE": "Date_in",
    "PUNCH IN SEC MIN": "Time_sec_in"
}, inplace=True)

punch_out_df.rename(columns={
    "PERS_NO": "Persno",
    "DATE": "Date_out",
    "PUNCH_OUT SEC MAX": "Time_sec_out"
}, inplace=True)

# ======= STEP 3: Match same-day punch-in and punch-out =======
same_day_merge = pd.merge(
    punch_in_df,
    punch_out_df,
    on=["Persno"],
    how="inner"
)

valid_same_day = same_day_merge[
    (same_day_merge["Date_in"] == same_day_merge["Date_out"]) &
    (same_day_merge["Time_sec_out"] > same_day_merge["Time_sec_in"])
]

# ======= STEP 4: Match night-shift (next-day) punch-outs =======
punch_in_df["Next_Date"] = punch_in_df["Date_in"] + pd.Timedelta(days=1)

next_day_merge = pd.merge(
    punch_in_df,
    punch_out_df,
    left_on=["Persno", "Next_Date"],
    right_on=["Persno", "Date_out"],
    how="inner"
)

valid_next_day = next_day_merge[
    next_day_merge["Time_sec_out"] > next_day_merge["Time_sec_in"]
]

# ======= STEP 5: Combine valid matched pairs =======
valid_pairs = pd.concat([
    valid_same_day[["Persno", "Date_in", "Time_sec_in", "Date_out", "Time_sec_out"]],
    valid_next_day[["Persno", "Date_in", "Time_sec_in", "Date_out", "Time_sec_out"]]
]).drop_duplicates()

# ======= STEP 6: Find unmatched Punch-Ins =======
matched_in_keys = valid_pairs[["Persno", "Date_in"]].drop_duplicates()

punch_in_no_out = pd.merge(
    punch_in_df,
    matched_in_keys,
    on=["Persno", "Date_in"],
    how="left",
    indicator=True
).query('_merge == "left_only"').drop(columns=["_merge", "Next_Date"])

# ======= STEP 7: Find unmatched Punch-Outs =======
matched_out_keys = valid_pairs[["Persno", "Date_out"]].drop_duplicates()

punch_out_no_in = pd.merge(
    punch_out_df,
    matched_out_keys,
    on=["Persno", "Date_out"],
    how="left",
    indicator=True
).query('_merge == "left_only"').drop(columns=["_merge"])

# ======= STEP 8: Export all to Excel with 3 sheets =======
output_file = "Corrected_Punch_Report.xlsx"

with pd.ExcelWriter(output_file) as writer:
    valid_pairs.to_excel(writer, sheet_name="Matched_Pairs", index=False)
    punch_in_no_out.to_excel(writer, sheet_name="PunchIn_Only", index=False)
    punch_out_no_in.to_excel(writer, sheet_name="PunchOut_Only", index=False)

print(f"✅ Analysis complete! File saved as: {output_file}")