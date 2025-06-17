from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_cors import CORS, cross_origin
import pandas as pd
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-123'  # Change this for production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # For HTTPS
Session(app)

CORS(app, supports_credentials=True, origins=["http://localhost"])  # Adjust for your frontend URL

# Configuration
EXCEL_FILE = 'requests.xlsx'
REQUEST_TYPES_FILE = 'request_types.txt'
ADMINS = {
    'admin1': {'password': generate_password_hash('password1'), 'role': 'admin1'},
    'admin2': {'password': generate_password_hash('password2'), 'role': 'admin2'},
    'admin3': {'password': generate_password_hash('password3'), 'role': 'admin3'}
}

# Initialize files
def init_files():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=[
            'sno', 'request_type', 'description', 'raiser_name',
            'updates', 'status', 'created_at', 'current_admin',
            'approval_path', 'last_updated', 'notification_sent'
        ])
        df.to_excel(EXCEL_FILE, index=False)
    
    if not os.path.exists(REQUEST_TYPES_FILE):
        with open(REQUEST_TYPES_FILE, 'w') as f:
            f.write("IT Support\nHR Query\nFacilities\nFinance")

# Get request types
def get_request_types():
    with open(REQUEST_TYPES_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# Add request type
def add_request_type(type_name):
    types = get_request_types()
    if type_name not in types:
        with open(REQUEST_TYPES_FILE, 'a') as f:
            f.write(f"\n{type_name}")

# Remove request type
def remove_request_type(type_name):
    types = get_request_types()
    if type_name in types:
        types.remove(type_name)
        with open(REQUEST_TYPES_FILE, 'w') as f:
            f.write("\n".join(types))

# Routes
@app.route('/api/login', methods=['POST'])
@cross_origin(supports_credentials=True)
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username in ADMINS and check_password_hash(ADMINS[username]['password'], password):
        session['user'] = username
        session['role'] = ADMINS[username]['role']
        return jsonify({
            'success': True,
            'role': ADMINS[username]['role'],
            'message': 'Login successful'
        })
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/check-auth', methods=['GET'])
@cross_origin(supports_credentials=True)
def check_auth():
    if 'user' in session:
        return jsonify({
            'success': True,
            'user': session['user'],
            'role': session['role']
        })
    return jsonify({'success': False}), 401

@app.route('/api/logout', methods=['POST'])
@cross_origin(supports_credentials=True)
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/request-types', methods=['GET', 'POST', 'DELETE'])
@cross_origin(supports_credentials=True)
def handle_request_types():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        return jsonify(get_request_types())
    
    data = request.get_json()
    type_name = data.get('type_name')
    
    if request.method == 'POST':
        if not type_name:
            return jsonify({'error': 'Type name required'}), 400
        add_request_type(type_name)
        return jsonify({'success': True})
    
    if request.method == 'DELETE':
        if not type_name:
            return jsonify({'error': 'Type name required'}), 400
        remove_request_type(type_name)
        return jsonify({'success': True})

@app.route('/api/requests', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def handle_requests():
    if request.method == 'GET':
        df = pd.read_excel(EXCEL_FILE).fillna('')
        status_filter = request.args.get('status', 'all')
        
        if status_filter != 'all':
            df = df[df['status'] == status_filter]
        
        return jsonify(df.to_dict('records'))
    
    if request.method == 'POST':
        data = request.get_json()
        required_fields = ['request_type', 'description', 'raiser_name']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        df = pd.read_excel(EXCEL_FILE)
        new_sno = df['sno'].max() + 1 if not df.empty else 1
        
        new_request = {
            'sno': new_sno,
            'request_type': data['request_type'],
            'description': data['description'],
            'raiser_name': data['raiser_name'],
            'updates': 'Request created - Pending admin1 approval',
            'status': 'Open',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_admin': 'admin1',
            'approval_path': 'admin1',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'notification_sent': False
        }
        
        df = pd.concat([df, pd.DataFrame([new_request])], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
        
        return jsonify({'success': True, 'sno': new_sno})

@app.route('/api/requests/<int:sno>', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_request(sno):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    df = pd.read_excel(EXCEL_FILE)
    
    if sno not in df['sno'].values:
        return jsonify({'error': 'Request not found'}), 404
    
    idx = df.index[df['sno'] == sno].tolist()[0]
    current_admin = df.at[idx, 'current_admin']
    user_role = session['role']
    
    if user_role != current_admin:
        return jsonify({'error': 'Not authorized to update this request'}), 403
    
    if 'next_admin' in data:
        next_admin = data['next_admin']
        valid_next = ['admin2', 'admin3'] if user_role == 'admin1' else ['admin3']
        
        if next_admin not in valid_next:
            return jsonify({'error': 'Invalid next admin'}), 400
        
        df.at[idx, 'current_admin'] = next_admin
        df.at[idx, 'approval_path'] += f"->{next_admin}"
        df.at[idx, 'updates'] += f"\nSent to {next_admin} for approval"
        df.at[idx, 'notification_sent'] = False
    
    if 'approve' in data:
        if user_role == 'admin2':
            df.at[idx, 'updates'] += f"\nApproved by admin2 - Pending admin3 approval"
            df.at[idx, 'current_admin'] = 'admin3'
            df.at[idx, 'approval_path'] += '->admin3'
        elif user_role == 'admin3':
            df.at[idx, 'status'] = 'Closed'
            df.at[idx, 'updates'] += f"\nApproved by admin3 - Request closed"
        df.at[idx, 'notification_sent'] = False
    
    df.at[idx, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df.to_excel(EXCEL_FILE, index=False)
    
    return jsonify({'success': True})

@app.route('/api/notifications', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_notifications():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_role = session['role']
    df = pd.read_excel(EXCEL_FILE).fillna('')
    
    # Get pending notifications for current admin
    notifications = df[(df['current_admin'] == user_role) & (df['notification_sent'] == False)]
    
    # Mark notifications as sent
    if not notifications.empty:
        for idx in notifications.index:
            df.at[idx, 'notification_sent'] = True
        df.to_excel(EXCEL_FILE, index=False)
    
    return jsonify(notifications.to_dict('records'))

if __name__ == '__main__':
    init_files()
    app.run(debug=True, host='0.0.0.0', port=5000)
