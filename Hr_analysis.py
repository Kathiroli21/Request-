import pandas as pd
from datetime import datetime, timedelta

# -------------------
# Example Inputs
# -------------------
# Punch data
punch_df = pd.DataFrame({
    "employee": [101,101,101,101,102,102,103,103],
    "date": ["2025-09-20","2025-09-20","2025-09-21","2025-09-21",
             "2025-09-21","2025-09-21","2025-09-20","2025-09-21"],
    "type": ["P10","P20","P10","P20","P10","P20","P10","P20"],
    "time": ["23:40","23:59","07:55","16:30","06:00","18:30","23:40","07:50"]
})

# Shifts per employee
shift_df = pd.DataFrame({
    "employee": [101,102,103],
    "date": ["2025-09-21","2025-09-21","2025-09-21"],
    "shifts": ["3","1","3"]
})

# -------------------
# Define Shift Timings
# -------------------
shift_times = {
    "1": ("08:05","16:05"),
    "2": ("16:05","00:05"),
    "3": ("00:05","08:05"),
}

# -------------------
# Convert punch datetime
# -------------------
punch_df["datetime"] = pd.to_datetime(punch_df["date"] + " " + punch_df["time"])
punch_df = punch_df.sort_values(["employee","datetime"])

# -------------------
# Function: Get shift window
# -------------------
def get_shift_window(base_date, shift_id):
    start_str, end_str = shift_times[shift_id]
    start_dt = datetime.strptime(base_date+" "+start_str,"%Y-%m-%d %H:%M")
    end_dt   = datetime.strptime(base_date+" "+end_str,"%Y-%m-%d %H:%M")
    
    # overnight shift (end <= start)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return start_dt, end_dt

# -------------------
# Process Shifts
# -------------------
results = []

for _, row in shift_df.iterrows():
    emp, date, shifts = row["employee"], row["date"], row["shifts"].split(",")
    
    # if multiple shifts (e.g. "1,2") → merge
    start_dt,end_dt = None,None
    for sh in shifts:
        s_dt,e_dt = get_shift_window(date,sh)
        if start_dt is None:
            start_dt,end_dt = s_dt,e_dt
        else:
            end_dt = max(end_dt,e_dt)
    
    # For overnight Shift 3 → allow punches from previous day late night
    day_start = pd.to_datetime(date)
    search_start = day_start - timedelta(days=1)  # include yesterday’s late punches
    search_end = day_start + timedelta(days=1)    # include next day morning
    
    punches = punch_df[(punch_df["employee"]==emp) &
                       (punch_df["datetime"]>=search_start) &
                       (punch_df["datetime"]<=search_end)]
    
    # Pick earliest IN and latest OUT among available punches in that range
    first_in = punches[punches["type"]=="P10"]["datetime"].min()
    last_out = punches[punches["type"]=="P20"]["datetime"].max()
    
    # If employee had no punch, leave NaT
    results.append({
        "employee": emp,
        "date": date,
        "shifts": ",".join(shifts),
        "shift_start": start_dt,
        "shift_end": end_dt,
        "first_in": first_in,
        "last_out": last_out
    })

final_df = pd.DataFrame(results)

print(final_df)