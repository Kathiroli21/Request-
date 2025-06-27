from flask import Flask, request, jsonify
from openpyxl import load_workbook, Workbook
from datetime import datetime, timedelta
import os
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Database file
DB_FILE = 'audit_allocations.xlsx'

# Initialize database if not exists
if not os.path.exists(DB_FILE):
    wb = Workbook()
    # Members sheet
    ws_members = wb.active
    ws_members.title = "Members"
    ws_members.append(["MemberID", "Name", "Email", "Department"])
    
    # Add some sample members
    sample_members = [
        [1, "John Doe", "john@example.com", "Audit"],
        [2, "Jane Smith", "jane@example.com", "Tax"],
        [3, "Mike Johnson", "mike@example.com", "Advisory"],
        [4, "Sarah Williams", "sarah@example.com", "Audit"],
        [5, "David Brown", "david@example.com", "Tax"]
    ]
    for member in sample_members:
        ws_members.append(member)
    
    # Allocations sheet
    ws_alloc = wb.create_sheet("Allocations")
    ws_alloc.append(["AllocationID", "MemberID", "Description", "Section", "FromDate", "ToDate", "FinancialYear"])
    
    # Add some sample allocations
    today = datetime.now().date()
    sample_allocations = [
        [1, 1, "Annual Financial Audit", "Section 1", (today - timedelta(days=30)).isoformat(), (today - timedelta(days=15)).isoformat(), get_financial_year((today - timedelta(days=30)).isoformat())],
        [2, 2, "Tax Compliance Review", "Section 2", (today - timedelta(days=10)).isoformat(), (today + timedelta(days=5)).isoformat(), get_financial_year((today - timedelta(days=10)).isoformat())],
        [3, 3, "Internal Controls Assessment", "Section 3", (today + timedelta(days=5)).isoformat(), (today + timedelta(days=15)).isoformat(), get_financial_year((today + timedelta(days=5)).isoformat())],
        [4, 4, "SOX Compliance", "Section 4", (today + timedelta(days=20)).isoformat(), (today + timedelta(days=30)).isoformat(), get_financial_year((today + timedelta(days=20)).isoformat())]
    ]
    for alloc in sample_allocations:
        ws_alloc.append(alloc)
    
    wb.save(DB_FILE)

def get_financial_year(date_str):
    """Get financial year (April-March) for a given date"""
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    if date.month >= 4:
        return f"{date.year}-{date.year+1}"
    return f"{date.year-1}-{date.year}"

def is_available(member_id, from_date, to_date):
    """Check if member is available for given date range"""
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] == member_id:
            alloc_from = datetime.strptime(row[4], '%Y-%m-%d').date() if isinstance(row[4], str) else row[4].date()
            alloc_to = datetime.strptime(row[5], '%Y-%m-%d').date() if isinstance(row[5], str) else row[5].date()
            
            # Check for date overlap
            if not (to_date < alloc_from or from_date > alloc_to):
                return False
    return True

@app.route('/api/members', methods=['GET'])
def get_members():
    """Get all members"""
    wb = load_workbook(DB_FILE)
    ws = wb["Members"]
    members = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        members.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "department": row[3]
        })
    return jsonify(members)

@app.route('/api/available-members', methods=['POST'])
def get_available_members():
    """Get members available for given date range"""
    data = request.json
    from_date = datetime.strptime(data['fromDate'], '%Y-%m-%d').date()
    to_date = datetime.strptime(data['toDate'], '%Y-%m-%d').date()
    
    wb = load_workbook(DB_FILE)
    ws_members = wb["Members"]
    available_members = []
    
    for row in ws_members.iter_rows(min_row=2, values_only=True):
        if is_available(row[0], from_date, to_date):
            available_members.append({
                "id": row[0],
                "name": row[1]
            })
    
    return jsonify(available_members)

@app.route('/api/suggest-dates', methods=['POST'])
def suggest_dates():
    """Suggest available date ranges for a member"""
    data = request.json
    member_id = data['memberId']
    days_required = int(data['daysRequired'])
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    # Get all allocations for this member, sorted by date
    member_allocations = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] == member_id:
            alloc_from = datetime.strptime(row[4], '%Y-%m-%d').date() if isinstance(row[4], str) else row[4].date()
            alloc_to = datetime.strptime(row[5], '%Y-%m-%d').date() if isinstance(row[5], str) else row[5].date()
            member_allocations.append((alloc_from, alloc_to))
    
    # Sort allocations by start date
    member_allocations.sort()
    
    today = datetime.now().date()
    suggestions = []
    
    # Check availability before first allocation
    if len(member_allocations) > 0:
        first_alloc_start = member_allocations[0][0]
        available_days = (first_alloc_start - today).days
        if available_days >= days_required:
            suggestions.append({
                "startDate": today.isoformat(),
                "endDate": (today + timedelta(days=days_required - 1)).isoformat(),
                "availableDays": available_days
            })
    
    # Check gaps between allocations
    for i in range(len(member_allocations) - 1):
        current_end = member_allocations[i][1]
        next_start = member_allocations[i+1][0]
        
        if next_start > current_end:
            gap_days = (next_start - current_end).days - 1
            if gap_days >= days_required:
                start_date = current_end + timedelta(days=1)
                suggestions.append({
                    "startDate": start_date.isoformat(),
                    "endDate": (start_date + timedelta(days=days_required - 1)).isoformat(),
                    "availableDays": gap_days
                })
    
    # Check availability after last allocation
    if len(member_allocations) > 0:
        last_alloc_end = member_allocations[-1][1]
        start_date = last_alloc_end + timedelta(days=1)
        suggestions.append({
            "startDate": start_date.isoformat(),
            "endDate": (start_date + timedelta(days=days_required - 1)).isoformat(),
            "availableDays": 365  # Arbitrary large number
        })
    else:
        # No allocations at all - suggest starting today
        suggestions.append({
            "startDate": today.isoformat(),
            "endDate": (today + timedelta(days=days_required - 1)).isoformat(),
            "availableDays": 365
        })
    
    # Sort suggestions by start date
    suggestions.sort(key=lambda x: x['startDate'])
    
    return jsonify(suggestions[:5])  # Return top 5 suggestions

@app.route('/api/allocations', methods=['GET'])
def get_allocations():
    """Get all allocations for a financial year"""
    financial_year = request.args.get('financialYear')
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    allocations = []
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_fy = row[6] if isinstance(row[6], str) else get_financial_year(row[4].strftime('%Y-%m-%d'))
        if row_fy == financial_year:
            allocations.append({
                "id": row[0],
                "memberId": row[1],
                "description": row[2],
                "section": row[3],
                "fromDate": row[4].strftime('%Y-%m-%d') if not isinstance(row[4], str) else row[4],
                "toDate": row[5].strftime('%Y-%m-%d') if not isinstance(row[5], str) else row[5],
                "financialYear": row_fy
            })
    
    return jsonify(allocations)

@app.route('/api/allocations', methods=['POST'])
def create_allocation():
    """Create new allocation"""
    data = request.json
    today = datetime.now().date()
    from_date = datetime.strptime(data['fromDate'], '%Y-%m-%d').date()
    to_date = datetime.strptime(data['toDate'], '%Y-%m-%d').date()
    
    # Validate dates
    if from_date > to_date:
        return jsonify({"error": "From date cannot be after to date"}), 400
    
    # Check if member is available
    if not is_available(data['memberId'], from_date, to_date):
        return jsonify({"error": "Member is not available for the selected dates"}), 400
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    # Generate new ID
    existing_ids = [row[0] for row in ws.iter_rows(min_row=2, values_only=True)]
    new_id = max(existing_ids) + 1 if existing_ids else 1
    
    # Add new allocation
    financial_year = get_financial_year(data['fromDate'])
    ws.append([
        new_id,
        data['memberId'],
        data['description'],
        data['section'],
        data['fromDate'],
        data['toDate'],
        financial_year
    ])
    
    wb.save(DB_FILE)
    return jsonify({"success": True, "id": new_id})

@app.route('/api/allocations/<int:alloc_id>', methods=['PUT'])
def update_allocation(alloc_id):
    """Update existing allocation"""
    data = request.json
    today = datetime.now().date()
    from_date = datetime.strptime(data['fromDate'], '%Y-%m-%d').date()
    to_date = datetime.strptime(data['toDate'], '%Y-%m-%d').date()
    
    # Validate dates
    if from_date > to_date:
        return jsonify({"error": "From date cannot be after to date"}), 400
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    # Find the allocation
    for row in ws.iter_rows(min_row=2):
        if row[0].value == alloc_id:
            original_from = datetime.strptime(row[4].value, '%Y-%m-%d').date() if isinstance(row[4].value, str) else row[4].value.date()
            original_to = datetime.strptime(row[5].value, '%Y-%m-%d').date() if isinstance(row[5].value, str) else row[5].value.date()
            
            # Validate: Cannot move allocation to the past
            if from_date < today and from_date != original_from:
                return jsonify({"error": "Cannot move allocation to the past"}), 400
            
            # Validate: Cannot shorten allocation to before today for current allocations
            if original_from <= today <= original_to:
                if from_date > original_from:
                    return jsonify({"error": "Cannot move start date forward for current allocation"}), 400
                if to_date < today:
                    return jsonify({"error": "Cannot set end date before today for current allocation"}), 400
            
            # Check if member is available for new dates (excluding this allocation)
            temp_from = row[4].value
            temp_to = row[5].value
            row[4].value = "2000-01-01"  # Temporary value to exclude from availability check
            row[5].value = "2000-01-01"
            
            if not is_available(row[1].value, from_date, to_date):
                row[4].value = temp_from
                row[5].value = temp_to
                return jsonify({"error": "Member is not available for the selected dates"}), 400
            
            # Restore original values if check passed
            row[4].value = temp_from
            row[5].value = temp_to
            
            # Update the allocation
            row[2].value = data['description']  # Description
            row[3].value = data['section']      # Section
            row[4].value = data['fromDate']     # From Date
            row[5].value = data['toDate']       # To Date
            break
    
    wb.save(DB_FILE)
    return jsonify({"success": True})

@app.route('/api/allocations/<int:alloc_id>', methods=['DELETE'])
def delete_allocation(alloc_id):
    """Delete an allocation"""
    today = datetime.now().date()
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    # Find the allocation
    for row in ws.iter_rows(min_row=2):
        if row[0].value == alloc_id:
            from_date = datetime.strptime(row[4].value, '%Y-%m-%d').date() if isinstance(row[4].value, str) else row[4].value.date()
            
            # Validate: Cannot delete past allocations
            if from_date < today:
                return jsonify({"error": "Cannot delete past allocations"}), 400
            
            # Delete the row
            ws.delete_rows(row[0].row)
            break
    
    wb.save(DB_FILE)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)