import pandas as pd
from datetime import datetime, timedelta

# ==== CONFIG ====
INPUT_FILE = "punch_data.csv"

# Shift timings
STAFF_SHIFTS = [
    ("07:30", "15:30"),
    ("08:00", "16:00")
]
WORKMEN_SHIFTS = [
    ("07:30", "15:30"),
    ("15:30", "23:30"),
    ("23:30", "07:30")
]

# Grace period
GRACE_MINUTES = 10

# ==== STEP 1: READ FILE ====
df = pd.read_csv(INPUT_FILE)

# Standardize column names
df.columns = df.columns.str.strip().str.lower()

# Ensure datetime format
df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y-%m-%d %H:%M")

# ==== STEP 2: Parse location ====
def parse_location(loc):
    loc = loc.lower()
    if "main" in loc:
        gate = "main"
    elif "lcm" in loc:
        gate = "lcm"
    else:
        gate = "unknown"

    if "door 1" in loc:
        punch_type = "in"
    elif "door 2" in loc:
        punch_type = "out"
    else:
        punch_type = "unknown"

    return gate, punch_type

df[["gate", "punch_type"]] = df["location"].apply(lambda x: pd.Series(parse_location(x)))

# ==== STEP 3: Assign shift times ====
def get_shift_times(emp_type, punch_dt):
    if emp_type.lower() == "staff":
        for start, end in STAFF_SHIFTS:
            start_dt = datetime.combine(punch_dt.date(), datetime.strptime(start, "%H:%M").time())
            end_dt = datetime.combine(punch_dt.date(), datetime.strptime(end, "%H:%M").time())
            return start_dt, end_dt
    else:
        for start, end in WORKMEN_SHIFTS:
            start_dt = datetime.combine(punch_dt.date(), datetime.strptime(start, "%H:%M").time())
            if end == "07:30":  # night shift crosses midnight
                end_dt = datetime.combine(punch_dt.date() + timedelta(days=1), datetime.strptime(end, "%H:%M").time())
            else:
                end_dt = datetime.combine(punch_dt.date(), datetime.strptime(end, "%H:%M").time())
            return start_dt, end_dt
    return None, None

df[["shift_start", "shift_end"]] = df.apply(lambda row: pd.Series(get_shift_times(row["last name"], row["datetime"])), axis=1)

# ==== STEP 4: Group and find punches ====
summary_records = []
for (emp_no, date), group in df.groupby(["employee number", df["datetime"].dt.date]):
    emp_type = group["last name"].iloc[0]
    shift_start = group["shift_start"].iloc[0]
    shift_end = group["shift_end"].iloc[0]

    # Find punches
    main_in = group[(group["gate"] == "main") & (group["punch_type"] == "in")]["datetime"].min()
    lcm_in = group[(group["gate"] == "lcm") & (group["punch_type"] == "in")]["datetime"].min()
    main_out = group[(group["gate"] == "main") & (group["punch_type"] == "out")]["datetime"].max()
    lcm_out = group[(group["gate"] == "lcm") & (group["punch_type"] == "out")]["datetime"].max()

    # Mismatches
    in_mismatch = "No"
    out_mismatch = "No"
    if pd.notna(main_in) and pd.isna(lcm_in):
        in_mismatch = "Yes (LCM In missing)"
    elif pd.notna(lcm_in) and pd.isna(main_in):
        in_mismatch = "Yes (Main In missing)"

    if pd.notna(main_out) and pd.isna(lcm_out):
        out_mismatch = "Yes (LCM Out missing)"
    elif pd.notna(lcm_out) and pd.isna(main_out):
        out_mismatch = "Yes (Main Out missing)"

    # Late
    grace_time = shift_start + timedelta(minutes=GRACE_MINUTES)
    late = "No"
    if pd.notna(main_in) and main_in > grace_time:
        late = "Yes"

    summary_records.append({
        "Employee No": emp_no,
        "Date": date,
        "Shift Start": shift_start.time(),
        "Shift End": shift_end.time(),
        "Main In": main_in.time() if pd.notna(main_in) else None,
        "LCM In": lcm_in.time() if pd.notna(lcm_in) else None,
        "Main Out": main_out.time() if pd.notna(main_out) else None,
        "LCM Out": lcm_out.time() if pd.notna(lcm_out) else None,
        "In Mismatch": in_mismatch,
        "Out Mismatch": out_mismatch,
        "Late": late
    })

summary_df = pd.DataFrame(summary_records)

# ==== STEP 5: Export files ====
# File 1 - Punch Mismatch Report
mismatch_df = summary_df[(summary_df["In Mismatch"] != "No") | (summary_df["Out Mismatch"] != "No")]
mismatch_df.to_csv("punch_mismatch_report.csv", index=False)

# File 2 - Late Comers Report
late_df = summary_df[summary_df["Late"] == "Yes"]
late_df.to_csv("late_comers_report.csv", index=False)

# File 3 - Full Summary
summary_df.to_csv("attendance_summary.csv", index=False)

print("✅ Analysis complete. Files generated:")
print("- punch_mismatch_report.csv")
print("- late_comers_report.csv")
print("- attendance_summary.csv")