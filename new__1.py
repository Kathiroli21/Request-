import re
import pandas as pd

def parse_payslips(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split based on "Employee No"
    blocks = re.split(r'(?=Employee No\s*:)', content)

    all_records = []
    all_earning_keys = set()
    all_deduction_keys = set()

    for block in blocks:
        if not block.strip():
            continue

        data = {}

        # Extract top-level fields
        fields = {
            'Employee No': r'Employee No\s*:\s*(\d+)',
            'Name': r'Name\s*:\s*(.+)',
            'Department': r'Department\s*:\s*(.+)',
            'Working Days': r'Working Days\s*:\s*([\d.]+)',
            'Net Amount': r'Net Amount\s*:\s*([\d,\.]+)'
        }

        for key, pattern in fields.items():
            match = re.search(pattern, block)
            if match:
                data[key] = match.group(1).strip()

        # Extract Earnings and Deductions
        lines = block.splitlines()
        capture = None
        for line in lines:
            if 'Earnings' in line and 'Deductions' in line:
                capture = 'both'
                continue
            elif 'Total' in line:
                capture = None
                continue
            elif capture == 'both':
                # Split earnings and deductions side-by-side
                left = line[:40].strip()
                right = line[40:].strip()

                if left:
                    parts = left.rsplit(' ', 1)
                    if len(parts) == 2:
                        key, val = parts
                        key = key.strip()
                        val = val.replace(",", "").strip()
                        data[f"Earning: {key}"] = float(val)
                        all_earning_keys.add(f"Earning: {key}")

                if right:
                    parts = right.rsplit(' ', 1)
                    if len(parts) == 2:
                        key, val = parts
                        key = key.strip()
                        val = val.replace(",", "").strip()
                        data[f"Deduction: {key}"] = float(val)
                        all_deduction_keys.add(f"Deduction: {key}")

        all_records.append(data)

    # Ensure all records have same keys
    all_keys = ['Employee No', 'Name', 'Department', 'Working Days', 'Net Amount'] + \
               sorted(all_earning_keys) + sorted(all_deduction_keys)

    for rec in all_records:
        for key in all_keys:
            rec.setdefault(key, 0)

    df = pd.DataFrame(all_records)
    df.to_excel("Parsed_Payslips.xlsx", index=False)
    print("Excel file saved as: Parsed_Payslips.xlsx")

# ---------- USAGE ----------
# Replace 'payslips.txt' with your actual file name
parse_payslips("payslips.txt")