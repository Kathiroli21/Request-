// Travel Claim Automation System - Final Implementation
// Corrected for per-travel advance and exact Excel format replication

// Global Variables
let currentUser = null;
let travelEntries = [];
let currentTravelData = null;
let editingTravelIndex = -1;
let editingHotelIndex = -1;
let editingConveyanceIndex = -1;

// Employee Database
const employeeDatabase = {
    'EMP001': {
        persNo: 'EMP001',
        employeeName: 'Kathiroli B',
        grade: 'SME',
        position: 'Manager',
        department: 'IA'
    },
    'EMP002': {
        persNo: 'EMP002',
        employeeName: 'Rajesh Kumar',
        grade: 'SE',
        position: 'Senior Engineer',
        department: 'IT'
    },
    'EMP003': {
        persNo: 'EMP003',
        employeeName: 'Priya Sharma',
        grade: 'MGR',
        position: 'Project Manager',
        department: 'Operations'
    }
};

// City Classifications
const cityClassifications = {
    // Class A Cities
    'Mumbai': 'A', 'Delhi': 'A', 'Bangalore': 'A', 'Chennai': 'A', 'Hyderabad': 'A', 
    'Pune': 'A', 'Kolkata': 'A', 'Ahmedabad': 'A', 'Surat': 'A', 'Jaipur': 'A',
    
    // Class B Cities
    'Coimbatore': 'B', 'Madurai': 'B', 'Trichy': 'B', 'Salem': 'B', 'Erode': 'B',
    'Tirupur': 'B', 'Vellore': 'B', 'Thanjavur': 'B', 'Dindigul': 'B', 'Karur': 'B',
    'Nagpur': 'B', 'Indore': 'B', 'Bhopal': 'B', 'Visakhapatnam': 'B', 'Vijayawada': 'B',
    'Guntur': 'B', 'Nellore': 'B', 'Kurnool': 'B', 'Rajahmundry': 'B', 'Tirupati': 'B'
};

// Grade-based Allowance Rules (per day)
const allowanceRules = {
    'SME': { 'A': 1200, 'B': 1000 },
    'SE': { 'A': 1500, 'B': 1200 },
    'MGR': { 'A': 2000, 'B': 1500 },
    'DGM': { 'A': 2500, 'B': 2000 },
    'GM': { 'A': 3000, 'B': 2500 }
};

// Utility Functions
function generateId() {
    return 'id_' + Math.random().toString(36).substr(2, 9);
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB');
}

function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '₹0.00';
    return '₹' + parseFloat(amount).toFixed(2);
}

function calculateDays(fromDate, toDate) {
    if (!fromDate || !toDate) return 0;
    const from = new Date(fromDate);
    const to = new Date(toDate);
    const diffTime = Math.abs(to - from);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // Include both start and end dates
    return diffDays;
}

function getCityClass(cityName) {
    return cityClassifications[cityName] || 'B'; // Default to Class B if not found
}

function getAllowanceRate(grade, cityClass) {
    return allowanceRules[grade] ? allowanceRules[grade][cityClass] || 1000 : 1000;
}

// Screen Management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

// Modal Management
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function hideModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showModalTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.modal-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.modal-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabId).classList.add('active');
    
    // Add active class to corresponding button
    const tabButtons = document.querySelectorAll('.modal-tab-btn');
    if (tabId === 'basic-details' || tabId === 'tebill-preview') {
        tabButtons[0].classList.add('active');
    } else if (tabId === 'hotel-expenses' || tabId === 'hotel-preview') {
        tabButtons[1].classList.add('active');
    } else if (tabId === 'local-conveyance' || tabId === 'conveyance-preview') {
        tabButtons[2].classList.add('active');
    }
}

// Login Management
function login(event) {
    event.preventDefault();
    
    const persNo = document.getElementById('persNo').value.trim();
    const errorDiv = document.getElementById('loginError');
    
    if (!persNo) {
        showError(errorDiv, 'Please enter your personnel number');
        return;
    }
    
    const employee = employeeDatabase[persNo];
    if (!employee) {
        showError(errorDiv, 'Invalid personnel number. Please try EMP001, EMP002, or EMP003');
        return;
    }
    
    currentUser = employee;
    loadDashboard();
    showScreen('dashboardScreen');
}

function logout() {
    currentUser = null;
    travelEntries = [];
    document.getElementById('persNo').value = '';
    document.getElementById('loginError').style.display = 'none';
    showScreen('loginScreen');
}

function showError(errorDiv, message) {
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function loadDashboard() {
    if (!currentUser) return;
    
    // Populate employee information
    document.getElementById('employeeName').textContent = `${currentUser.employeeName} / ${currentUser.persNo}`;
    document.getElementById('employeeGrade').textContent = currentUser.grade;
    document.getElementById('employeePosition').textContent = currentUser.position;
    document.getElementById('employeeDepartment').textContent = currentUser.department;
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-GB');
    
    // Load saved data
    loadSavedData();
    refreshTravelTable();
    updateExpenseSummary();
}

function loadSavedData() {
    const savedData = localStorage.getItem(`travelClaim_${currentUser.persNo}`);
    if (savedData) {
        const data = JSON.parse(savedData);
        travelEntries = data.travelEntries || [];
        document.getElementById('purposeOfVisit').value = data.purposeOfVisit || '';
    }
}

function saveData() {
    if (!currentUser) return;
    
    const data = {
        travelEntries: travelEntries,
        purposeOfVisit: document.getElementById('purposeOfVisit').value
    };
    
    localStorage.setItem(`travelClaim_${currentUser.persNo}`, JSON.stringify(data));
}

// Travel Entry Management
function addTravelEntry() {
    editingTravelIndex = -1;
    currentTravelData = {
        id: generateId(),
        dateFrom: '',
        dateTo: '',
        fromLocation: '',
        toLocation: '',
        modeClass: '',
        fare: 0,
        advance: 0, // Per-travel advance
        miscExpenses: 0,
        businessDisc: 0,
        touristTaxi: false,
        companyCar: false,
        hotelExpenses: [],
        localConveyance: []
    };
    
    clearTravelForm();
    document.getElementById('travelModalTitle').textContent = 'Add Travel Entry';
    showModal('travelModal');
    showModalTab('basic-details');
    updateCalculatedTotals();
}

function editTravelEntry(index) {
    editingTravelIndex = index;
    currentTravelData = JSON.parse(JSON.stringify(travelEntries[index])); // Deep copy
    
    populateTravelForm(currentTravelData);
    document.getElementById('travelModalTitle').textContent = 'Edit Travel Entry';
    showModal('travelModal');
    showModalTab('basic-details');
    updateNestedTables();
    updateCalculatedTotals();
}

function deleteTravelEntry(index) {
    if (confirm('Are you sure you want to delete this travel entry?')) {
        travelEntries.splice(index, 1);
        refreshTravelTable();
        updateExpenseSummary();
        saveData();
    }
}

function clearTravelForm() {
    document.getElementById('travelForm').reset();
    document.getElementById('nestedHotelTableBody').innerHTML = '';
    document.getElementById('nestedConveyanceTableBody').innerHTML = '';
}

function populateTravelForm(travelData) {
    document.getElementById('dateFrom').value = travelData.dateFrom;
    document.getElementById('dateTo').value = travelData.dateTo;
    document.getElementById('fromLocation').value = travelData.fromLocation;
    document.getElementById('toLocation').value = travelData.toLocation;
    document.getElementById('modeClass').value = travelData.modeClass;
    document.getElementById('fare').value = travelData.fare;
    document.getElementById('travelAdvance').value = travelData.advance; // Per-travel advance
    document.getElementById('miscExpenses').value = travelData.miscExpenses;
    document.getElementById('businessDisc').value = travelData.businessDisc;
    document.getElementById('touristTaxi').checked = travelData.touristTaxi;
    document.getElementById('companyCar').checked = travelData.companyCar;
}

function saveTravelEntry() {
    if (!validateTravelForm()) return;
    
    // Update current travel data with form values
    currentTravelData.dateFrom = document.getElementById('dateFrom').value;
    currentTravelData.dateTo = document.getElementById('dateTo').value;
    currentTravelData.fromLocation = document.getElementById('fromLocation').value;
    currentTravelData.toLocation = document.getElementById('toLocation').value;
    currentTravelData.modeClass = document.getElementById('modeClass').value;
    currentTravelData.fare = parseFloat(document.getElementById('fare').value) || 0;
    currentTravelData.advance = parseFloat(document.getElementById('travelAdvance').value) || 0; // Per-travel advance
    currentTravelData.miscExpenses = parseFloat(document.getElementById('miscExpenses').value) || 0;
    currentTravelData.businessDisc = parseFloat(document.getElementById('businessDisc').value) || 0;
    currentTravelData.touristTaxi = document.getElementById('touristTaxi').checked;
    currentTravelData.companyCar = document.getElementById('companyCar').checked;
    
    if (editingTravelIndex >= 0) {
        travelEntries[editingTravelIndex] = currentTravelData;
    } else {
        travelEntries.push(currentTravelData);
    }
    
    refreshTravelTable();
    updateExpenseSummary();
    saveData();
    hideModal('travelModal');
}

function validateTravelForm() {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    const fromLocation = document.getElementById('fromLocation').value;
    const toLocation = document.getElementById('toLocation').value;
    const modeClass = document.getElementById('modeClass').value;
    
    if (!dateFrom || !dateTo || !fromLocation || !toLocation || !modeClass) {
        alert('Please fill in all required fields');
        return false;
    }
    
    if (new Date(dateTo) < new Date(dateFrom)) {
        alert('To date cannot be earlier than From date');
        return false;
    }
    
    return true;
}

// Hotel Eligibility Calculation
function calculateHotelEligibility(expense, grade, location) {
    if (!expense || !grade) return {
        days: 0, dailyAllowance: 0, totalRoomRent: 0, totalTax: 0,
        totalExpense: 0, eligibility: 0, finalClaimable: 0, cityClass: 'B',
        eligibilityText: ''
    };
    
    const days = calculateDays(expense.dateFrom, expense.dateTo);
    const cityClass = getCityClass(location || expense.particulars);
    const dailyAllowance = getAllowanceRate(grade, cityClass);
    
    const totalRoomRent = (expense.roomRentPerDay || 0) * days;
    const totalTax = (expense.taxPerDay || 0) * days;
    const totalExpense = totalRoomRent + totalTax;
    
    // Eligibility = (Daily Allowance × Days) + Total Tax Amount
    const eligibility = (dailyAllowance * days) + totalTax;
    
    // Final claimable = Min(Total Expense, Eligibility) - Company Paid Total
    const finalClaimable = Math.max(0, Math.min(totalExpense, eligibility) - (expense.companyPaidTotal || 0));
    
    const eligibilityText = `Sust Rs.${dailyAllowance}x ${days} day= Rs.${(dailyAllowance * days).toFixed(2)} + Total Tax Amount Rs.${totalTax.toFixed(2)}`;
    
    return {
        days,
        dailyAllowance,
        totalRoomRent,
        totalTax,
        totalExpense,
        eligibility,
        finalClaimable,
        cityClass,
        eligibilityText
    };
}

function calculateHotelTotal(hotelExpenses) {
    if (!hotelExpenses || hotelExpenses.length === 0) return 0;
    
    return hotelExpenses.reduce((total, expense) => {
        const calc = calculateHotelEligibility(expense, currentUser.grade, currentTravelData?.toLocation);
        return total + calc.finalClaimable;
    }, 0);
}

function calculateConveyanceTotal(conveyanceEntries) {
    if (!conveyanceEntries || conveyanceEntries.length === 0) return 0;
    
    return conveyanceEntries.reduce((total, entry) => total + (entry.amount || 0), 0);
}

function updateCalculatedTotals() {
    if (!currentTravelData) return;
    
    const hotelTotal = calculateHotelTotal(currentTravelData.hotelExpenses);
    const conveyanceTotal = calculateConveyanceTotal(currentTravelData.localConveyance);
    const advance = parseFloat(document.getElementById('travelAdvance').value) || 0;
    const fare = parseFloat(document.getElementById('fare').value) || 0;
    const miscExpenses = parseFloat(document.getElementById('miscExpenses').value) || 0;
    const businessDisc = parseFloat(document.getElementById('businessDisc').value) || 0;
    
    const grossTotal = fare + hotelTotal + miscExpenses + conveyanceTotal - businessDisc;
    const netClaim = Math.max(0, grossTotal - advance);
    
    document.getElementById('calculatedHotelTotal').textContent = formatCurrency(hotelTotal);
    document.getElementById('calculatedConveyanceTotal').textContent = formatCurrency(conveyanceTotal);
    document.getElementById('calculatedAdvance').textContent = formatCurrency(advance);
    document.getElementById('calculatedNetClaim').textContent = formatCurrency(netClaim);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', login);
    
    // Travel form inputs for real-time calculation
    ['fare', 'travelAdvance', 'miscExpenses', 'businessDisc'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateCalculatedTotals);
    });
    
    // Purpose of visit auto-save
    document.getElementById('purposeOfVisit').addEventListener('input', saveData);
    
    console.log('Travel Claim System initialized');
});


// Travel Table Management and TEBILL Sheet Implementation
function refreshTravelTable() {
    const tbody = document.getElementById('tebillTableBody');
    tbody.innerHTML = '';
    
    travelEntries.forEach((travel, index) => {
        const row = document.createElement('tr');
        
        const hotelTotal = calculateHotelTotal(travel.hotelExpenses);
        const conveyanceTotal = calculateConveyanceTotal(travel.localConveyance);
        const totalAmount = (travel.fare || 0) + hotelTotal + (travel.miscExpenses || 0) + conveyanceTotal - (travel.businessDisc || 0);
        
        row.innerHTML = `
            <td>
                <input type="checkbox" class="travel-select" data-index="${index}">
            </td>
            <td>${formatDate(travel.dateFrom)} to ${formatDate(travel.dateTo)}</td>
            <td>${travel.fromLocation}</td>
            <td>${travel.toLocation}</td>
            <td>${travel.modeClass}</td>
            <td>${formatCurrency(travel.fare)}</td>
            <td>${formatCurrency(hotelTotal)}</td>
            <td>${formatCurrency(travel.businessDisc)}</td>
            <td>${formatCurrency(travel.miscExpenses)}</td>
            <td>${formatCurrency(conveyanceTotal)}</td>
            <td>${formatCurrency(travel.advance)}</td>
            <td>${travel.touristTaxi ? '✓' : ''}</td>
            <td>${travel.companyCar ? '✓' : ''}</td>
            <td>${formatCurrency(totalAmount)}</td>
            <td>
                <button class="btn-edit" onclick="editTravelEntry(${index})">Edit</button>
                <button class="btn-delete" onclick="deleteTravelEntry(${index})">Delete</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateExpenseSummary() {
    let totalFare = 0;
    let totalHotel = 0;
    let totalConveyance = 0;
    let totalMisc = 0;
    let totalBusinessDisc = 0;
    let totalAdvance = 0;
    
    travelEntries.forEach(travel => {
        totalFare += travel.fare || 0;
        totalHotel += calculateHotelTotal(travel.hotelExpenses);
        totalConveyance += calculateConveyanceTotal(travel.localConveyance);
        totalMisc += travel.miscExpenses || 0;
        totalBusinessDisc += travel.businessDisc || 0;
        totalAdvance += travel.advance || 0; // Per-travel advance
    });
    
    const grossTotal = totalFare + totalHotel + totalMisc + totalConveyance - totalBusinessDisc;
    const netClaimable = Math.max(0, grossTotal - totalAdvance);
    
    document.getElementById('totalFare').textContent = formatCurrency(totalFare);
    document.getElementById('totalHotel').textContent = formatCurrency(totalHotel);
    document.getElementById('totalConveyance').textContent = formatCurrency(totalConveyance);
    document.getElementById('totalMisc').textContent = formatCurrency(totalMisc);
    document.getElementById('totalBusinessDisc').textContent = formatCurrency(totalBusinessDisc);
    document.getElementById('totalAdvance').textContent = formatCurrency(totalAdvance);
    document.getElementById('netClaimable').textContent = formatCurrency(netClaimable);
}

// Hotel Expense Management
function addHotelExpense() {
    editingHotelIndex = -1;
    clearHotelSubForm();
    document.getElementById('hotelSubModalTitle').textContent = 'Add Hotel Expense';
    showModal('hotelSubModal');
    updateHotelEligibilityPreview();
}

function editHotelExpense(index) {
    editingHotelIndex = index;
    const expense = currentTravelData.hotelExpenses[index];
    populateHotelSubForm(expense);
    document.getElementById('hotelSubModalTitle').textContent = 'Edit Hotel Expense';
    showModal('hotelSubModal');
    updateHotelEligibilityPreview();
}

function deleteHotelExpense(index) {
    if (confirm('Are you sure you want to delete this hotel expense?')) {
        currentTravelData.hotelExpenses.splice(index, 1);
        updateNestedTables();
        updateCalculatedTotals();
    }
}

function clearHotelSubForm() {
    document.getElementById('hotelSubForm').reset();
}

function populateHotelSubForm(expense) {
    document.getElementById('hotelDateFrom').value = expense.dateFrom;
    document.getElementById('hotelDateTo').value = expense.dateTo;
    document.getElementById('hotelParticulars').value = expense.particulars;
    document.getElementById('roomRentPerDay').value = expense.roomRentPerDay;
    document.getElementById('taxPerDay').value = expense.taxPerDay;
    document.getElementById('companyPaidHotel').value = expense.companyPaidTotal || 0;
}

function saveHotelExpense(event) {
    event.preventDefault();
    
    if (!validateHotelSubForm()) return;
    
    const expense = {
        id: editingHotelIndex >= 0 ? currentTravelData.hotelExpenses[editingHotelIndex].id : generateId(),
        dateFrom: document.getElementById('hotelDateFrom').value,
        dateTo: document.getElementById('hotelDateTo').value,
        particulars: document.getElementById('hotelParticulars').value,
        roomRentPerDay: parseFloat(document.getElementById('roomRentPerDay').value) || 0,
        taxPerDay: parseFloat(document.getElementById('taxPerDay').value) || 0,
        companyPaidTotal: parseFloat(document.getElementById('companyPaidHotel').value) || 0 // Overall amount
    };
    
    if (editingHotelIndex >= 0) {
        currentTravelData.hotelExpenses[editingHotelIndex] = expense;
    } else {
        currentTravelData.hotelExpenses.push(expense);
    }
    
    updateNestedTables();
    updateCalculatedTotals();
    hideModal('hotelSubModal');
}

function validateHotelSubForm() {
    const dateFrom = document.getElementById('hotelDateFrom').value;
    const dateTo = document.getElementById('hotelDateTo').value;
    const particulars = document.getElementById('hotelParticulars').value;
    const roomRent = document.getElementById('roomRentPerDay').value;
    const tax = document.getElementById('taxPerDay').value;
    
    if (!dateFrom || !dateTo || !particulars || !roomRent || !tax) {
        alert('Please fill in all required fields');
        return false;
    }
    
    if (new Date(dateTo) < new Date(dateFrom)) {
        alert('To date cannot be earlier than From date');
        return false;
    }
    
    return true;
}

function updateHotelEligibilityPreview() {
    const dateFrom = document.getElementById('hotelDateFrom').value;
    const dateTo = document.getElementById('hotelDateTo').value;
    const roomRentPerDay = parseFloat(document.getElementById('roomRentPerDay').value) || 0;
    const taxPerDay = parseFloat(document.getElementById('taxPerDay').value) || 0;
    const companyPaid = parseFloat(document.getElementById('companyPaidHotel').value) || 0;
    
    const expense = {
        dateFrom, dateTo, roomRentPerDay, taxPerDay, companyPaidTotal: companyPaid
    };
    
    const calc = calculateHotelEligibility(expense, currentUser?.grade, currentTravelData?.toLocation);
    
    document.getElementById('daysStayed').textContent = `${calc.days} days`;
    document.getElementById('dailyAllowanceRate').textContent = `₹${calc.dailyAllowance}/day (Class ${calc.cityClass})`;
    document.getElementById('totalRoomRent').textContent = formatCurrency(calc.totalRoomRent);
    document.getElementById('totalTax').textContent = formatCurrency(calc.totalTax);
    document.getElementById('totalExpense').textContent = formatCurrency(calc.totalExpense);
    document.getElementById('eligibilityAmount').textContent = formatCurrency(calc.eligibility);
    document.getElementById('finalClaimable').textContent = formatCurrency(calc.finalClaimable);
}

// Local Conveyance Management
function addConveyanceEntry() {
    editingConveyanceIndex = -1;
    clearConveyanceSubForm();
    document.getElementById('conveyanceSubModalTitle').textContent = 'Add Conveyance Entry';
    showModal('conveyanceSubModal');
}

function editConveyanceEntry(index) {
    editingConveyanceIndex = index;
    const entry = currentTravelData.localConveyance[index];
    populateConveyanceSubForm(entry);
    document.getElementById('conveyanceSubModalTitle').textContent = 'Edit Conveyance Entry';
    showModal('conveyanceSubModal');
}

function deleteConveyanceEntry(index) {
    if (confirm('Are you sure you want to delete this conveyance entry?')) {
        currentTravelData.localConveyance.splice(index, 1);
        updateNestedTables();
        updateCalculatedTotals();
    }
}

function clearConveyanceSubForm() {
    document.getElementById('conveyanceSubForm').reset();
}

function populateConveyanceSubForm(entry) {
    document.getElementById('conveyanceDate').value = entry.date;
    document.getElementById('conveyanceFrom').value = entry.from;
    document.getElementById('conveyanceTo').value = entry.to;
    document.getElementById('modeOfTravel').value = entry.modeOfTravel;
    document.getElementById('conveyanceAmount').value = entry.amount;
}

function saveConveyanceEntry(event) {
    event.preventDefault();
    
    if (!validateConveyanceSubForm()) return;
    
    const entry = {
        id: editingConveyanceIndex >= 0 ? currentTravelData.localConveyance[editingConveyanceIndex].id : generateId(),
        date: document.getElementById('conveyanceDate').value,
        from: document.getElementById('conveyanceFrom').value,
        to: document.getElementById('conveyanceTo').value,
        modeOfTravel: document.getElementById('modeOfTravel').value,
        amount: parseFloat(document.getElementById('conveyanceAmount').value) || 0
    };
    
    if (editingConveyanceIndex >= 0) {
        currentTravelData.localConveyance[editingConveyanceIndex] = entry;
    } else {
        currentTravelData.localConveyance.push(entry);
    }
    
    updateNestedTables();
    updateCalculatedTotals();
    hideModal('conveyanceSubModal');
}

function validateConveyanceSubForm() {
    const date = document.getElementById('conveyanceDate').value;
    const from = document.getElementById('conveyanceFrom').value;
    const to = document.getElementById('conveyanceTo').value;
    const mode = document.getElementById('modeOfTravel').value;
    const amount = document.getElementById('conveyanceAmount').value;
    
    if (!date || !from || !to || !mode || !amount) {
        alert('Please fill in all required fields');
        return false;
    }
    
    return true;
}

function updateNestedTables() {
    updateNestedHotelTable();
    updateNestedConveyanceTable();
}

function updateNestedHotelTable() {
    const tbody = document.getElementById('nestedHotelTableBody');
    tbody.innerHTML = '';
    
    if (!currentTravelData.hotelExpenses) return;
    
    currentTravelData.hotelExpenses.forEach((expense, index) => {
        const calc = calculateHotelEligibility(expense, currentUser.grade, currentTravelData.toLocation);
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${formatDate(expense.dateFrom)} to ${formatDate(expense.dateTo)}</td>
            <td>${expense.particulars}</td>
            <td>${formatCurrency(calc.totalRoomRent)}</td>
            <td>${formatCurrency(calc.totalTax)}</td>
            <td>${formatCurrency(calc.totalExpense)}</td>
            <td>${calc.eligibilityText}</td>
            <td>${formatCurrency(expense.companyPaidTotal)}</td>
            <td>${formatCurrency(calc.finalClaimable)}</td>
            <td>
                <button class="btn-edit" onclick="editHotelExpense(${index})">Edit</button>
                <button class="btn-delete" onclick="deleteHotelExpense(${index})">Delete</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateNestedConveyanceTable() {
    const tbody = document.getElementById('nestedConveyanceTableBody');
    tbody.innerHTML = '';
    
    if (!currentTravelData.localConveyance) return;
    
    currentTravelData.localConveyance.forEach((entry, index) => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${formatDate(entry.date)}</td>
            <td>${entry.from}</td>
            <td>${entry.to}</td>
            <td>${entry.modeOfTravel}</td>
            <td>${formatCurrency(entry.amount)}</td>
            <td>
                <button class="btn-edit" onclick="editConveyanceEntry(${index})">Edit</button>
                <button class="btn-delete" onclick="deleteConveyanceEntry(${index})">Delete</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Additional Event Listeners for Hotel and Conveyance Sub-forms
document.addEventListener('DOMContentLoaded', function() {
    // Hotel sub-form
    document.getElementById('hotelSubForm').addEventListener('submit', saveHotelExpense);
    document.getElementById('cancelHotelBtn').addEventListener('click', () => hideModal('hotelSubModal'));
    
    // Conveyance sub-form
    document.getElementById('conveyanceSubForm').addEventListener('submit', saveConveyanceEntry);
    document.getElementById('cancelConveyanceBtn').addEventListener('click', () => hideModal('conveyanceSubModal'));
    
    // Hotel eligibility preview updates
    ['hotelDateFrom', 'hotelDateTo', 'roomRentPerDay', 'taxPerDay', 'companyPaidHotel'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateHotelEligibilityPreview);
    });
    
    // All sheets modal
    document.getElementById('closeAllSheetsBtn').addEventListener('click', () => hideModal('allSheetsModal'));
    document.getElementById('printAllSheetsBtn').addEventListener('click', printAllSheets);
});


// SheetJS Export and Print Functionality - Exact Excel Format Replication
function exportToExcel() {
    if (travelEntries.length === 0) {
        alert('No travel entries to export');
        return;
    }
    
    const workbook = XLSX.utils.book_new();
    
    // Create TEBILL Sheet
    const tebillSheet = createTEBILLSheet();
    XLSX.utils.book_append_sheet(workbook, tebillSheet, 'TEBILL');
    
    // Create Hotel Expenses Sheet
    const hotelSheet = createHotelExpensesSheet();
    XLSX.utils.book_append_sheet(workbook, hotelSheet, 'Hotel Expenses');
    
    // Create Local Conveyance Sheet
    const conveyanceSheet = createLocalConveyanceSheet();
    XLSX.utils.book_append_sheet(workbook, conveyanceSheet, 'Local Conveyance');
    
    // Export file
    const fileName = `TravelClaim_${currentUser.persNo}_${new Date().toISOString().split('T')[0]}.xlsx`;
    XLSX.writeFile(workbook, fileName);
}

function createTEBILLSheet() {
    const ws = {};
    
    // Set column widths
    ws['!cols'] = [
        {wch: 3}, {wch: 12}, {wch: 10}, {wch: 10}, {wch: 8}, {wch: 8}, 
        {wch: 8}, {wch: 8}, {wch: 12}, {wch: 10}, {wch: 8}, {wch: 8}, 
        {wch: 8}, {wch: 8}, {wch: 8}, {wch: 8}, {wch: 8}, {wch: 8}, {wch: 8}
    ];
    
    // Header Section (Rows 1-12)
    ws['B3'] = { v: 'XYZ', t: 's' };
    ws['N3'] = { v: 'TRAVEL EXPENSE STATEMENT', t: 's' };
    
    ws['B4'] = { v: 'NAME / EMP No.:', t: 's' };
    ws['F4'] = { v: 'GRADE', t: 's' };
    ws['H4'] = { v: 'DESIGNATION', t: 's' };
    ws['M4'] = { v: 'DEPARTMENT', t: 's' };
    ws['Q4'] = { v: 'DATE', t: 's' };
    
    ws['B5'] = { v: `${currentUser.employeeName} / ${currentUser.persNo}`, t: 's' };
    ws['F5'] = { v: currentUser.grade, t: 's' };
    ws['H5'] = { v: currentUser.position, t: 's' };
    ws['M5'] = { v: currentUser.department, t: 's' };
    ws['Q5'] = { v: new Date().toLocaleDateString('en-GB'), t: 's' };
    
    ws['B6'] = { v: 'PLACE & PURPOSE OF VISIT :', t: 's' };
    ws['B7'] = { v: document.getElementById('purposeOfVisit').value || '', t: 's' };
    
    ws['P6'] = { v: '10', t: 's' };
    ws['R6'] = { v: '11', t: 's' };
    ws['P7'] = { v: 'Indicate whether Tourist Taxi on Credit or Company Car used or not', t: 's' };
    ws['R7'] = { v: 'Total', t: 's' };
    
    // Column Headers (Rows 8-12)
    ws['B8'] = { v: '1', t: 's' };
    ws['C8'] = { v: '2', t: 's' };
    ws['D8'] = { v: '3', t: 's' };
    ws['E8'] = { v: '4', t: 's' };
    ws['F8'] = { v: '5', t: 's' };
    ws['H8'] = { v: '6', t: 's' };
    ws['J8'] = { v: '7', t: 's' };
    ws['L8'] = { v: '8', t: 's' };
    ws['N8'] = { v: '9', t: 's' };
    
    ws['B9'] = { v: 'DATE', t: 's' };
    ws['C9'] = { v: 'FROM', t: 's' };
    ws['D9'] = { v: 'TO', t: 's' };
    ws['E9'] = { v: 'MODE/', t: 's' };
    ws['F9'] = { v: 'FARE', t: 's' };
    ws['H9'] = { v: 'HOTEL BILLS/', t: 's' };
    ws['J9'] = { v: 'BUSINESS', t: 's' };
    ws['L9'] = { v: 'MISCELLANEOUS /', t: 's' };
    ws['N9'] = { v: 'CONVEYANCE', t: 's' };
    
    ws['E10'] = { v: 'CLASS', t: 's' };
    ws['H10'] = { v: 'SUST.EXP', t: 's' };
    ws['J10'] = { v: 'DISC', t: 's' };
    ws['L10'] = { v: 'OUT OF POCKET', t: 's' };
    ws['N10'] = { v: 'EXPENSES', t: 's' };
    
    ws['L11'] = { v: 'EXPENSES', t: 's' };
    
    ws['F12'] = { v: 'Rs.', t: 's' };
    ws['G12'] = { v: 'P.', t: 's' };
    ws['H12'] = { v: 'Rs.', t: 's' };
    ws['I12'] = { v: 'P.', t: 's' };
    ws['J12'] = { v: 'Rs.', t: 's' };
    ws['K12'] = { v: 'P.', t: 's' };
    ws['L12'] = { v: 'Rs.', t: 's' };
    ws['M12'] = { v: 'P.', t: 's' };
    ws['N12'] = { v: 'Rs.', t: 's' };
    ws['O12'] = { v: 'P.', t: 's' };
    ws['R12'] = { v: 'Rs.', t: 's' };
    ws['S12'] = { v: 'P.', t: 's' };
    
    // Part A Header
    ws['B13'] = { v: 'PART - A - TO BE FILLED IN BY INDIVIDUAL', t: 's' };
    
    // Travel Entries Data (Starting from Row 14)
    let currentRow = 14;
    let totalFare = 0, totalHotel = 0, totalBusinessDisc = 0, totalMisc = 0, totalConveyance = 0, totalAdvance = 0;
    
    travelEntries.forEach((travel, index) => {
        const hotelTotal = calculateHotelTotal(travel.hotelExpenses);
        const conveyanceTotal = calculateConveyanceTotal(travel.localConveyance);
        const rowTotal = (travel.fare || 0) + hotelTotal + (travel.miscExpenses || 0) + conveyanceTotal - (travel.businessDisc || 0);
        
        ws[`B${currentRow}`] = { v: `${formatDate(travel.dateFrom)} to ${formatDate(travel.dateTo)}`, t: 's' };
        ws[`C${currentRow}`] = { v: travel.fromLocation, t: 's' };
        ws[`D${currentRow}`] = { v: travel.toLocation, t: 's' };
        ws[`E${currentRow}`] = { v: travel.modeClass, t: 's' };
        ws[`F${currentRow}`] = { v: travel.fare || 0, t: 'n' };
        ws[`H${currentRow}`] = { v: hotelTotal, t: 'n' };
        ws[`J${currentRow}`] = { v: travel.businessDisc || 0, t: 'n' };
        ws[`L${currentRow}`] = { v: travel.miscExpenses || 0, t: 'n' };
        ws[`N${currentRow}`] = { v: conveyanceTotal, t: 'n' };
        ws[`R${currentRow}`] = { v: rowTotal, t: 'n' };
        
        totalFare += travel.fare || 0;
        totalHotel += hotelTotal;
        totalBusinessDisc += travel.businessDisc || 0;
        totalMisc += travel.miscExpenses || 0;
        totalConveyance += conveyanceTotal;
        totalAdvance += travel.advance || 0;
        
        currentRow++;
    });
    
    // Add empty rows up to row 23
    while (currentRow < 24) {
        ws[`R${currentRow}`] = { v: 0, t: 'n' };
        currentRow++;
    }
    
    // Totals Row (Row 24)
    ws['F24'] = { v: totalFare, t: 'n' };
    ws['H24'] = { v: totalHotel, t: 'n' };
    ws['J24'] = { v: totalBusinessDisc, t: 'n' };
    ws['L24'] = { v: totalMisc, t: 'n' };
    ws['N24'] = { v: totalConveyance, t: 'n' };
    ws['R24'] = { v: totalFare + totalHotel + totalMisc + totalConveyance - totalBusinessDisc, t: 'n' };
    
    // Bottom Section
    ws['B26'] = { v: 'Accounts/Branches', t: 's' };
    ws['B27'] = { v: 'HOTEL BILLS ON CREDIT', t: 's' };
    ws['B28'] = { v: 'Paid by Plant / Sales Office.', t: 's' };
    
    ws['B30'] = { v: 'SIGNATURE', t: 's' };
    
    ws['J30'] = { v: 'TO BE FILLED IN BY INDIVIDUAL', t: 's' };
    ws['J31'] = { v: 'A. TOTAL EXPENSES - A - COL.11', t: 's' };
    ws['J33'] = { v: 'B. ADVANCE-', t: 's' };
    ws['J35'] = { v: 'C. FARE (AS PER COL. 5)', t: 's' };
    ws['J37'] = { v: 'D. NET PAYABLE TO CO/SELF (A-(B+C))', t: 's' };
    
    ws['O31'] = { v: totalFare + totalHotel + totalMisc + totalConveyance - totalBusinessDisc, t: 'n' };
    ws['O33'] = { v: totalAdvance, t: 'n' };
    ws['O35'] = { v: totalFare, t: 'n' };
    ws['O37'] = { v: Math.max(0, (totalFare + totalHotel + totalMisc + totalConveyance - totalBusinessDisc) - totalAdvance - totalFare), t: 'n' };
    
    ws['B32'] = { v: 'AUTHORISED BY', t: 's' };
    ws['B33'] = { v: 'LESS ALLOWED AS PER RULE 6 DD', t: 's' };
    ws['B35'] = { v: 'NO. OF DAYS X', t: 's' };
    ws['B36'] = { v: 'DISALLOWED HOTEL I A/c No.6331', t: 's' };
    
    // Set range
    const range = XLSX.utils.encode_range({ s: { c: 0, r: 0 }, e: { c: 18, r: 40 } });
    ws['!ref'] = range;
    
    return ws;
}

function createHotelExpensesSheet() {
    const ws = {};
    
    // Set column widths
    ws['!cols'] = [
        {wch: 3}, {wch: 15}, {wch: 12}, {wch: 10}, {wch: 10}, {wch: 25}, {wch: 15}, {wch: 15}, {wch: 15}
    ];
    
    // Header
    ws['B4'] = { v: `Food & Lodging Expenses of ${currentUser.employeeName} (E.No.${currentUser.persNo}) in ${getLocationsList()}.`, t: 's' };
    
    // Column Headers
    ws['B6'] = { v: 'Date', t: 's' };
    ws['C6'] = { v: 'Particulars', t: 's' };
    ws['D6'] = { v: 'Room Rent (Rs.)', t: 's' };
    ws['E6'] = { v: 'Tax (Rs.)', t: 's' };
    ws['F6'] = { v: 'Total (Rs.)', t: 's' };
    ws['G6'] = { v: 'Eligibility', t: 's' };
    ws['H6'] = { v: 'Amount Paid by Company', t: 's' };
    ws['I6'] = { v: 'Balance Amount Claimed Rs.', t: 's' };
    
    // Data Rows
    let currentRow = 7;
    let totalRoomRent = 0, totalTax = 0, totalAmount = 0, totalClaimable = 0;
    
    travelEntries.forEach(travel => {
        if (travel.hotelExpenses && travel.hotelExpenses.length > 0) {
            travel.hotelExpenses.forEach(expense => {
                const calc = calculateHotelEligibility(expense, currentUser.grade, travel.toLocation);
                
                ws[`B${currentRow}`] = { v: `${formatDate(expense.dateFrom)} to ${formatDate(expense.dateTo)}`, t: 's' };
                ws[`C${currentRow}`] = { v: expense.particulars, t: 's' };
                ws[`D${currentRow}`] = { v: calc.totalRoomRent, t: 'n' };
                ws[`E${currentRow}`] = { v: calc.totalTax, t: 'n' };
                ws[`F${currentRow}`] = { v: calc.totalExpense, t: 'n' };
                ws[`G${currentRow}`] = { v: calc.eligibilityText, t: 's' };
                ws[`H${currentRow}`] = { v: expense.companyPaidTotal || 0, t: 'n' };
                ws[`I${currentRow}`] = { v: calc.finalClaimable, t: 'n' };
                
                totalRoomRent += calc.totalRoomRent;
                totalTax += calc.totalTax;
                totalAmount += calc.totalExpense;
                totalClaimable += calc.finalClaimable;
                
                currentRow++;
            });
        }
    });
    
    // Add empty rows up to row 18
    while (currentRow < 19) {
        ws[`D${currentRow}`] = { v: 0, t: 'n' };
        ws[`E${currentRow}`] = { v: 0, t: 'n' };
        ws[`F${currentRow}`] = { v: 0, t: 'n' };
        ws[`H${currentRow}`] = { v: 0, t: 'n' };
        ws[`I${currentRow}`] = { v: 0, t: 'n' };
        currentRow++;
    }
    
    // Summary row
    ws['B18'] = { v: 'from _____ to ______', t: 's' };
    ws['C18'] = { v: 'Stayed at _________________', t: 's' };
    ws['D18'] = { v: 0, t: 'n' };
    ws['E18'] = { v: 0, t: 'n' };
    ws['F18'] = { v: 0, t: 'n' };
    
    // Total row
    ws['C19'] = { v: 'TOTAL', t: 's' };
    ws['D19'] = { v: totalRoomRent, t: 'n' };
    ws['E19'] = { v: totalTax, t: 'n' };
    ws['F19'] = { v: totalAmount, t: 'n' };
    ws['G19'] = { v: '-', t: 's' };
    ws['H19'] = { v: 0, t: 'n' };
    ws['I19'] = { v: totalClaimable, t: 'n' };
    
    // Set range
    const range = XLSX.utils.encode_range({ s: { c: 0, r: 0 }, e: { c: 8, r: 20 } });
    ws['!ref'] = range;
    
    return ws;
}

function createLocalConveyanceSheet() {
    const ws = {};
    
    // Set column widths
    ws['!cols'] = [
        {wch: 3}, {wch: 12}, {wch: 15}, {wch: 15}, {wch: 15}, {wch: 12}
    ];
    
    // Header
    ws['B4'] = { v: `Details of Local Conveyance of ${currentUser.employeeName} (E.No.${currentUser.persNo}) in ${getLocationsList()}.`, t: 's' };
    
    // Column Headers
    ws['B7'] = { v: 'Date', t: 's' };
    ws['C7'] = { v: 'From', t: 's' };
    ws['D7'] = { v: 'To', t: 's' };
    ws['E7'] = { v: 'Mode of Travel', t: 's' };
    ws['F7'] = { v: 'Amount Rs.', t: 's' };
    
    // Data Rows
    let currentRow = 8;
    let totalAmount = 0;
    
    travelEntries.forEach(travel => {
        if (travel.localConveyance && travel.localConveyance.length > 0) {
            travel.localConveyance.forEach(entry => {
                ws[`B${currentRow}`] = { v: formatDate(entry.date), t: 's' };
                ws[`C${currentRow}`] = { v: entry.from, t: 's' };
                ws[`D${currentRow}`] = { v: entry.to, t: 's' };
                ws[`E${currentRow}`] = { v: entry.modeOfTravel, t: 's' };
                ws[`F${currentRow}`] = { v: entry.amount, t: 'n' };
                
                totalAmount += entry.amount;
                currentRow++;
            });
        }
    });
    
    // Add empty rows with quotes up to row 16
    while (currentRow < 17) {
        ws[`E${currentRow}`] = { v: '"', t: 's' };
        currentRow++;
    }
    
    // Total row
    ws['C17'] = { v: 'TOTAL', t: 's' };
    ws['F17'] = { v: totalAmount, t: 'n' };
    
    // Set range
    const range = XLSX.utils.encode_range({ s: { c: 0, r: 0 }, e: { c: 5, r: 18 } });
    ws['!ref'] = range;
    
    return ws;
}

function getLocationsList() {
    const locations = new Set();
    travelEntries.forEach(travel => {
        locations.add(travel.fromLocation);
        locations.add(travel.toLocation);
    });
    return Array.from(locations).join(', ');
}

function printSelected() {
    const selectedCheckboxes = document.querySelectorAll('.travel-select:checked');
    if (selectedCheckboxes.length === 0) {
        alert('Please select at least one travel entry to print');
        return;
    }
    
    const selectedIndices = Array.from(selectedCheckboxes).map(cb => parseInt(cb.dataset.index));
    const selectedEntries = selectedIndices.map(index => travelEntries[index]);
    
    // Create temporary workbook with selected entries
    const originalEntries = [...travelEntries];
    travelEntries = selectedEntries;
    
    const workbook = XLSX.utils.book_new();
    
    const tebillSheet = createTEBILLSheet();
    XLSX.utils.book_append_sheet(workbook, tebillSheet, 'TEBILL');
    
    const hotelSheet = createHotelExpensesSheet();
    XLSX.utils.book_append_sheet(workbook, hotelSheet, 'Hotel Expenses');
    
    const conveyanceSheet = createLocalConveyanceSheet();
    XLSX.utils.book_append_sheet(workbook, conveyanceSheet, 'Local Conveyance');
    
    // Restore original entries
    travelEntries = originalEntries;
    
    // Export file
    const fileName = `TravelClaim_Selected_${currentUser.persNo}_${new Date().toISOString().split('T')[0]}.xlsx`;
    XLSX.writeFile(workbook, fileName);
}

function viewAllSheets() {
    if (travelEntries.length === 0) {
        alert('No travel entries to preview');
        return;
    }
    
    generateSheetPreviews();
    showModal('allSheetsModal');
    showModalTab('tebill-preview');
}

function generateSheetPreviews() {
    // Generate TEBILL Preview
    generateTEBILLPreview();
    
    // Generate Hotel Expenses Preview
    generateHotelExpensesPreview();
    
    // Generate Local Conveyance Preview
    generateLocalConveyancePreview();
}

function generateTEBILLPreview() {
    const container = document.getElementById('tebillPreviewContent');
    
    let html = `
        <div class="excel-sheet">
            <table class="excel-table">
                <tr><td colspan="19" class="company-header">XYZ - TRAVEL EXPENSE STATEMENT</td></tr>
                <tr>
                    <td colspan="2">NAME / EMP No.:</td>
                    <td colspan="2">${currentUser.employeeName} / ${currentUser.persNo}</td>
                    <td>GRADE:</td>
                    <td>${currentUser.grade}</td>
                    <td>DESIGNATION:</td>
                    <td colspan="2">${currentUser.position}</td>
                    <td colspan="2">DEPARTMENT:</td>
                    <td>${currentUser.department}</td>
                    <td colspan="2">DATE:</td>
                    <td colspan="2">${new Date().toLocaleDateString('en-GB')}</td>
                </tr>
                <tr>
                    <td colspan="2">PLACE & PURPOSE OF VISIT:</td>
                    <td colspan="17">${document.getElementById('purposeOfVisit').value || ''}</td>
                </tr>
                <tr class="header-row">
                    <td>DATE</td>
                    <td>FROM</td>
                    <td>TO</td>
                    <td>MODE/CLASS</td>
                    <td>FARE (Rs.)</td>
                    <td>HOTEL BILLS/SUST.EXP (Rs.)</td>
                    <td>BUSINESS DISC (Rs.)</td>
                    <td>MISCELLANEOUS/OUT OF POCKET EXPENSES (Rs.)</td>
                    <td>CONVEYANCE EXPENSES (Rs.)</td>
                    <td>ADVANCE (Rs.)</td>
                    <td>Tourist Taxi Credit</td>
                    <td>Company Car</td>
                    <td>Total (Rs.)</td>
                </tr>
    `;
    
    let totalFare = 0, totalHotel = 0, totalBusinessDisc = 0, totalMisc = 0, totalConveyance = 0, totalAdvance = 0;
    
    travelEntries.forEach(travel => {
        const hotelTotal = calculateHotelTotal(travel.hotelExpenses);
        const conveyanceTotal = calculateConveyanceTotal(travel.localConveyance);
        const rowTotal = (travel.fare || 0) + hotelTotal + (travel.miscExpenses || 0) + conveyanceTotal - (travel.businessDisc || 0);
        
        html += `
            <tr>
                <td>${formatDate(travel.dateFrom)} to ${formatDate(travel.dateTo)}</td>
                <td>${travel.fromLocation}</td>
                <td>${travel.toLocation}</td>
                <td>${travel.modeClass}</td>
                <td>${formatCurrency(travel.fare)}</td>
                <td>${formatCurrency(hotelTotal)}</td>
                <td>${formatCurrency(travel.businessDisc)}</td>
                <td>${formatCurrency(travel.miscExpenses)}</td>
                <td>${formatCurrency(conveyanceTotal)}</td>
                <td>${formatCurrency(travel.advance)}</td>
                <td>${travel.touristTaxi ? '✓' : ''}</td>
                <td>${travel.companyCar ? '✓' : ''}</td>
                <td>${formatCurrency(rowTotal)}</td>
            </tr>
        `;
        
        totalFare += travel.fare || 0;
        totalHotel += hotelTotal;
        totalBusinessDisc += travel.businessDisc || 0;
        totalMisc += travel.miscExpenses || 0;
        totalConveyance += conveyanceTotal;
        totalAdvance += travel.advance || 0;
    });
    
    html += `
                <tr class="total-row">
                    <td colspan="4"><strong>TOTAL</strong></td>
                    <td><strong>${formatCurrency(totalFare)}</strong></td>
                    <td><strong>${formatCurrency(totalHotel)}</strong></td>
                    <td><strong>${formatCurrency(totalBusinessDisc)}</strong></td>
                    <td><strong>${formatCurrency(totalMisc)}</strong></td>
                    <td><strong>${formatCurrency(totalConveyance)}</strong></td>
                    <td><strong>${formatCurrency(totalAdvance)}</strong></td>
                    <td colspan="2"></td>
                    <td><strong>${formatCurrency(totalFare + totalHotel + totalMisc + totalConveyance - totalBusinessDisc)}</strong></td>
                </tr>
            </table>
        </div>
    `;
    
    container.innerHTML = html;
}

function generateHotelExpensesPreview() {
    const container = document.getElementById('hotelPreviewContent');
    
    let html = `
        <div class="excel-sheet">
            <h3>Food & Lodging Expenses of ${currentUser.employeeName} (E.No.${currentUser.persNo}) in ${getLocationsList()}</h3>
            <table class="excel-table">
                <tr class="header-row">
                    <td>Date</td>
                    <td>Particulars</td>
                    <td>Room Rent (Rs.)</td>
                    <td>Tax (Rs.)</td>
                    <td>Total (Rs.)</td>
                    <td>Eligibility</td>
                    <td>Amount Paid by Company</td>
                    <td>Balance Amount Claimed Rs.</td>
                </tr>
    `;
    
    let totalRoomRent = 0, totalTax = 0, totalAmount = 0, totalClaimable = 0;
    
    travelEntries.forEach(travel => {
        if (travel.hotelExpenses && travel.hotelExpenses.length > 0) {
            travel.hotelExpenses.forEach(expense => {
                const calc = calculateHotelEligibility(expense, currentUser.grade, travel.toLocation);
                
                html += `
                    <tr>
                        <td>${formatDate(expense.dateFrom)} to ${formatDate(expense.dateTo)}</td>
                        <td>${expense.particulars}</td>
                        <td>${formatCurrency(calc.totalRoomRent)}</td>
                        <td>${formatCurrency(calc.totalTax)}</td>
                        <td>${formatCurrency(calc.totalExpense)}</td>
                        <td>${calc.eligibilityText}</td>
                        <td>${formatCurrency(expense.companyPaidTotal)}</td>
                        <td>${formatCurrency(calc.finalClaimable)}</td>
                    </tr>
                `;
                
                totalRoomRent += calc.totalRoomRent;
                totalTax += calc.totalTax;
                totalAmount += calc.totalExpense;
                totalClaimable += calc.finalClaimable;
            });
        }
    });
    
    html += `
                <tr class="total-row">
                    <td colspan="2"><strong>TOTAL</strong></td>
                    <td><strong>${formatCurrency(totalRoomRent)}</strong></td>
                    <td><strong>${formatCurrency(totalTax)}</strong></td>
                    <td><strong>${formatCurrency(totalAmount)}</strong></td>
                    <td><strong>-</strong></td>
                    <td><strong>-</strong></td>
                    <td><strong>${formatCurrency(totalClaimable)}</strong></td>
                </tr>
            </table>
        </div>
    `;
    
    container.innerHTML = html;
}

function generateLocalConveyancePreview() {
    const container = document.getElementById('conveyancePreviewContent');
    
    let html = `
        <div class="excel-sheet">
            <h3>Details of Local Conveyance of ${currentUser.employeeName} (E.No.${currentUser.persNo}) in ${getLocationsList()}</h3>
            <table class="excel-table">
                <tr class="header-row">
                    <td>Date</td>
                    <td>From</td>
                    <td>To</td>
                    <td>Mode of Travel</td>
                    <td>Amount Rs.</td>
                </tr>
    `;
    
    let totalAmount = 0;
    
    travelEntries.forEach(travel => {
        if (travel.localConveyance && travel.localConveyance.length > 0) {
            travel.localConveyance.forEach(entry => {
                html += `
                    <tr>
                        <td>${formatDate(entry.date)}</td>
                        <td>${entry.from}</td>
                        <td>${entry.to}</td>
                        <td>${entry.modeOfTravel}</td>
                        <td>${formatCurrency(entry.amount)}</td>
                    </tr>
                `;
                
                totalAmount += entry.amount;
            });
        }
    });
    
    html += `
                <tr class="total-row">
                    <td colspan="4"><strong>TOTAL</strong></td>
                    <td><strong>${formatCurrency(totalAmount)}</strong></td>
                </tr>
            </table>
        </div>
    `;
    
    container.innerHTML = html;
}

function printAllSheets() {
    window.print();
}

