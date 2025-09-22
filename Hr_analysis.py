import pandas as pd

file_path = "your_file.xlsx"
df = pd.read_excel(file_path)

df["Attendance or Absence Type"] = df["Attendance or Absence Type"].str.strip().str.lower()
df["Start"] = pd.to_datetime(df["Start"], dayfirst=True, errors="coerce")
df["End"] = pd.to_datetime(df["End"], dayfirst=True, errors="coerce")

if "Tot. cal.days" not in df.columns:
    df["Tot. cal.days"] = (df["End"] - df["Start"]).dt.days + 1

df = df.sort_values(["Pers.No.", "Start"])

combined_issues = []
for emp, group in df.groupby("Pers.No."):
    group = group.sort_values("Start").reset_index(drop=True)
    for i in range(len(group) - 1):
        leave1 = group.loc[i, "Attendance or Absence Type"]
        leave2 = group.loc[i+1, "Attendance or Absence Type"]
        end1 = group.loc[i, "End"]
        start2 = group.loc[i+1, "Start"]
        if (start2 - end1).days <= 1:
            if (("privilege leave" in leave1 or "casual leave" in leave1) and ("medical" in leave2 or "sick" in leave2)) or (("privilege leave" in leave2 or "casual leave" in leave2) and ("medical" in leave1 or "sick" in leave1)):
                combined_issues.append((emp, group.loc[i, "Start"], group.loc[i+1, "End"]))

pl_less_than_3 = df[(df["Attendance or Absence Type"].str.contains("privilege leave", case=False)) & (df["Tot. cal.days"] < 3)]

df["Year"] = df["Start"].dt.year
pl_counts = df[df["Attendance or Absence Type"].str.contains("privilege leave", case=False)].groupby(["Pers.No.", "Year"]).size().reset_index(name="PL_Occasions")
pl_more_than_3 = pl_counts[pl_counts["PL_Occasions"] > 3]

print("Combined PL/CL with Sick Leave:")
print(combined_issues)

print("\nPrivilege Leave less than 3 days:")
print(pl_less_than_3[["Pers.No.", "Start", "End", "Tot. cal.days"]])

print("\nEmployees with more than 3 PL occasions in a year:")
print(pl_more_than_3)

with pd.ExcelWriter("leave_analysis_output.xlsx") as writer:
    pd.DataFrame(combined_issues, columns=["Pers.No.", "Start", "End"]).to_excel(writer, sheet_name="Combined_Issues", index=False)
    pl_less_than_3.to_excel(writer, sheet_name="PL_Less_Than_3", index=False)
    pl_more_than_3.to_excel(writer, sheet_name="PL_More_Than_3", index=False)