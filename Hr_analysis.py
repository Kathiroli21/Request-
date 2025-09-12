import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

# -------------------------
# Sample / Test punch data
# -------------------------
data = [
    # Day Shift - Main In/Out
    (1001, "A", "2025-09-10 07:35:00", "MAIN ENTRY FHT 1 Door 1", 1),
    (1001, "A", "2025-09-10 15:36:00", "MAIN ENTRY FHT 1 Door 2", 2),

    # Day Shift - LMC In/Out only
    (1002, "B", "2025-09-10 07:40:00", "LMC-Z3 T1 Door 1 Reader", 1),
    (1002, "B", "2025-09-10 15:45:00", "LMC-Z3 T1 Door 2 Reader", 2),

    # Night Shift - In on 10th, Out on 11th
    (1003, "C", "2025-09-10 23:40:00", "MAIN ENTRY FHT 1 Door 1", 1),
    (1003, "C", "2025-09-11 07:20:00", "MAIN ENTRY FHT 1 Door 2", 2),

    # Missing Out (only In punch)
    (1004, "D", "2025-09-10 07:50:00", "MAIN ENTRY FHT 1 Door 1", 1),

    # Missing In (only Out punch)
    (1005, "E", "2025-09-10 15:25:00", "MAIN ENTRY FHT 1 Door 2", 2),

    # LMC In but no Main In (and Main out later)
    (1007, "F", "2025-09-10 08:05:00", "LMC-Z3 T1 Door 1 Reader", 1),
    (1007, "F", "2025-09-10 16:05:00", "MAIN ENTRY FHT 1 Door 2", 2),

    # Fixed shift employee (08:00–16:00)
    (2001, "G", "2025-09-10 08:00:00", "MAIN ENTRY FHT 1 Door 1", 1),
    (2001, "G", "2025-09-10 16:00:00", "MAIN ENTRY FHT 1 Door 2", 2),
]

df = pd.DataFrame(data, columns=["employee_id","name","datetime","location","door"])
df["datetime"] = pd.to_datetime(df["datetime"])
df["date"] = df["datetime"].dt.date

# -------------------------
# Normalize location & door
# -------------------------
def normalize_location(loc):
    s = str(loc).upper()
    if "MAIN" in s:
        return "Main"
    if "LMC" in s or "BIAS" in s:
        return "LMC"
    return "Other"

df["location_norm"] = df["location"].apply(normalize_location)
df["door_type"] = df["door"].map({1:"Entry",2:"Exit"})

# -------------------------
# Configuration: fixed shift employees
# -------------------------
fixed_shift_employees = {2001}  # add employee IDs who have fixed 08:00-16:00 shift

# -------------------------
# Shift assignment helper
# -------------------------
def shift_label_and_bounds_from_dt(dt, emp_id=None):
    """
    Return (label, shift_start_dt, shift_end_dt)
    If dt is NaT return (None, None, None)
    """
    if pd.isna(dt):
        return (None, None, None)
    # fixed shift override
    if emp_id in fixed_shift_employees:
        start = datetime.combine(dt.date(), time(8,0))
        end   = datetime.combine(dt.date(), time(16,0))
        return ("Fixed 08:00-16:00", start, end)

    t = dt.time()
    if time(5,0) <= t < time(12,0):
        return ("Shift 1 (07:30-15:30)", datetime.combine(dt.date(), time(7,30)), datetime.combine(dt.date(), time(15,30)))
    elif time(12,0) <= t < time(20,0):
        return ("Shift 2 (15:30-23:30)", datetime.combine(dt.date(), time(15,30)), datetime.combine(dt.date(), time(23,30)))
    else:
        # night shift anchored to dt.date()
        return ("Shift 3 (23:30-07:30)", datetime.combine(dt.date(), time(23,30)), datetime.combine(dt.date()+timedelta(days=1), time(7,30)))

# -------------------------
# Build summary anchored to IN punches
# -------------------------
summary_rows = []

# iterate per employee
for emp, g in df.groupby("employee_id"):
    g = g.sort_values("datetime").reset_index(drop=True)
    # all entry punches (for anchor dates)
    entries_all = g[g["door_type"]=="Entry"]
    anchor_dates = sorted(entries_all["date"].unique().tolist())  # days where there's at least one IN

    # 1) For each anchor date (has at least one IN) -> build shift row and attach outs (even if outs are next day)
    for d in anchor_dates:
        # all punches (entries/exits) for this employee (we'll use some relative windows to pick outs)
        punches_emp = g  # already filtered by emp
        # entries on the anchor date
        entries_day = punches_emp[(punches_emp["date"]==d) & (punches_emp["door_type"]=="Entry")]
        main_in = entries_day[entries_day["location_norm"]=="Main"]["datetime"].min() if not entries_day[entries_day["location_norm"]=="Main"].empty else pd.NaT
        lmc_in  = entries_day[entries_day["location_norm"]=="LMC"]["datetime"].min() if not entries_day[entries_day["location_norm"]=="LMC"].empty else pd.NaT
        # earliest IN (Main or LMC) for shift assignment
        earliest_in = min([x for x in [main_in,lmc_in] if not pd.isna(x)], default=pd.NaT)

        # assign shift label + bounds based on earliest_in (and fixed-shift override)
        shift_label, shift_start, shift_end = shift_label_and_bounds_from_dt(earliest_in, emp_id=emp)

        # find candidate exits in a window depending on shift (search across punch dataframe for this emp)
        exits_all = punches_emp[punches_emp["door_type"]=="Exit"]
        main_out = pd.NaT
        lmc_out = pd.NaT
        if shift_label is not None:
            if "Shift 3" in shift_label:
                # night shift -> allow exits up to next day 08:00
                window_start = shift_start - timedelta(hours=2)
                window_end   = datetime.combine(shift_start.date()+timedelta(days=1), time(8,0))
            else:
                window_start = shift_start - timedelta(hours=2)
                window_end   = shift_end + timedelta(hours=1)
            candidate_exits = exits_all[(exits_all["datetime"] >= window_start) & (exits_all["datetime"] <= window_end)]
            if not candidate_exits.empty:
                mo = candidate_exits[candidate_exits["location_norm"]=="Main"]["datetime"]
                lo = candidate_exits[candidate_exits["location_norm"]=="LMC"]["datetime"]
                if not mo.empty: main_out = mo.min()
                if not lo.empty: lmc_out = lo.min()

        # compute work start/end based on preference Main -> LMC
        work_start = main_in if not pd.isna(main_in) else lmc_in
        work_end   = main_out if not pd.isna(main_out) else lmc_out
        if pd.notna(work_start) and pd.notna(work_end):
            work_hours = round((work_end - work_start).total_seconds()/3600.0, 2)
            if work_hours < 0:
                work_hours = 0.0
        else:
            work_hours = 0.0

        summary_rows.append({
            "Employee Number": emp,
            "Name": g["name"].iloc[0],
            "Date": d,
            "Shift": shift_label,
            "Shift Start": shift_start,
            "Shift End": shift_end,
            "Main In": main_in,
            "LMC In": lmc_in,
            "Main Out": main_out,
            "LMC Out": lmc_out,
            "Work Hours": work_hours
        })

    # 2) Handle exit-only dates (dates where employee has Exit(s) but no Entry)
    exits_only_dates = sorted(g[g["door_type"]=="Exit"]["date"].unique().tolist())
    # exit-only dates that are not already covered by anchor_dates
    extra_exit_dates = [dt for dt in exits_only_dates if dt not in anchor_dates]
    for d in extra_exit_dates:
        exits_day = g[(g["date"]==d) & (g["door_type"]=="Exit")]
        main_out = exits_day[exits_day["location_norm"]=="Main"]["datetime"].min() if not exits_day[exits_day["location_norm"]=="Main"].empty else pd.NaT
        lmc_out  = exits_day[exits_day["location_norm"]=="LMC"]["datetime"].min() if not exits_day[exits_day["location_norm"]=="LMC"].empty else pd.NaT
        # no shift (assign only if you want heuristic from out - but per instruction shift should be based on IN)
        summary_rows.append({
            "Employee Number": emp,
            "Name": g["name"].iloc[0],
            "Date": d,
            "Shift": None,
            "Shift Start": None,
            "Shift End": None,
            "Main In": pd.NaT,
            "LMC In": pd.NaT,
            "Main Out": main_out,
            "LMC Out": lmc_out,
            "Work Hours": 0.0
        })

# Build DataFrame
summary_df = pd.DataFrame(summary_rows)

# Remove rows where absolutely nothing exists (defensive) - e.g., shouldn't happen but safe
summary_df = summary_df[~(summary_df[["Main In","LMC In","Main Out","LMC Out"]].isna().all(axis=1))]

# Sort and display
summary_df = summary_df.sort_values(["Employee Number","Date"]).reset_index(drop=True)

# Print
pd.set_option("display.max_columns", None)
print(summary_df)
