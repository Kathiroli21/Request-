import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

# =========================
# 1. Extended Sample Punch Data
# =========================
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

    # LMC In but no Main In
    (1007, "F", "2025-09-10 08:05:00", "LMC-Z3 T1 Door 1 Reader", 1),
    (1007, "F", "2025-09-10 16:05:00", "MAIN ENTRY FHT 1 Door 2", 2),

    # Fixed shift employee (08:00–16:00)
    (2001, "G", "2025-09-10 08:00:00", "MAIN ENTRY FHT 1 Door 1", 1),
    (2001, "G", "2025-09-10 16:00:00", "MAIN ENTRY FHT 1 Door 2", 2),
]

df = pd.DataFrame(data, columns=["employee_id","name","datetime","location","door"])
df["datetime"] = pd.to_datetime(df["datetime"])
df["date"] = df["datetime"].dt.date

# =========================
# 2. Normalize location/door
# =========================
def normalize_location(loc):
    s = str(loc).upper()
    if "MAIN" in s:
        return "Main"
    if "LMC" in s:
        return "LMC"
    return "Other"

df["location_norm"] = df["location"].apply(normalize_location)
df["door_type"] = df["door"].map({1:"Entry",2:"Exit"})

# =========================
# 3. Shift assignment
# =========================
def assign_shift_by_time(dt, emp_id=None):
    if pd.isna(dt): 
        return (None, None)
    # fixed shift for employee 2001
    if emp_id == 2001:
        start = datetime.combine(dt.date(), time(8,0))
        end   = datetime.combine(dt.date(), time(16,0))
        return (start, end)

    t = dt.time()
    if time(5,0) <= t < time(12,0):  # shift 1
        return (datetime.combine(dt.date(), time(7,30)), datetime.combine(dt.date(), time(15,30)))
    elif time(12,0) <= t < time(20,0):  # shift 2
        return (datetime.combine(dt.date(), time(15,30)), datetime.combine(dt.date(), time(23,30)))
    else:  # shift 3 (night)
        return (datetime.combine(dt.date(), time(23,30)), datetime.combine(dt.date()+timedelta(days=1), time(7,30)))

# =========================
# 4. Build summary
# =========================
summary_rows = []
for emp, g in df.groupby("employee_id"):
    g = g.sort_values("datetime")
    for d in g["date"].unique():
        punches_day = g[g["date"] == d]

        # ins
        entries = punches_day[punches_day["door_type"]=="Entry"]
        main_in = entries[entries["location_norm"]=="Main"]["datetime"].min()
        lmc_in  = entries[entries["location_norm"]=="LMC"]["datetime"].min()
        earliest_in = min([x for x in [main_in,lmc_in] if not pd.isna(x)], default=pd.NaT)

        # shift assignment
        shift_start, shift_end = assign_shift_by_time(earliest_in, emp)

        # outs
        exits = g[g["door_type"]=="Exit"]
        main_out, lmc_out = pd.NaT, pd.NaT
        if shift_start and shift_end:
            if shift_end.time() == time(7,30):  # night shift
                window_end = datetime.combine(shift_start.date()+timedelta(days=1), time(8,0))
            else:
                window_end = shift_end + timedelta(hours=1)
            window_start = shift_start - timedelta(hours=2)
            exits = exits[(exits["datetime"] >= window_start) & (exits["datetime"] <= window_end)]
            if not exits.empty:
                mo = exits[exits["location_norm"]=="Main"]["datetime"]
                lo = exits[exits["location_norm"]=="LMC"]["datetime"]
                if not mo.empty: main_out = mo.min()
                if not lo.empty: lmc_out = lo.min()

        # work start/end
        work_start = main_in if not pd.isna(main_in) else lmc_in
        work_end   = main_out if not pd.isna(main_out) else lmc_out
        work_hours = (work_end - work_start).total_seconds()/3600 if (pd.notna(work_start) and pd.notna(work_end)) else 0

        summary_rows.append({
            "Employee Number": emp,
            "Date": d,
            "Shift Start": shift_start,
            "Shift End": shift_end,
            "Main In": main_in,
            "LMC In": lmc_in,
            "Main Out": main_out,
            "LMC Out": lmc_out,
            "Work Hours": round(work_hours,2)
        })

summary_df = pd.DataFrame(summary_rows)

# remove rows with no In/Out at all (e.g., night shift duplicate)
summary_df = summary_df[~(summary_df[["Main In","LMC In","Main Out","LMC Out"]].isna().all(axis=1))]

print(summary_df)
# summary_df.to_excel("clean_summary.xlsx", index=False)