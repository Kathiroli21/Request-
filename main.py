from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_cors import CORS, cross_origin
import pandas as pd
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-123'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
Session(app)

CORS(app, supports_credentials=True, origins=["http://localhost:5000"])

# Configuration
EXCEL_FILE = 'requests.xlsx'
REQUEST_TYPES_FILE = 'request_types.txt'
DESCRIPTIONS_FILE = 'descriptions.json'
USERS_FILE = 'users.txt'

# Initialize files
def init_files():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=[
            'request_id', 'sno', 'request_type', 'description', 'custom_description',
            'raiser_name', 'raiser_username', 'updates', 'status', 'created_at',
            'current_admin', 'approval_path', 'last_updated', 'notification_sent'
        ])
        df.to_excel(EXCEL_FILE, index=False)
    
    if not os.path.exists(REQUEST_TYPES_FILE):
        with open(REQUEST_TYPES_FILE, 'w') as f:
            f.write("IT Support\nHR Query\nFacilities\nFinance")
    
    if not os.path.exists(DESCRIPTIONS_FILE):
        with open(DESCRIPTIONS_FILE, 'w') as f:
            json.dump({
                "IT Support": ["New laptop request", "Network issue", "Software installation"],
                "HR Query": ["Leave request", "Salary query", "Policy clarification"],
                "Facilities": ["Chair replacement", "AC repair", "Cab booking"],
                "Finance": ["Expense claim", "Invoice query", "Travel advance"]
            }, f)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            f.write("admin1:password1:admin1\nadmin2:password2:admin2\nadmin3:password3:admin3\nuser1:user123:user")

# Get request types
def get_request_types():
    with open(REQUEST_TYPES_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# Get predefined descriptions
def get_predefined_descriptions():
    with open(DESCRIPTIONS_FILE, 'r') as f:
        return json.load(f)

# Save predefined descriptions
def save_predefined_descriptions(descriptions):
    with open(DESCRIPTIONS_FILE, 'w') as f:
        json.dump(descriptions, f)

# Add request type
def add_request_type(type_name):
    types = get_request_types()
    if type_name not in types:
        with open(REQUEST_TYPES_FILE, 'a') as f:
            f.write(f"\n{type_name}")
        
        descriptions = get_predefined_descriptions()
        descriptions[type_name] = []
        save_predefined_descriptions(descriptions)

# Remove request type
def remove_request_type(type_name):
    types = get_request_types()
    if type_name in types:
        types.remove(type_name)
        with open(REQUEST_TYPES_FILE, 'w') as f:
            f.write("\n".join(types))
        
        descriptions = get_predefined_descriptions()
        if type_name in descriptions:
            del descriptions[type_name]
            save_predefined_descriptions(descriptions)

# Get users
def get_users():
    users = {}
    with open(USERS_FILE, 'r') as f:
        for line in f.readlines():
            if line.strip():
                username, password, role = line.strip().split(':')
                users[username] = {'password': password, 'role': role}
    return users

# Add user
def add_user(username, password, role):
    with open(USERS_FILE, 'a') as f:
        f.write(f"\n{username}:{password}:{role}")

# Routes
@app.route('/api/login', methods=['POST'])
@cross_origin(supports_credentials=True)
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    users = get_users()
    
    if username in users and users[username]['password'] == password:
        session['user'] = username
        session['role'] = users[username]['role']
        return jsonify({
            'success': True,
            'role': users[username]['role'],
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

@app.route('/api/request-types', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_request_types_api():
    return jsonify({
        'types': get_request_types(),
        'predefined_descriptions': get_predefined_descriptions()
    })

@app.route('/api/request-types', methods=['POST', 'DELETE'])
@cross_origin(supports_credentials=True)
def manage_request_types():
    if 'user' not in session or session['role'] not in ['admin1', 'admin2', 'admin3']:
        return jsonify({'error': 'Unauthorized'}), 401
    
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

@app.route('/api/request-types/descriptions', methods=['GET', 'POST', 'DELETE'])
@cross_origin(supports_credentials=True)
def manage_descriptions():
    if 'user' not in session or session['role'] not in ['admin1', 'admin2', 'admin3']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    request_type = data.get('request_type')
    description = data.get('description')
    
    if request.method == 'GET':
        return jsonify(get_predefined_descriptions())
    
    descriptions = get_predefined_descriptions()
    
    if request.method == 'POST':
        if not request_type or not description:
            return jsonify({'error': 'Request type and description required'}), 400
        
        if request_type not in descriptions:
            descriptions[request_type] = []
        
        if description not in descriptions[request_type]:
            descriptions[request_type].append(description)
            save_predefined_descriptions(descriptions)
            return jsonify({'success': True})
        return jsonify({'error': 'Description already exists'}), 400
    
    if request.method == 'DELETE':
        if not request_type or not description:
            return jsonify({'error': 'Request type and description required'}), 400
        
        if request_type in descriptions and description in descriptions[request_type]:
            descriptions[request_type].remove(description)
            save_predefined_descriptions(descriptions)
            return jsonify({'success': True})
        return jsonify({'error': 'Description not found'}), 404

@app.route('/api/requests', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def handle_requests():
    if request.method == 'GET':
        df = pd.read_excel(EXCEL_FILE).fillna('')
        
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user_role = session['role']
        username = session['user']
        
        if user_role == 'user':
            df = df[df['raiser_username'] == username]
        else:
            status_filter = request.args.get('status', 'all')
            if status_filter != 'all':
                df = df[df['status'] == status_filter]
        
        return jsonify(df.to_dict('records'))
    
    if request.method == 'POST':
        data = request.get_json()
        required_fields = ['request_type', 'description', 'custom_description', 'raiser_name']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        df = pd.read_excel(EXCEL_FILE)
        new_sno = df['sno'].max() + 1 if not df.empty else 1
        
        request_id = str(uuid.uuid4())
        
        full_description = data['description']
        if data['custom_description']:
            full_description += f" - {data['custom_description']}"
        
        new_request = {
            'request_id': request_id,
            'sno': new_sno,
            'request_type': data['request_type'],
            'description': full_description,
            'custom_description': data['custom_description'],
            'raiser_name': data['raiser_name'],
            'raiser_username': session.get('user', ''),
            'updates': f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Request created by {data['raiser_name']} - Pending admin1 approval",
            'status': 'Open',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_admin': 'admin1',
            'approval_path': 'admin1',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'notification_sent': False
        }
        
        df = pd.concat([df, pd.DataFrame([new_request])], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
        
        return jsonify({'success': True, 'request_id': request_id})

@app.route('/api/requests/<string:request_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_request(request_id):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_role = session['role']
    username = session['user']
    
    data = request.get_json()
    df = pd.read_excel(EXCEL_FILE)
    
    if request_id not in df['request_id'].values:
        return jsonify({'error': 'Request not found'}), 404
    
    idx = df.index[df['request_id'] == request_id].tolist()[0]
    current_admin = df.at[idx, 'current_admin']
    
    # Admin1 has full control, others only control their own requests
    if user_role != 'admin1' and user_role != current_admin:
        return jsonify({'error': 'Not authorized to update this request'}), 403
    
    if 'update_text' in data and (user_role == 'admin1' or user_role == current_admin):
        new_update = f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {username}: {data['update_text']}"
        df.at[idx, 'updates'] += new_update
        if 'status' in data:
            df.at[idx, 'status'] = data['status']
    
    if 'next_admin' in data and (user_role == 'admin1' or user_role == current_admin):
        next_admin = data['next_admin']
        
        if user_role == 'admin1':
            valid_next = ['admin2', 'admin3']
        elif user_role == 'admin2':
            valid_next = ['admin3']
        else:
            valid_next = []
        
        if next_admin not in valid_next:
            return jsonify({'error': 'Invalid next admin'}), 400
        
        df.at[idx, 'current_admin'] = next_admin
        df.at[idx, 'approval_path'] += f"->{next_admin}"
        df.at[idx, 'updates'] += f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Forwarded to {next_admin} by {username}"
        df.at[idx, 'notification_sent'] = False
    
    df.at[idx, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df.to_excel(EXCEL_FILE, index=False)
    
    return jsonify({'success': True})

@app.route('/api/dashboard', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_dashboard():
    if 'user' not in session or session['role'] not in ['admin1', 'admin2', 'admin3']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    df = pd.read_excel(EXCEL_FILE).fillna('')
    
    # General stats
    total_requests = len(df)
    open_requests = len(df[df['status'] == 'Open'])
    closed_requests = len(df[df['status'] == 'Closed'])
    
    # Requests by type
    requests_by_type = df['request_type'].value_counts().to_dict()
    
    # Requests by status
    requests_by_status = df['status'].value_counts().to_dict()
    
    # Pending requests for current admin
    current_admin = session['role']
    pending_requests = len(df[(df['current_admin'] == current_admin) & (df['status'] == 'Open')])
    
    return jsonify({
        'total_requests': total_requests,
        'open_requests': open_requests,
        'closed_requests': closed_requests,
        'requests_by_type': requests_by_type,
        'requests_by_status': requests_by_status,
        'pending_requests': pending_requests
    })

if __name__ == '__main__':
    init_files()
    app.run(debug=True, host='0.0.0.0', port=5000)
