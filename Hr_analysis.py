import pandas as pd
from datetime import datetime, timedelta

# --- Sample Data (replace with your file load for real data) ---
sample_data = {
    'Employee Number': ['101', '101', '101', '101', '101', '101',
                        '102', '102', '102', '102',
                        '103', '103', '103', '103'],
    'First Name': ['Alice']*6 + ['Bob']*4 + ['Carol']*4,
    'Last Name': ['STAFF']*6 + ['WORKMAN']*4 + ['STAFF']*4,
    'Date Occurred': [
        '10-09-2025', '10-09-2025', '11-09-2025', '11-09-2025',
        '11-09-2025', '11-09-2025',
        '10-09-2025', '10-09-2025', '11-09-2025', '11-09-2025',
        '10-09-2025', '10-09-2025', '10-09-2025', '11-09-2025'
    ],
    'Time Occurred': [
        '23:30:00', '23:55:00', '01:10:00', '07:25:00', '07:45:00', '15:15:00',
        '07:35:00', '15:25:00', '23:45:00', '07:20:00',
        '07:47:00', '12:03:00', '12:15:00', '17:30:00'
    ],
    'Location': [
        'MAIN_ENTRY Door 1 Reader', 'LMC-Z3-T1 Door 2 Reader',
        'MAIN_ENTRY Door 2 Reader', 'LMC-Z3-T1 Door 1 Reader',
        'MAIN_ENTRY Door 1 Reader', 'MAIN_ENTRY Door 2 Reader',
        'LMC-Z3-T1 Door 1 Reader', 'MAIN_ENTRY Door 2 Reader',
        'BIAS-Z3-T1 Door 1 Reader', 'MAIN_ENTRY Door 2 Reader',
        'MAIN_ENTRY Door 1 Reader', 'LMC-Z3-T1 Door 1 Reader',
        'LMC-Z3-T1 Door 2 Reader', 'MAIN_ENTRY Door 2 Reader'
    ]
}
df = pd.DataFrame(sample_data)

# ---- Shift rules ----
STAFF_SHIFTS = [("07:30", "15:30"), ("08:00", "16:00"), ("23:30", "07:30")]
WORKMEN_SHIFTS = [("07:30", "15:30"), ("15:30", "23:30"), ("23:30", "07:30")]
fixed_shift_staff = ['999']

def normalize_location(loc):
    if "LMC" in loc or "BIAS" in loc:
        return "LMC"
    elif "MAIN" in loc:
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

def to_datetime(date_str, time_str):
    return pd.to_datetime(date_str + " " + time_str, format="%d-%m-%Y %H:%M:%S")

def get_shift_windows(date, shifts):
    date_dt = pd.to_datetime(date, dayfirst=True)
    windows = []
    for start_str, end_str in shifts:
        start_t = datetime.strptime(start_str, "%H:%M").time()
        end_t = datetime.strptime(end_str, "%H:%M").time()
        if end_t < start_t:
            shift_start_dt = date_dt.replace(hour=start_t.hour, minute=start_t.minute, second=0)
            shift_end_dt = (date_dt + timedelta(days=1)).replace(hour=end_t.hour, minute=end_t.minute, second=0)
        else:
            shift_start_dt = date_dt.replace(hour=start_t.hour, minute=start_t.minute, second=0)
            shift_end_dt = date_dt.replace(hour=end_t.hour, minute=end_t.minute, second=0)
        windows.append((shift_start_dt, shift_end_dt, start_str, end_str))
    return windows

# --- Enrich data ---
df['Role'] = df['Last Name'].apply(get_role)
df = df[df['Role'].isin(['STAFF', 'WORKMEN'])]
df['Location Type'] = df['Location'].apply(normalize_location)
df['Door'] = df['Location'].apply(get_door)
df['Punch Datetime'] = df.apply(lambda r: to_datetime(r['Date Occurred'], r['Time Occurred']), axis=1)

summary_rows = []

for emp_no in df['Employee Number'].unique():
    emp_df = df[df['Employee Number'] == emp_no]
    role = emp_df.iloc[0]['Role']
    shifts = STAFF_SHIFTS if role == "STAFF" else WORKMEN_SHIFTS
    dates = sorted(emp_df['Date Occurred'].unique(), key=lambda d: pd.to_datetime(d, dayfirst=True))
    for date in dates:
        windows = get_shift_windows(date, shifts)
        punches = emp_df[((emp_df['Date Occurred'] == date) | (emp_df['Date Occurred'] == (pd.to_datetime(date, dayfirst=True)+timedelta(days=1)).strftime("%d-%m-%Y")))]
        for shift_start_dt, shift_end_dt, shift_start_label, shift_end_label in windows:
            mask = (punches['Punch Datetime'] >= shift_start_dt) & (punches['Punch Datetime'] <= shift_end_dt)
            shift_punches = punches[mask].sort_values('Punch Datetime')
            if not shift_punches.empty:
                main_in = shift_punches[(shift_punches['Location Type'] == 'MAIN') & (shift_punches['Door'] == 'IN')]
                lmc_in = shift_punches[(shift_punches['Location Type'] == 'LMC') & (shift_punches['Door'] == 'IN')]
                lmc_out = shift_punches[(shift_punches['Location Type'] == 'LMC') & (shift_punches['Door'] == 'OUT')]
                main_out = shift_punches[(shift_punches['Location Type'] == 'MAIN') & (shift_punches['Door'] == 'OUT')]
                summary_rows.append({
                    'Employee Number': emp_no,
                    'Last Name': role,
                    'Date': date,
                    'Shift Start': shift_start_label,
                    'Shift End': shift_end_label,
                    'Main In': main_in['Time Occurred'].iloc[0] if not main_in.empty else '',
                    'LMC In': lmc_in['Time Occurred'].iloc[0] if not lmc_in.empty else '',
                    'LMC Out': lmc_out['Time Occurred'].iloc[0] if not lmc_out.empty else '',
                    'Main Out': main_out['Time Occurred'].iloc[0] if not main_out.empty else '',
                })

summary_df = pd.DataFrame(summary_rows)
print(summary_df)

# To save to CSV:
# summary_df.to_csv("output_punch_summary.csv", index=False)
