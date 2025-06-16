class ExcelDatabase {
    constructor() {
        this.workbook = new ExcelJS.Workbook();
        this.worksheet = null;
        this.fileHandle = null;
        this.filePath = 'requests_database.xlsx';
        this.isConnected = false;
    }

    async connect() {
        try {
            this.showAlert('Connecting to Excel database...', 'info');
            
            // Try to get file handle
            this.fileHandle = await this.getFileHandle();
            const file = await this.fileHandle.getFile();
            
            if (file.size > 0) {
                // Load existing file
                const buffer = await file.arrayBuffer();
                await this.workbook.xlsx.load(buffer);
                this.showAlert('Existing Excel file loaded', 'success');
            } else {
                // Create new file
                this.initializeWorkbook();
                this.showAlert('New Excel file created', 'success');
            }
            
            this.worksheet = this.workbook.getWorksheet('Requests') || 
                           this.workbook.addWorksheet('Requests');
            
            if (this.worksheet.rowCount === 0) {
                this.initializeWorksheet();
                await this.save();
            }
            
            this.isConnected = true;
            return true;
        } catch (error) {
            console.error('Connection error:', error);
            this.showAlert('Failed to connect to Excel file', 'error');
            this.isConnected = false;
            return false;
        }
    }

    async getFileHandle() {
        try {
            if (!window.showSaveFilePicker) {
                throw new Error('File System Access API not available');
            }
            
            let fileHandle;
            
            try {
                [fileHandle] = await window.showOpenFilePicker({
                    types: [{
                        description: 'Excel Files',
                        accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
                    }],
                    multiple: false
                });
            } catch (error) {
                // If file doesn't exist, create it
                fileHandle = await window.showSaveFilePicker({
                    suggestedName: this.filePath,
                    types: [{
                        description: 'Excel Files',
                        accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
                    }]
                });
            }
            
            return fileHandle;
        } catch (error) {
            console.error('File handle error:', error);
            throw error;
        }
    }

    initializeWorkbook() {
        this.worksheet = this.workbook.addWorksheet('Requests');
        this.initializeWorksheet();
    }

    initializeWorksheet() {
        this.worksheet.columns = [
            { header: 'ID', key: 'id', width: 10 },
            { header: 'Type', key: 'type', width: 15 },
            { header: 'Requester', key: 'requester', width: 20 },
            { header: 'Description', key: 'description', width: 40 },
            { header: 'Date', key: 'date', width: 20 },
            { header: 'Status', key: 'status', width: 15 }
        ];
    }

    async addRecord(data) {
        if (!this.isConnected) {
            throw new Error('Not connected to database');
        }
        
        try {
            const newRow = {
                id: data.id,
                type: data.type,
                requester: data.requester,
                description: data.description,
                date: data.date,
                status: data.status || 'Open'
            };
            
            this.worksheet.addRow(newRow);
            await this.save();
            return newRow;
        } catch (error) {
            console.error('Error adding record:', error);
            throw error;
        }
    }

    async getAllRecords() {
        if (!this.isConnected) {
            throw new Error('Not connected to database');
        }
        
        const records = [];
        
        try {
            this.worksheet.eachRow({ includeEmpty: false }, (row, rowNumber) => {
                if (rowNumber === 1) return; // Skip header
                
                records.push({
                    id: row.getCell(1).value,
                    type: row.getCell(2).value,
                    requester: row.getCell(3).value,
                    description: row.getCell(4).value,
                    date: row.getCell(5).value,
                    status: row.getCell(6).value
                });
            });
            
            return records;
        } catch (error) {
            console.error('Error reading records:', error);
            throw error;
        }
    }

    async save() {
        if (!this.isConnected || !this.fileHandle) {
            throw new Error('Not connected to database');
        }
        
        try {
            const writable = await this.fileHandle.createWritable();
            const buffer = await this.workbook.xlsx.writeBuffer();
            await writable.write(buffer);
            await writable.close();
            console.log('Changes saved to Excel file');
        } catch (error) {
            console.error('Error saving file:', error);
            throw error;
        }
    }

    showAlert(message, type = 'info') {
        const alertBox = document.createElement('div');
        alertBox.className = `alert alert-${type}`;
        alertBox.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : 
                             type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;
        
        const container = document.getElementById('alert-container');
        container.appendChild(alertBox);
        
        setTimeout(() => {
            alertBox.classList.add('fade-out');
            setTimeout(() => alertBox.remove(), 500);
        }, 3000);
    }
}

class AppController {
    constructor() {
        this.db = new ExcelDatabase();
        this.initElements();
        this.setupEventListeners();
        this.updateUI();
    }

    initElements() {
        this.elements = {
            connectDbBtn: document.getElementById('connect-db'),
            newRequestBtn: document.getElementById('new-request'),
            requestForm: document.getElementById('request-form'),
            requestDataForm: document.getElementById('request-data-form'),
            cancelRequestBtn: document.getElementById('cancel-request'),
            requestsBody: document.getElementById('requests-body'),
            refreshDataBtn: document.getElementById('refresh-data'),
            dbStatus: document.getElementById('db-status'),
            dbPath: document.getElementById('db-path'),
            dbStatusIcon: document.getElementById('db-status-icon')
        };
    }

    setupEventListeners() {
        this.elements.connectDbBtn.addEventListener('click', () => this.connectDatabase());
        this.elements.newRequestBtn.addEventListener('click', () => this.toggleRequestForm());
        this.elements.cancelRequestBtn.addEventListener('click', () => this.toggleRequestForm());
        this.elements.requestDataForm.addEventListener('submit', (e) => this.handleRequestSubmit(e));
        this.elements.refreshDataBtn.addEventListener('click', () => this.loadRequests());
    }

    async connectDatabase() {
        try {
            this.setDbStatus('Connecting...', 'fa-circle-notch fa-spin');
            const success = await this.db.connect();
            
            if (success) {
                this.setDbStatus(`Connected to: ${this.db.filePath}`, 'fa-check-circle', 'connected');
                this.enableControls();
                await this.loadRequests();
            } else {
                this.setDbStatus('Connection failed', 'fa-times-circle', 'disconnected');
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.setDbStatus('Error connecting', 'fa-times-circle', 'disconnected');
        }
    }

    enableControls() {
        this.elements.newRequestBtn.disabled = false;
        this.elements.refreshDataBtn.disabled = false;
    }

    setDbStatus(text, iconClass, statusClass = '') {
        this.elements.dbPath.textContent = `Database: ${text}`;
        const icon = this.elements.dbStatusIcon.querySelector('i') || document.createElement('i');
        icon.className = `fas ${iconClass}`;
        this.elements.dbStatusIcon.innerHTML = '';
        this.elements.dbStatusIcon.appendChild(icon);
        this.elements.dbStatus.className = `db-status ${statusClass}`;
    }

    toggleRequestForm() {
        this.elements.requestForm.classList.toggle('hidden');
    }

    async handleRequestSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.elements.requestDataForm);
        const requestData = {
            id: Date.now(),
            type: formData.get('request-type'),
            requester: formData.get('requester'),
            description: formData.get('description'),
            date: new Date().toISOString()
        };
        
        try {
            await this.db.addRecord(requestData);
            this.elements.requestDataForm.reset();
            this.toggleRequestForm();
            await this.loadRequests();
            this.db.showAlert('Request submitted successfully!', 'success');
        } catch (error) {
            console.error('Submission error:', error);
            this.db.showAlert('Failed to submit request', 'error');
        }
    }

    async loadRequests() {
        try {
            const requests = await this.db.getAllRecords();
            this.renderRequests(requests);
            this.db.showAlert('Requests loaded successfully', 'success');
        } catch (error) {
            console.error('Load error:', error);
            this.db.showAlert('Failed to load requests', 'error');
        }
    }

    renderRequests(requests) {
        this.elements.requestsBody.innerHTML = '';
        
        if (requests.length === 0) {
            this.elements.requestsBody.innerHTML = `
                <tr>
                    <td colspan="6" class="no-data">No requests found</td>
                </tr>
            `;
            return;
        }
        
        requests.forEach(request => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${request.id}</td>
                <td>${request.type}</td>
                <td>${request.requester}</td>
                <td>${request.description}</td>
                <td>${new Date(request.date).toLocaleString()}</td>
                <td><span class="status status-${(request.status || 'Open').toLowerCase()}">${request.status || 'Open'}</span></td>
            `;
            this.elements.requestsBody.appendChild(row);
        });
    }

    updateUI() {
        this.setDbStatus('Not connected', 'fa-plug', 'disconnected');
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    const app = new AppController();
});