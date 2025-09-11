import pandas as pd
from datetime import datetime, timedelta

# Sample data setup (replace with your own CSV or DataFrame input)
data = {
    'Employee Number': ['618163']*10,
    'First Name': ['Voggu Van']*10,
    'Last Name': ['STAFF']*10,
    'Date Occurred': [
        '05-03-2025', '06-03-2025', '07-03-2025', '07-03-2025', '08-03-2025', '08-03-2025',
        '08-03-2025', '08-03-2025', '09-03-2025', '09-03-2025'
    ],
    'Time Occurred': [
        '23:29:31', '07:36:45', '07:38:14', '23:29:47', '07:47:25', '23:40:09',
        '07:38:50', '23:31:38', '07:38:47', '07:46:58'
    ],
    'Location': [
        'LMC-Z3-T1 Door 1 Reader', 'LMC-Z3-T2 Door 2 Reader',
        'LMC-Z3-T1 Door 1 Reader', 'MAIN_ENTRY_FHT_3 Door 1 Reader',
        'MAIN_ENTRY_FHT_5 Door 2 Reader', 'LMC-Z3-T2 Door 1 Reader',
        'LMC-Z3-T1 Door 2 Reader', 'MAIN_ENTRY_FHT_3 Door 1 Reader',
        'LMC-Z3-T2 Door 2 Reader', 'MAIN_ENTRY_FHT_5 Door 2 Reader'
    ]
}
df = pd.DataFrame(data)

# Shift definitions
STAFF_SHIFTS = [("07:30", "15:30"), ("08:00", "16:00"), ("23:30", "07:30")]
fixed_shift_staff = ['999']  # leave empty or fill as required

def normalize_location(loc):
    if 'LMC' in loc or 'BIAS' in loc:
        return 'LMC'
    elif 'MAIN' in loc:
        return 'MAIN'
    return 'OTHER'

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
    return pd.to_datetime(f"{date_str} {time_str}", format="%d-%m-%Y %H:%M:%S")

def get_shift_windows_for_period(start_date, end_date, shifts):
    date_range = pd.date_range(start=start_date, end=end_date)
    windows = []
    for date_dt in date_range:
        for start_str, end_str in shifts:
            start_t = datetime.strptime(start_str, "%H:%M").time()
            end_t = datetime.strptime(end_str, "%H:%M").time()
            if end_t < start_t:
                shift_start_dt = date_dt.replace(hour=start_t.hour, minute=start_t.minute, second=0)
                shift_end_dt = (date_dt + timedelta(days=1)).replace(hour=end_t.hour, minute=end_t.minute, second=0)
            else:
                shift_start_dt = date_dt.replace(hour=start_t.hour, minute=start_t.minute, second=0)
                shift_end_dt = date_dt.replace(hour=end_t.hour, minute=end_t.minute, second=0)
            windows.append((shift_start_dt, shift_end_dt, start_str, end_str, date_dt.strftime('%d-%m-%Y')))
    return windows

def first(series):
    return series.iloc[0] if len(series) else ''

def last(series):
    return series.iloc[-1] if len(series) > 1 else ''

# Enrich the data frame with useful columns
df['Role'] = df['Last Name'].apply(get_role)
df['Location Type'] = df['Location'].apply(normalize_location)
df['Door'] = df['Location'].apply(get_door)
df['Punch Datetime'] = df.apply(lambda r: to_datetime(r['Date Occurred'], r['Time Occurred']), axis=1)

summary_rows = []
for emp_no in df['Employee Number'].unique():
    emp_df = df[df['Employee Number'] == emp_no]
    role = emp_df.iloc[0]['Role']
    shifts = STAFF_SHIFTS if role == "STAFF" else []  # Extend for workmen if needed
    min_date = pd.to_datetime(emp_df['Date Occurred'], dayfirst=True).min()
    max_date = pd.to_datetime(emp_df['Date Occurred'], dayfirst=True).max()
    windows = get_shift_windows_for_period(min_date, max_date, shifts)
    for shift_start_dt, shift_end_dt, shift_start_label, shift_end_label, window_start_date in windows:
        punches = emp_df[(emp_df['Punch Datetime'] >= shift_start_dt) & (emp_df['Punch Datetime'] <= shift_end_dt)].sort_values('Punch Datetime')
        if punches.empty:
            continue
        main_in = punches[(punches['Location Type'] == 'MAIN') & (punches['Door'] == 'IN')]['Time Occurred']
        main_out = punches[(punches['Location Type'] == 'MAIN') & (punches['Door'] == 'OUT')]['Time Occurred']
        lmc_in = punches[(punches['Location Type'] == 'LMC') & (punches['Door'] == 'IN')]['Time Occurred']
        lmc_out = punches[(punches['Location Type'] == 'LMC') & (punches['Door'] == 'OUT')]['Time Occurred']

        summary_rows.append({
            'Employee Number': emp_no,
            'Last Name': role,
            'Shift Date': window_start_date,
            'Shift Start': shift_start_label,
            'Shift End': shift_end_label,
            'Main In': first(main_in),
            'Main In (Last)': last(main_in),
            'LMC In': first(lmc_in),
            'LMC In (Last)': last(lmc_in),
            'LMC Out': first(lmc_out),
            'LMC Out (Last)': last(lmc_out),
            'Main Out': first(main_out),
            'Main Out (Last)': last(main_out)
        })

summary_df = pd.DataFrame(summary_rows)

print(summary_df)
