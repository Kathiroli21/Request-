import pandas as pd
from datetime import datetime, timedelta

# ---- USER INPUT ----
# Replace with your real data file path and list:
# df = pd.read_csv("your_file.csv")
fixed_shift_staff = ['123456', '234567']  # example; use actual employee numbers as string or int

# ---- UTILITY FUNCTIONS ----
STAFF_SHIFTS = [("07:30", "15:30"), ("08:00", "16:00"), ("23:30", "07:30")]
WORKMEN_SHIFTS = [("07:30", "15:30"), ("15:30", "23:30"), ("23:30", "07:30")]

def normalize_location(loc):
    if isinstance(loc, str) and ("LMC" in loc or "BIAS" in loc):
        return "LMC"
    elif isinstance(loc, str) and "MAIN" in loc:
        return "MAIN"
    return "OTHER"

def get_door(loc):
    if "Door 1" in loc:
        return "IN"
    elif "Door 2" in loc:
        return "OUT"
    return "UNKNOWN"

def get_role(last_name):
    lname = str(last_name).upper()
    if "STAFF" in lname:
        return "STAFF"
    elif "WORKMEN" in lname or "WORKMAN" in lname:
        return "WORKMEN"
    return "OTHER"

def parse_time(date_str, time_str):
    return datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M:%S")

def assign_shift(first_punch, emp_no, role):
    punch_time = first_punch.time()
    shifts = STAFF_SHIFTS if role == "STAFF" else WORKMEN_SHIFTS
    if role == "STAFF" and str(emp_no) in fixed_shift_staff:
        shifts = [("08:00", "16:00")]
    for start_str, end_str in shifts:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        if end_time < start_time:  # Night shift
            if punch_time >= start_time or punch_time < end_time:
                return start_str, end_str
        else:
            if start_time <= punch_time < end_time:
                return start_str, end_str
    return None, None

# ---- READ DATA ----
# Replace with your filename; use read_excel if Excel file
# df = pd.read_csv("your_file.csv", dtype=str)
# For interactive test, insert a small DataFrame manually if no file access
# Ensure all columns (including 'Employee Number') are proper dtype (string recommended for grouping)

# ---- PREPROCESS ----
df['Role'] = df['Last Name'].apply(get_role)
df = df[df['Role'].isin(['STAFF', 'WORKMEN'])]
df['Location Type'] = df['Location'].apply(normalize_location)
df['Door'] = df['Location'].apply(get_door)
df['Punch Datetime'] = df.apply(lambda r: parse_time(r['Date Occurred'], r['Time Occurred']), axis=1)

# ---- SHIFT and IN/OUT LOGIC ----
output_rows = []

# Group by Employee and Date for initial shift assignment
grouped = df.groupby(['Employee Number', 'Date Occurred'])

for (emp_no, date), group in grouped:
    group_sorted = group.sort_values('Punch Datetime')
    last_name = group_sorted.iloc['Last Name']
    role = group_sorted.iloc['Role']
    first_punch = group_sorted.iloc['Punch Datetime']
    shift_start, shift_end = assign_shift(first_punch, emp_no, role)

    # --- Extended grouping for night shift OUTs ---
    if shift_start == "23:30" and shift_end == "07:30":
        date_dt = pd.to_datetime(date, dayfirst=True)
        next_date = (date_dt + timedelta(days=1)).strftime("%d-%m-%Y")
        # Combine today and next day
        next_day_punches = df[(df['Employee Number'] == emp_no) & (df['Date Occurred'] == next_date)]
        combined = pd.concat([group_sorted, next_day_punches])
        # Considering punches from today 23:30 until next day 07:30
        shift_start_dt = date_dt.replace(hour=23, minute=30, second=0)
        shift_end_dt = (date_dt + timedelta(days=1)).replace(hour=7, minute=30, second=0)
        punches = combined[(combined['Punch Datetime'] >= shift_start_dt) & (combined['Punch Datetime'] <= shift_end_dt)]
    else:
        punches = group_sorted

    # Get first IN/OUT for Main/LMC for this shift's punches
    main_in = punches[(punches['Location Type'] == 'MAIN') & (punches['Door'] == 'IN')]
    lmc_in = punches[(punches['Location Type'] == 'LMC') & (punches['Door'] == 'IN')]
    lmc_out = punches[(punches['Location Type'] == 'LMC') & (punches['Door'] == 'OUT')]
    main_out = punches[(punches['Location Type'] == 'MAIN') & (punches['Door'] == 'OUT')]

    row = {
        'Employee Number': emp_no,
        'Last Name': last_name,
        'Shift Start': shift_start if shift_start else "",
        'Shift End': shift_end if shift_end else "",
        'Main In': main_in.iloc['Time Occurred'] if not main_in.empty else "",
        'LMC In': lmc_in.iloc['Time Occurred'] if not lmc_in.empty else "",
        'LMC Out': lmc_out.iloc['Time Occurred'] if not lmc_out.empty else "",
        'Main Out': main_out.iloc['Time Occurred'] if not main_out.empty else "",
    }
    output_rows.append(row)

summary_df = pd.DataFrame(output_rows)

# ---- OUTPUT ----
print(summary_df.head())
# summary_df.to_csv("punch_summary.csv", index=False)  # Save as CSV if needed
