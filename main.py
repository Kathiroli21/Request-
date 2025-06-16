from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
EXCEL_FILE = 'requests.xlsx'
ADMIN_USERS = {
    'admin1': generate_password_hash('password1'),
    'admin2': generate_password_hash('password2'),
    'admin3': generate_password_hash('password3')
}

# Helper function to initialize or get DataFrame
def get_dataframe():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=[
            'sno', 
            'request_type', 
            'description', 
            'raiser_name',
            'updates', 
            'status', 
            'created_at'
        ])
        df.to_excel(EXCEL_FILE, index=False)
        return df
    return pd.read_excel(EXCEL_FILE)

# Helper function to save DataFrame
def save_dataframe(df):
    df.to_excel(EXCEL_FILE, index=False)

# Authentication middleware
def check_auth():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    # In a real app, you would validate JWT or session token here
    return True

# Routes
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Missing credentials'}), 400
    
    username = data['username']
    password = data['password']
    
    if username in ADMIN_USERS and check_password_hash(ADMIN_USERS[username], password):
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'token': 'dummy-token'  # In real app, return JWT
        })
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/requests', methods=['GET'])
def get_requests():
    try:
        df = get_dataframe()
        # Convert NaN values to empty strings for JSON serialization
        df = df.fillna('')
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/requests', methods=['POST'])
def create_request():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['request_type', 'description', 'raiser_name']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate field types and content
    if not isinstance(data.get('raiser_name'), str) or not data['raiser_name'].strip():
        return jsonify({'error': 'Invalid raiser name'}), 400
    if not isinstance(data.get('description'), str) or not data['description'].strip():
        return jsonify({'error': 'Invalid description'}), 400
    
    try:
        df = get_dataframe()
        
        # Generate new SNo
        new_sno = df['sno'].max() + 1 if not df.empty else 1
        
        # Create new request
        new_request = {
            'sno': new_sno,
            'request_type': data['request_type'].strip(),
            'description': data['description'].strip(),
            'raiser_name': data['raiser_name'].strip(),
            'updates': 'Request created',
            'status': 'Open',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add to DataFrame
        df = pd.concat([df, pd.DataFrame([new_request])], ignore_index=True)
        save_dataframe(df)
        
        return jsonify({
            'success': True, 
            'sno': new_sno,
            'message': 'Request created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/requests/<int:sno>', methods=['PUT'])
def update_request(sno):
    # Check authentication
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        df = get_dataframe()
        
        # Find request
        if sno not in df['sno'].values:
            return jsonify({'error': 'Request not found'}), 404
        
        idx = df.index[df['sno'] == sno].tolist()[0]
        
        # Only allow updates to specific fields
        updatable_fields = ['updates', 'status']
        updates_made = False
        
        for field in updatable_fields:
            if field in data and isinstance(data[field], str) and data[field].strip():
                df.at[idx, field] = data[field].strip()
                updates_made = True
        
        if not updates_made:
            return jsonify({'error': 'No valid updates provided'}), 400
        
        # Add update timestamp if updates were modified
        if 'updates' in data:
            df.at[idx, 'updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        save_dataframe(df)
        
        return jsonify({
            'success': True,
            'message': 'Request updated successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    # Create Excel file if it doesn't exist
    if not os.path.exists(EXCEL_FILE):
        get_dataframe()
    app.run(debug=True)