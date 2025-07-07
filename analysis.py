import pandas as pd

# Load the data
punch_in_df = pd.read_csv("punch_in.csv", parse_dates=["Date"])
punch_out_df = pd.read_csv("punch_out.csv", parse_dates=["Date"])

# Rename sec columns for uniformity
punch_in_df.rename(columns={"PunchIn_sec": "Time_sec_in"}, inplace=True)
punch_out_df.rename(columns={"PunchOut_sec": "Time_sec_out"}, inplace=True)

# Step 1: Try joining on same day
merge_same_day = pd.merge(
    punch_in_df,
    punch_out_df,
    on=["Persno", "Date"],
    how="inner"
)

valid_same_day = merge_same_day[merge_same_day["Time_sec_out"] > merge_same_day["Time_sec_in"]]

# Step 2: Try joining PunchIn with next-day PunchOut (for night shift)
punch_in_df["Next_Date"] = punch_in_df["Date"] + pd.Timedelta(days=1)

merge_next_day = pd.merge(
    punch_in_df,
    punch_out_df,
    left_on=["Persno", "Next_Date"],
    right_on=["Persno", "Date"],
    how="inner"
)

valid_next_day = merge_next_day[merge_next_day["Time_sec_out"] > merge_next_day["Time_sec_in"]]

# Step 3: Combine all valid matches
valid_punch_pairs = pd.concat([
    valid_same_day[["Persno", "Date", "Time_sec_in", "Time_sec_out"]],
    valid_next_day.rename(columns={"Date_x": "Date"})[["Persno", "Date", "Time_sec_in", "Time_sec_out"]]
])

# Drop duplicates if any
valid_punch_pairs = valid_punch_pairs.drop_duplicates()

# Step 4: PunchIn without PunchOut
punch_in_keys = valid_punch_pairs[["Persno", "Date"]].drop_duplicates()
punch_in_no_out = pd.merge(
    punch_in_df,
    punch_in_keys,
    on=["Persno", "Date"],
    how="left",
    indicator=True
).query('_merge == "left_only"').drop(columns=["_merge", "Next_Date"])

# Step 5: PunchOut without PunchIn
# For night shift: punch_out might be matched with previous day's punch_in
punch_out_keys = valid_punch_pairs[["Persno", "Date"]].drop_duplicates()
punch_out_no_in = pd.merge(
    punch_out_df,
    punch_out_keys,
    on=["Persno", "Date"],
    how="left",
    indicator=True
).query('_merge == "left_only"').drop(columns=["_merge"])

# Step 6: Export or Print Results
print("🔴 Punch In with NO Punch Out:")
print(punch_in_no_out)

print("\n🔵 Punch Out with NO Punch In:")
print(punch_out_no_in)

print("\n✅ Valid Matched Punch In & Out:")
print(valid_punch_pairs)
