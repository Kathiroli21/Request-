# app.py
from flask import Flask, request, jsonify
from openpyxl import load_workbook
from datetime import datetime
import os

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
    
    # Allocations sheet
    ws_alloc = wb.create_sheet("Allocations")
    ws_alloc.append(["AllocationID", "MemberID", "Description", "Section", "FromDate", "ToDate", "FinancialYear"])
    
    wb.save(DB_FILE)

def get_financial_year(date_str):
    """Get financial year (April-March) for a given date"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    if date.month >= 4:
        return f"{date.year}-{date.year+1}"
    return f"{date.year-1}-{date.year}"

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
    from_date = data['fromDate']
    to_date = data['toDate']
    
    wb = load_workbook(DB_FILE)
    ws_alloc = wb["Allocations"]
    
    # Get all allocated member IDs for the date range
    allocated_member_ids = set()
    for row in ws_alloc.iter_rows(min_row=2, values_only=True):
        alloc_from = row[4] if isinstance(row[4], str) else row[4].strftime('%Y-%m-%d')
        alloc_to = row[5] if isinstance(row[5], str) else row[5].strftime('%Y-%m-%d')
        
        # Check for date overlap
        if not (to_date < alloc_from or from_date > alloc_to):
            allocated_member_ids.add(row[1])
    
    # Get all members not in allocated list
    ws_members = wb["Members"]
    available_members = []
    for row in ws_members.iter_rows(min_row=2, values_only=True):
        if row[0] not in allocated_member_ids:
            available_members.append({
                "id": row[0],
                "name": row[1]
            })
    
    return jsonify(available_members)

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
    current_year = datetime.now().year
    allocation_date = datetime.strptime(data['fromDate'], '%Y-%m-%d')
    
    # Validate: Cannot modify past allocations
    if allocation_date.year < current_year:
        return jsonify({"error": "Cannot create allocations for past years"}), 400
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    # Generate new ID
    new_id = max([row[0] for row in ws.iter_rows(min_row=2, values_only=True)] or [0]) + 1
    
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
    current_date = datetime.now().date()
    from_date = datetime.strptime(data['fromDate'], '%Y-%m-%d').date()
    
    # Validate: Cannot modify past allocations
    if from_date < current_date:
        return jsonify({"error": "Cannot modify past allocations"}), 400
    
    wb = load_workbook(DB_FILE)
    ws = wb["Allocations"]
    
    # Find and update allocation
    for row in ws.iter_rows(min_row=2):
        if row[0].value == alloc_id:
            row[2].value = data['description']  # Description
            row[3].value = data['section']      # Section
            row[4].value = data['fromDate']     # From Date
            row[5].value = data['toDate']      # To Date
            break
    
    wb.save(DB_FILE)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)