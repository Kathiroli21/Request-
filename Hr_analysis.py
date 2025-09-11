import pandas as pd
from datetime import datetime, timedelta

# --- INPUT DATA (replace with your own DataFrame load if needed) ---
data = [
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '05-03-2025', 'Time Occurred': '23:29:31', 'Location': 'LMC-Z3-T1 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '06-03-2025', 'Time Occurred': '07:36:45', 'Location': 'LMC-Z3-T2 Door 2 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '07-03-2025', 'Time Occurred': '23:29:46', 'Location': 'MAIN_ENTRY_FHT_3 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '07-03-2025', 'Time Occurred': '23:38:14', 'Location': 'LMC-Z3-T1 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '08-03-2025', 'Time Occurred': '07:47:26', 'Location': 'MAIN_ENTRY_FHT_5 Door 2 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '08-03-2025', 'Time Occurred': '23:31:38', 'Location': 'MAIN_ENTRY_FHT_3 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '08-03-2025', 'Time Occurred': '23:40:09', 'Location': 'LMC-Z3-T2 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '09-03-2025', 'Time Occurred': '07:38:50', 'Location': 'LMC-Z3-T2 Door 2 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '09-03-2025', 'Time Occurred': '07:46:58', 'Location': 'MAIN_ENTRY_FHT_5 Door 2 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '09-03-2025', 'Time Occurred': '08:46:58', 'Location': 'MAIN_ENTRY_FHT_5 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '09-03-2025', 'Time Occurred': '03:46:58', 'Location': 'MAIN_ENTRY_FHT_5 Door 2 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '10-03-2025', 'Time Occurred': '07:46:58', 'Location': 'MAIN_ENTRY_FHT_5 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '10-03-2025', 'Time Occurred': '15:46:58', 'Location': 'MAIN_ENTRY_FHT_5 Door 2 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '11-03-2025', 'Time Occurred': '15:46:58', 'Location': 'MAIN_ENTRY_FHT_5 Door 1 Reader'},
    {'Employee Number': 618163, 'Last Name': 'STAFF', 'Date Occurred': '11-03-2025', 'Time Occurred': '23:25:10', 'Location': 'MAIN_ENTRY_FHT_5 Door 2 Reader'}
]
df = pd.DataFrame(data)

# --- SHIFT DEFINITIONS ---
shift_windows = [
    ('23:30', '07:30'),    # Night shift
    ('07:30', '15:30'),    # Day shift
    ('15:30', '23:30')     # Evening shift
]

# --- DATA ENRICHMENT ---
def normalize_location(loc):
    if 'LMC' in loc or 'BIAS' in loc:
        return 'LMC'
    elif 'MAIN' in loc:
        return 'MAIN'
    return 'OTHER'

def get_door(loc):
    if 'Door 1' in loc:
        return 'IN'
    elif 'Door 2' in loc:
        return 'OUT'
    return 'UNKNOWN'

def to_datetime(date, time):
    return pd.to_datetime(f"{date} {time}", format="%d-%m-%Y %H:%M:%S")

df['Location Type'] = df['Location'].apply(normalize_location)
df['Door'] = df['Location'].apply(get_door)
df['Punch Datetime'] = df.apply(lambda r: to_datetime(r['Date Occurred'], r['Time Occurred']), axis=1)
# Add a 'used' column to track which punches have been assigned to a shift
df['used'] = False
df = df.sort_values('Punch Datetime').reset_index(drop=True)

all_dates = pd.to_datetime(df['Date Occurred'], dayfirst=True).sort_values().unique()

# Define a grace period to catch punches slightly outside the shift window
grace_period = timedelta(hours=2)

records = []
# Iterate through each day that has a punch
for shift_date in all_dates:
    # Check each type of shift for that day
    for start_str, end_str in shift_windows:
        shift_start_t = datetime.strptime(start_str, "%H:%M").time()
        shift_end_t = datetime.strptime(end_str, "%H:%M").time()
        
        # Define the core shift start and end datetimes
        shift_start_dt = pd.Timestamp(shift_date).replace(hour=shift_start_t.hour, minute=shift_start_t.minute, second=0)
        
        # Handle night shift crossing over midnight
        if shift_end_t < shift_start_t:
            shift_end_dt = (pd.Timestamp(shift_date) + timedelta(days=1)).replace(hour=shift_end_t.hour, minute=shift_end_t.minute, second=0)
        else:
            shift_end_dt = pd.Timestamp(shift_date).replace(hour=shift_end_t.hour, minute=shift_end_t.minute, second=0)

        # Define a wider search window using the grace period to find all related punches
        search_start_dt = shift_start_dt - grace_period
        search_end_dt = shift_end_dt + grace_period

        # Filter for punches within the search window that haven't been used yet
        window = df[(df['Punch Datetime'] >= search_start_dt) & (df['Punch Datetime'] < search_end_dt) & (~df['used'])]
        
        if window.empty:
            continue
        
        # --- LOGIC CORRECTION ---
        # Find all IN and OUT punches within the entire shift window
        in_punches = window[window['Door'] == 'IN']
        out_punches = window[window['Door'] == 'OUT']

        # A valid shift must have at least one IN and one OUT punch
        if in_punches.empty or out_punches.empty:
            continue
            
        main_in = in_punches[in_punches['Location Type'] == 'MAIN']['Time Occurred']
        lmc_in  = in_punches[in_punches['Location Type'] == 'LMC']['Time Occurred']
        main_out= out_punches[out_punches['Location Type'] == 'MAIN']['Time Occurred']
        lmc_out = out_punches[out_punches['Location Type'] == 'LMC']['Time Occurred']

        # Mark the punches in this valid shift as 'used' to prevent them from being double-counted
        df.loc[in_punches.index, 'used'] = True
        df.loc[out_punches.index, 'used'] = True
        
        records.append({
            'Employee Number': window.iloc[0]['Employee Number'],
            'Last Name': window.iloc[0]['Last Name'],
            'DATE': shift_date.strftime('%d-%m-%Y'),
            'SHIFT START': start_str,
            'SHIFT END': end_str,
            # Use min() for the first IN punch
            'MAIN IN': main_in.min() if not main_in.empty else '',
            'LMC IN': lmc_in.min() if not lmc_in.empty else '',
            # Use max() for the last OUT punch
            'MAIN OUT': main_out.max() if not main_out.empty else '',
            'LMC OUT': lmc_out.max() if not lmc_out.empty else ''
        })

output_df = pd.DataFrame(records)
print(output_df)

