import pandas as pd
from datetime import datetime, timedelta

# Load the data - update file paths as needed
punch_in_df = pd.read_excel('punch_in_data.xlsx')
punch_out_df = pd.read_excel('punch_out_data.xlsx')

# Ensure column names match exactly what you have in your files
# Punch In columns: Persno, in_date, punchinsec, tm_ev_type, punchin_time, emp_date_key
# Punch Out columns: emp_date_key, punch_out_sec, persno, tm_ev_type, Date, punch_out_time

# Convert to consistent naming (if needed)
punch_in_df.columns = ['Persno', 'in_date', 'punchinsec', 'tm_ev_type_in', 'punchin_time', 'emp_date_key_in']
punch_out_df.columns = ['emp_date_key_out', 'punch_out_sec', 'Persno', 'tm_ev_type_out', 'Date', 'punch_out_time']

# Convert date and time columns to datetime objects
# Punch In datetime
punch_in_df['in_datetime'] = pd.to_datetime(
    punch_in_df['in_date'].astype(str) + ' ' + punch_in_df['punchin_time'].astype(str),
    format='%d%m%Y %H:%M:%S',
    errors='coerce'
)

# Punch Out datetime
punch_out_df['out_datetime'] = pd.to_datetime(
    punch_out_df['Date'].astype(str) + ' ' + punch_out_df['punch_out_time'].astype(str),
    format='%d%m%Y %H:%M:%S',
    errors='coerce'
)

# Handle overnight shifts (punch out next day before 10am)
def adjust_for_overnight_shifts(df):
    # Create columns to help with matching overnight shifts
    df['date_only'] = df['in_datetime'].dt.date
    df['next_day_10am'] = df['in_datetime'] + timedelta(days=1)
    df['next_day_10am'] = df['next_day_10am'].dt.normalize() + timedelta(hours=10)
    return df

punch_in_df = adjust_for_overnight_shifts(punch_in_df)

# Create matching keys
punch_in_df['match_key'] = punch_in_df['Persno'].astype(str) + '_' + punch_in_df['in_date'].astype(str)
punch_out_df['match_key'] = punch_out_df['Persno'].astype(str) + '_' + punch_out_df['Date'].astype(str)

# Merge the data
merged_df = pd.merge(
    punch_in_df,
    punch_out_df,
    how='outer',
    on='match_key',
    suffixes=('_in', '_out')
)

# Analysis 1: Punch ins without punch outs
punch_in_no_out = merged_df[merged_df['punch_out_time'].isna() & merged_df['punchin_time'].notna()]
punch_in_no_out = punch_in_no_out[[
    'Persno_in', 'in_date', 'punchinsec', 'tm_ev_type_in', 
    'punchin_time', 'emp_date_key_in', 'in_datetime'
]].rename(columns={'Persno_in': 'Persno'})

# Analysis 2: Punch outs without punch ins
punch_out_no_in = merged_df[merged_df['punchin_time'].isna() & merged_df['punch_out_time'].notna()]
punch_out_no_in = punch_out_no_in[[
    'Persno_out', 'emp_date_key_out', 'punch_out_sec', 'tm_ev_type_out',
    'Date', 'punch_out_time', 'out_datetime'
]].rename(columns={'Persno_out': 'Persno'})

# Analysis 3: Both punch in and punch out exist
complete_punches = merged_df[merged_df['punchin_time'].notna() & merged_df['punch_out_time'].notna()]

# Handle overnight shifts in complete punches
complete_punches['duration'] = complete_punches['out_datetime'] - complete_punches['in_datetime']
complete_punches['is_overnight'] = complete_punches['duration'] > timedelta(hours=12)

# Prepare final complete punches output
complete_punches = complete_punches[[
    'Persno_in', 'in_date', 'punchin_time', 'punch_out_time',
    'in_datetime', 'out_datetime', 'duration', 'is_overnight',
    'tm_ev_type_in', 'tm_ev_type_out', 'emp_date_key_in', 'emp_date_key_out'
]].rename(columns={'Persno_in': 'Persno'})

# Export results to Excel
with pd.ExcelWriter('punch_analysis_results.xlsx') as writer:
    punch_in_no_out.to_excel(writer, sheet_name='PunchIn_NoOut', index=False)
    punch_out_no_in.to_excel(writer, sheet_name='PunchOut_NoIn', index=False)
    complete_punches.to_excel(writer, sheet_name='Complete_Punches', index=False)

print("Analysis complete. Results saved to 'punch_analysis_results.xlsx'")