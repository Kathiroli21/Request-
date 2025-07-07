import pandas as pd
from datetime import datetime, timedelta

def analyze_punch_data(punch_in_file, punch_out_file):
    # Read the CSV files
    punch_in_df = pd.read_csv(punch_in_file)
    punch_out_df = pd.read_csv(punch_out_file)

    # Data Cleaning and Preparation
    punch_in_df["in_datetime"] = pd.to_datetime(punch_in_df["in_date"] + " " + punch_in_df["punchin_time"], format="%d-%m-%Y %H:%M:%S")
    punch_out_df["out_datetime"] = pd.to_datetime(punch_out_df["Date"] + " " + punch_out_df["punch_out_time"], format="%d-%m-%Y %H:%M:%S")

    # Sort by person number and datetime
    punch_in_df = punch_in_df.sort_values(by=["Persno", "in_datetime"])
    punch_out_df = punch_out_df.sort_values(by=["persno", "out_datetime"])

    # Merge the dataframes
    merged_df = pd.merge(punch_in_df, punch_out_df, left_on="Persno", right_on="persno", how="outer", suffixes=("_in", "_out"))

    # Identify overnight shifts
    # An overnight punch is defined as a punch-in on one day and a punch-out on the next day, within a reasonable timeframe (e.g., less than 12 hours total duration)
    # For the edge case provided (39305, 22:29:00 on 01-04-2024 and 07:30:00 on 02-04-2024), the time difference is 9 hours and 1 minute.
    # This condition (time_diff > 0 and time_diff < 12 hours) correctly identifies such cases.
    merged_df["time_diff"] = merged_df["out_datetime"] - merged_df["in_datetime"]
    overnight_punches = merged_df[(merged_df["time_diff"] > timedelta(hours=0)) & (merged_df["time_diff"] < timedelta(hours=12))]

    # Identify punch in without punch out
    punch_in_without_out = merged_df[merged_df["out_datetime"].isnull()]

    # Identify punch out without punch in
    punch_out_without_in = merged_df[merged_df["in_datetime"].isnull()]

    # Both punch in and punch out
    both_in_and_out = merged_df.dropna(subset=["in_datetime", "out_datetime"])

    print("\n--- Punch In without Punch Out ---")
    print(punch_in_without_out)
    print("\n--- Punch Out without Punch In ---")
    print(punch_out_without_in)
    print("\n--- Both Punch In and Out ---")
    print(both_in_and_out)
    print("\n--- Overnight Punches ---")
    print(overnight_punches)

    # Save to excel
    with pd.ExcelWriter("punch_analysis_results.xlsx") as writer:
        punch_in_without_out.to_excel(writer, sheet_name="Punch In without Punch Out", index=False)
        punch_out_without_in.to_excel(writer, sheet_name="Punch Out without Punch In", index=False)
        both_in_and_out.to_excel(writer, sheet_name="Both Punch In and Out", index=False)
        overnight_punches.to_excel(writer, sheet_name="Overnight Punches", index=False)

if __name__ == "__main__":
    analyze_punch_data("punch_in_data.csv", "punch_out_data.csv")


