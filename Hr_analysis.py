import pandas as pd
from datetime import datetime, timedelta

# --- Step 1: Load Data ---
# df = pd.read_csv("your_file.csv")  # Use your actual file path
# Column names: ['Employee Number', 'First Name', 'Last Name', 'Date Occurred', 'Time Occurred', 'Time Recorded', 'Location', ...]

# --- Step 2: Utility Functions ---
STAFF_SHIFTS = [
    ("07:30", "15:30"),
    ("08:00", "16:00"),
    ("23:30", "07:30")
]
WORKMEN_SHIFTS = [
    ("07:30", "15:30"),
    ("15:30", "23:30"),
    ("23:30", "07:30")
]
fixed_shift_staff = ['123456', '234567']  # Replace with your own fixed shift employee numbers

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
    # Check fixed shift for staff
    if role == "STAFF" and str(emp_no) in fixed_shift_staff:
        shifts = [("08:00", "16:00")]
    for start_str, end_str in shifts:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        # Handle night shift (end before start)
        if end_time < start_time:
            if punch_time >= start_time or punch_time < end_time:
                return start_str, end_str
        else:
            if start_time <= punch_time < end_time:
                return start_str, end_str
    return None, None

# --- Step 3: Processing ---
df['Role'] = df['Last Name'].apply(get_role)
df = df[df['Role'].isin(['STAFF', 'WORKMEN'])]
df['Location Type'] = df['Location'].apply(normalize_location)
df['Door'] = df['Location'].apply(get_door)
df['Punch Datetime'] = df.apply(lambda r: parse_time(r['Date Occurred'], r['Time Occurred']), axis=1)

grouped = df.groupby(['Employee Number', 'Date Occurred'])

output_rows = []
for (emp_no, date), group in grouped:
    group_sorted = group.sort_values('Punch Datetime')
    last_name = group_sorted.iloc['Last Name']
    role = group_sorted.iloc['Role']
    first_punch = group_sorted.iloc['Punch Datetime']
    shift_start, shift_end = assign_shift(first_punch, emp_no, role)
    # Find each punch type
    main_in = group_sorted[(group_sorted['Location Type'] == 'MAIN') & (group_sorted['Door'] == 'IN')]
    lmc_in = group_sorted[(group_sorted['Location Type'] == 'LMC') & (group_sorted['Door'] == 'IN')]
    lmc_out = group_sorted[(group_sorted['Location Type'] == 'LMC') & (group_sorted['Door'] == 'OUT')]
    main_out = group_sorted[(group_sorted['Location Type'] == 'MAIN') & (group_sorted['Door'] == 'OUT')]
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
print(summary_df.head())

# Optional: Save to CSV
# summary_df.to_csv("punch_summary.csv", index=False)
