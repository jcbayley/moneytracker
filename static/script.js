let currentAccount = null;
let charts = {};
let editingAccountId = null;
let editingTransactionId = null;
let currentAnalyticsMonth = new Date();

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('date').valueAsDate = new Date();
    loadAccounts();
    loadTransactions();
    loadRecurringTransactions();
    updateAnalytics();
    getDatabaseInfo();
    
    // Handle window resize for chart responsiveness
    window.addEventListener('resize', debounce(function() {
        if (Object.keys(charts).length > 0) {
            Object.values(charts).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        }
    }, 250));
});

// API Functions
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(endpoint, options);
    return await response.json();
}

async function loadAccounts() {
    const accounts = await apiCall('/api/accounts');
    const accountsList = document.getElementById('accounts-list');
    const accountSelect = document.getElementById('account-select');
    const transactionAccountFilter = document.getElementById('transaction-account-filter');
    const editTransactionAccount = document.getElementById('edit-transaction-account');
    const transferAccount = document.getElementById('transfer-account');
    const editTransferAccount = document.getElementById('edit-transfer-account');
    
    accountsList.innerHTML = '';
    accountSelect.innerHTML = '<option value="">All Accounts</option>';
    if (transactionAccountFilter) {
        transactionAccountFilter.innerHTML = '<option value="">All Accounts</option>';
    }
    if (editTransactionAccount) {
        editTransactionAccount.innerHTML = '';
    }
    if (transferAccount) {
        transferAccount.innerHTML = '<option value="">Select destination account</option>';
    }
    if (editTransferAccount) {
        editTransferAccount.innerHTML = '<option value="">Select destination account</option>';
    }
    
    // Group accounts by type
    const accountsByType = accounts.reduce((acc, account) => {
        if (!acc[account.type]) acc[account.type] = [];
        acc[account.type].push(account);
        return acc;
    }, {});
    
    // Sort types for consistent display
    const typeOrder = ['checking', 'savings', 'credit', 'investment'];
    const sortedTypes = Object.keys(accountsByType).sort((a, b) => {
        const aIndex = typeOrder.indexOf(a);
        const bIndex = typeOrder.indexOf(b);
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
    });
    
    sortedTypes.forEach(type => {
        // Add type header
        const typeHeader = document.createElement('div');
        typeHeader.className = 'account-type-header';
        typeHeader.innerHTML = `<h4>${type.charAt(0).toUpperCase() + type.slice(1)}</h4>`;
        accountsList.appendChild(typeHeader);
        
        accountsByType[type].forEach(account => {
            // Sidebar
            const div = document.createElement('div');
            div.className = 'account-item';
            if (account.id === currentAccount) div.classList.add('active');
            div.onclick = () => selectAccount(account.id);
            div.innerHTML = `
                <span>${account.name}</span>
                <div>
                    <span class="amount ${account.balance >= 0 ? 'positive' : 'negative'}">
                        £${Math.abs(account.balance).toFixed(2)}
                    </span>
                    <button class="btn-edit" onclick="editAccount(${account.id}, '${account.name}', '${account.type}'); event.stopPropagation();">✏️</button>
                </div>
            `;
            accountsList.appendChild(div);
            
            // Add to all dropdowns
            const option = document.createElement('option');
            option.value = account.id;
            option.textContent = account.name;
            accountSelect.appendChild(option);
            
            if (transactionAccountFilter) {
                const filterOption = document.createElement('option');
                filterOption.value = account.id;
                filterOption.textContent = account.name;
                transactionAccountFilter.appendChild(filterOption);
            }
            
            if (editTransactionAccount) {
                const editOption = document.createElement('option');
                editOption.value = account.id;
                editOption.textContent = account.name;
                editTransactionAccount.appendChild(editOption);
            }
            
            if (transferAccount) {
                const transferOption = document.createElement('option');
                transferOption.value = account.id;
                transferOption.textContent = account.name;
                transferAccount.appendChild(transferOption);
            }
            
            if (editTransferAccount) {
                const editTransferOption = document.createElement('option');
                editTransferOption.value = account.id;
                editTransferOption.textContent = account.name;
                editTransferAccount.appendChild(editTransferOption);
            }
        });
    });
}

async function loadTransactions() {
    // Build query parameters
    const params = new URLSearchParams();
    
    // Account filter (either from sidebar or filter dropdown)
    const accountFilter = document.getElementById('transaction-account-filter');
    const selectedAccount = accountFilter ? accountFilter.value : '';
    if (currentAccount) {
        params.append('account_id', currentAccount);
    } else if (selectedAccount) {
        params.append('account_id', selectedAccount);
    }
    
    // Category filter
    const categoryFilter = document.getElementById('transaction-category-filter');
    if (categoryFilter && categoryFilter.value) {
        params.append('category', categoryFilter.value);
    }
    
    // Type filter
    const typeFilter = document.getElementById('transaction-type-filter');
    if (typeFilter && typeFilter.value) {
        params.append('type', typeFilter.value);
    }
    
    // Date filter
    const dateFrom = document.getElementById('transaction-date-from');
    if (dateFrom && dateFrom.value) {
        params.append('date_from', dateFrom.value);
    }
    
    const endpoint = `/api/transactions?${params.toString()}`;
    const transactions = await apiCall(endpoint);
    const tbody = document.getElementById('transactions-list');
    
    tbody.innerHTML = '';
    transactions.forEach(t => {
        const tr = document.createElement('tr');
        const isPositive = t.amount >= 0;
        const recurring = t.frequency ? `<span class="recurring-badge">${t.frequency}</span>` : '';
        
        tr.innerHTML = `
            <td>${t.date}</td>
            <td>${t.account_name}</td>
            <td>${t.payee || '-'}${recurring}</td>
            <td>${t.category || '-'}</td>
            <td class="amount ${isPositive ? 'positive' : 'negative'}">
                £${Math.abs(t.amount).toFixed(2)}
            </td>
            <td>${t.type}</td>
            <td>${t.notes || '-'}</td>
            <td>
                <button class="btn btn-secondary" style="padding: 5px 8px; font-size: 12px; margin-right: 5px;" 
                        onclick="editTransaction(${t.id})">✏️</button>
                <button class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" 
                        onclick="deleteTransaction(${t.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function loadRecurringTransactions() {
    const recurring = await apiCall('/api/recurring');
    const list = document.getElementById('recurring-list');
    
    list.innerHTML = '';
    if (recurring.length === 0) {
        list.innerHTML = '<p style="color: #6c757d;">No recurring transactions set up yet.</p>';
        return;
    }
    
    recurring.forEach(r => {
        const div = document.createElement('div');
        div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #dee2e6;';
        const isPositive = r.amount >= 0;
        
        div.innerHTML = `
            <div>
                <strong>${r.payee || 'Transaction'}</strong> - ${r.account_name}
                <br>
                <small>${r.frequency} | ${r.category || 'No category'} | Next: ${r.next_date}</small>
            </div>
            <div>
                <span class="amount ${isPositive ? 'positive' : 'negative'}">
                    £${Math.abs(r.amount).toFixed(2)}
                </span>
                <button class="btn btn-danger" style="margin-left: 10px; padding: 5px 10px; font-size: 12px;" 
                        onclick="deleteRecurring(${r.id})">Delete</button>
            </div>
        `;
        list.appendChild(div);
    });
}

async function addTransaction() {
    // Handle custom category
    let category = document.getElementById('category').value;
    if (category === 'custom') {
        category = prompt('Enter new category name:');
        if (!category) return;
    }
    
    const data = {
        account_id: document.getElementById('account-select').value,
        amount: parseFloat(document.getElementById('amount').value),
        date: document.getElementById('date').value,
        type: document.getElementById('type').value,
        payee: document.getElementById('payee').value,
        category: category,
        notes: document.getElementById('notes').value,
        is_recurring: document.getElementById('is-recurring').checked,
        frequency: document.getElementById('frequency').value,
        end_date: document.getElementById('end-date').value || null
    };
    
    if (!data.account_id || !data.amount || !data.date) {
        alert('Please fill in required fields: Account, Amount, and Date');
        return;
    }
    
    // Handle transfer
    if (data.type === 'transfer') {
        const transferAccountId = document.getElementById('transfer-account').value;
        if (!transferAccountId) {
            alert('Please select a destination account for the transfer');
            return;
        }
        data.transfer_account_id = transferAccountId;
        // Set payee to destination account name
        const accounts = await apiCall('/api/accounts');
        const destAccount = accounts.find(a => a.id == transferAccountId);
        data.payee = destAccount ? destAccount.name : 'Transfer';
    } else if (data.type === 'expense') {
        data.amount = -Math.abs(data.amount);
    } else {
        data.amount = Math.abs(data.amount);
    }
    
    await apiCall('/api/transactions', 'POST', data);
    clearForm();
    loadAccounts();
    loadTransactions();
    loadRecurringTransactions();
    updateAnalytics();
}

async function deleteTransaction(id) {
    if (confirm('Are you sure you want to delete this transaction?')) {
        await apiCall(`/api/transactions/${id}`, 'DELETE');
        loadAccounts();
        loadTransactions();
        updateAnalytics();
    }
}

async function deleteRecurring(id) {
    if (confirm('Are you sure you want to delete this recurring transaction?')) {
        await apiCall(`/api/recurring/${id}`, 'DELETE');
        loadRecurringTransactions();
    }
}

async function processRecurring() {
    const result = await apiCall('/api/recurring/process', 'POST');
    alert(result.message);
    if (result.processed > 0) {
        loadAccounts();
        loadTransactions();
        updateAnalytics();
    }
}

async function addAccount() {
    const data = {
        name: document.getElementById('new-account-name').value,
        type: document.getElementById('new-account-type').value,
        balance: parseFloat(document.getElementById('new-account-balance').value) || 0
    };
    
    if (!data.name) {
        alert('Please enter an account name');
        return;
    }
    
    await apiCall('/api/accounts', 'POST', data);
    closeModal();
    loadAccounts();
}

async function updateAnalytics() {
    const filters = getAnalyticsFilters();
    const queryString = new URLSearchParams(filters).toString();
    
    const stats = await apiCall(`/api/analytics/stats?${queryString}`);
    document.getElementById('total-balance').textContent = `£${stats.total_balance.toFixed(2)}`;
    document.getElementById('monthly-income').textContent = `£${stats.monthly_income.toFixed(2)}`;
    document.getElementById('monthly-expenses').textContent = `£${stats.monthly_expenses.toFixed(2)}`;
    document.getElementById('net-monthly').textContent = `£${stats.net_monthly.toFixed(2)}`;
    
    // Update charts
    updateCharts();
}

function getAnalyticsFilters() {
    const filters = {};
    
    // Get selected account types
    const accountTypeChecks = document.querySelectorAll('#account-type-filters input[type="checkbox"]:checked');
    const selectedTypes = Array.from(accountTypeChecks).map(cb => cb.value);
    if (selectedTypes.length > 0) {
        selectedTypes.forEach(type => {
            if (!filters['account_types']) filters['account_types'] = [];
            filters['account_types'].push(type);
        });
    }
    
    // Get date range
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (startDate) filters['start_date'] = startDate;
    if (endDate) filters['end_date'] = endDate;
    
    return filters;
}

function updateDateFilter() {
    const period = document.getElementById('date-period').value;
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    const prevBtn = document.getElementById('prev-month');
    const nextBtn = document.getElementById('next-month');
    const currentPeriodSpan = document.getElementById('current-period');
    
    // Reset
    startDate.disabled = true;
    endDate.disabled = true;
    prevBtn.style.display = 'none';
    nextBtn.style.display = 'none';
    
    const now = new Date();
    let start, end;
    
    if (period === 'custom') {
        startDate.disabled = false;
        endDate.disabled = false;
        currentPeriodSpan.textContent = 'Custom Range';
        return;
    }
    
    if (period === 'current_month' || period === 'last_month') {
        prevBtn.style.display = 'inline-block';
        nextBtn.style.display = 'inline-block';
    }
    
    switch (period) {
        case 'current_month':
            start = new Date(currentAnalyticsMonth.getFullYear(), currentAnalyticsMonth.getMonth(), 1);
            end = new Date(currentAnalyticsMonth.getFullYear(), currentAnalyticsMonth.getMonth() + 1, 0);
            currentPeriodSpan.textContent = currentAnalyticsMonth.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
            break;
        case 'last_month':
            const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            start = lastMonth;
            end = new Date(now.getFullYear(), now.getMonth(), 0);
            currentPeriodSpan.textContent = lastMonth.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
            break;
        case 'last_3_months':
            start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
            end = now;
            currentPeriodSpan.textContent = 'Last 3 Months';
            break;
        case 'last_6_months':
            start = new Date(now.getFullYear(), now.getMonth() - 6, 1);
            end = now;
            currentPeriodSpan.textContent = 'Last 6 Months';
            break;
        case 'this_year':
            start = new Date(now.getFullYear(), 0, 1);
            end = now;
            currentPeriodSpan.textContent = now.getFullYear().toString();
            break;
    }
    
    if (start && end) {
        startDate.value = start.toISOString().split('T')[0];
        endDate.value = end.toISOString().split('T')[0];
    }
    
    updateAnalytics();
}

function navigateMonth(direction) {
    currentAnalyticsMonth.setMonth(currentAnalyticsMonth.getMonth() + direction);
    updateDateFilter();
}

async function updateCharts() {
    const filters = getAnalyticsFilters();
    const queryString = new URLSearchParams(filters).toString();
    const chartData = await apiCall(`/api/analytics/charts?${queryString}`);
    
    // Category Chart
    if (chartData.category.labels.length > 0) {
        const ctx1 = document.getElementById('categoryChart').getContext('2d');
        if (charts.category) charts.category.destroy();
        charts.category = new Chart(ctx1, {
            type: 'doughnut',
            data: chartData.category,
            options: { 
                responsive: true, 
                maintainAspectRatio: true,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const category = chartData.category.labels[index];
                        showCategoryDetails(category);
                    }
                }
            }
        });
    }
    
    // Trend Chart
    if (chartData.trend.labels.length > 0) {
        const ctx2 = document.getElementById('trendChart').getContext('2d');
        if (charts.trend) charts.trend.destroy();
        charts.trend = new Chart(ctx2, {
            type: 'line',
            data: chartData.trend,
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    // Account Chart
    if (chartData.accounts.labels.length > 0) {
        const ctx3 = document.getElementById('accountChart').getContext('2d');
        if (charts.account) charts.account.destroy();
        charts.account = new Chart(ctx3, {
            type: 'bar',
            data: chartData.accounts,
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    // Category Trends Chart
    if (chartData.category_trends && chartData.category_trends.labels.length > 0) {
        const ctx4 = document.getElementById('categoryTrendsChart').getContext('2d');
        if (charts.categoryTrends) charts.categoryTrends.destroy();
        charts.categoryTrends = new Chart(ctx4, {
            type: 'line',
            data: chartData.category_trends,
            options: { 
                responsive: true,
                scales: { y: { beginAtZero: true } },
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

async function getDatabaseInfo() {
    const info = await apiCall('/api/database/info');
    document.getElementById('db-size').textContent = `Size: ${info.size}`;
}

async function exportData() {
    window.location.href = '/api/export';
}

async function exportCsv() {
    window.location.href = '/api/export/csv';
}

async function importData() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.db';
    input.onchange = async function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.name.endsWith('.db')) {
            alert('Please select a .db file');
            return;
        }
        
        if (!confirm('This will replace your current database. Are you sure? (Current database will be backed up)')) {
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/import', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                alert(result.message + '\n\nPage will reload to show new data.');
                window.location.reload();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('Error importing database: ' + error.message);
        }
    };
    input.click();
}

async function importCsv() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.onchange = async function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.name.toLowerCase().endsWith('.csv')) {
            alert('Please select a .csv file');
            return;
        }
        
        if (!confirm('This will import transactions from the CSV file. Existing transactions will not be affected. Continue?')) {
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/import/csv', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                alert(result.message + '\n\nPage will reload to show imported data.');
                window.location.reload();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('Error importing CSV: ' + error.message);
        }
    };
    input.click();
}

function selectAccount(accountId) {
    currentAccount = accountId === currentAccount ? null : accountId;
    loadAccounts();
    loadTransactions();
}

function switchTab(tab) {
    const tabs = ['transactions', 'recurring', 'analytics', 'settings'];
    tabs.forEach(t => {
        document.getElementById(`${t}-tab`).classList.add('hidden');
    });
    document.getElementById(`${tab}-tab`).classList.remove('hidden');
    
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    
    if (tab === 'analytics') {
        updateDateFilter(); // This will also call updateAnalytics()
    } else if (tab === 'settings') {
        getDatabaseInfo();
    }
}

function toggleRecurring() {
    const section = document.getElementById('recurring-section');
    const checkbox = document.getElementById('is-recurring');
    section.classList.toggle('active', checkbox.checked);
}

function clearForm() {
    document.getElementById('amount').value = '';
    document.getElementById('payee').value = '';
    document.getElementById('notes').value = '';
    document.getElementById('date').valueAsDate = new Date();
    document.getElementById('type').value = 'expense';
    document.getElementById('is-recurring').checked = false;
    document.getElementById('recurring-section').classList.remove('active');
    
    // Hide transfer fields
    const transferRow = document.getElementById('transfer-row');
    if (transferRow) {
        transferRow.style.display = 'none';
    }
}

function showAddAccountModal() {
    document.getElementById('accountModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('accountModal').style.display = 'none';
    document.getElementById('new-account-name').value = '';
    document.getElementById('new-account-balance').value = '0';
}

function editAccount(id, name, type) {
    editingAccountId = id;
    document.getElementById('edit-account-name').value = name;
    document.getElementById('edit-account-type').value = type;
    document.getElementById('editAccountModal').style.display = 'block';
}

function closeEditModal() {
    document.getElementById('editAccountModal').style.display = 'none';
    editingAccountId = null;
}

async function updateAccount() {
    if (!editingAccountId) return;
    
    const data = {
        name: document.getElementById('edit-account-name').value,
        type: document.getElementById('edit-account-type').value
    };
    
    if (!data.name) {
        alert('Please enter an account name');
        return;
    }
    
    await apiCall(`/api/accounts/${editingAccountId}`, 'PUT', data);
    closeEditModal();
    loadAccounts();
}

async function editTransaction(id) {
    // Get transaction details
    const transactions = await apiCall('/api/transactions');
    const transaction = transactions.find(t => t.id === id);
    
    if (!transaction) return;
    
    editingTransactionId = id;
    
    // Populate form
    document.getElementById('edit-transaction-account').value = transaction.account_id;
    document.getElementById('edit-transaction-amount').value = Math.abs(transaction.amount);
    document.getElementById('edit-transaction-date').value = transaction.date;
    document.getElementById('edit-transaction-type').value = transaction.type;
    document.getElementById('edit-transaction-payee').value = transaction.payee || '';
    document.getElementById('edit-transaction-category').value = transaction.category || '';
    document.getElementById('edit-transaction-notes').value = transaction.notes || '';
    
    // Handle transfer fields
    if (transaction.type === 'transfer') {
        // For transfers, try to find the destination account by payee name
        const accounts = await apiCall('/api/accounts');
        const destAccount = accounts.find(a => a.name === transaction.payee);
        if (destAccount) {
            document.getElementById('edit-transfer-account').value = destAccount.id;
        }
        toggleEditTransferFields();
    }
    
    document.getElementById('editTransactionModal').style.display = 'block';
}

function closeEditTransactionModal() {
    document.getElementById('editTransactionModal').style.display = 'none';
    editingTransactionId = null;
}

async function updateTransaction() {
    if (!editingTransactionId) return;
    
    // Handle custom category
    let category = document.getElementById('edit-transaction-category').value;
    if (category === 'custom') {
        category = prompt('Enter new category name:');
        if (!category) return;
    }
    
    const data = {
        account_id: parseInt(document.getElementById('edit-transaction-account').value),
        amount: parseFloat(document.getElementById('edit-transaction-amount').value),
        date: document.getElementById('edit-transaction-date').value,
        type: document.getElementById('edit-transaction-type').value,
        payee: document.getElementById('edit-transaction-payee').value,
        category: category,
        notes: document.getElementById('edit-transaction-notes').value
    };
    
    if (!data.account_id || !data.amount || !data.date) {
        alert('Please fill in required fields: Account, Amount, and Date');
        return;
    }
    
    // Handle transfer
    if (data.type === 'transfer') {
        const transferAccountId = document.getElementById('edit-transfer-account').value;
        if (!transferAccountId) {
            alert('Please select a destination account for the transfer');
            return;
        }
        data.transfer_account_id = transferAccountId;
        // Set payee to destination account name
        const accounts = await apiCall('/api/accounts');
        const destAccount = accounts.find(a => a.id == transferAccountId);
        data.payee = destAccount ? destAccount.name : 'Transfer';
    }
    
    await apiCall(`/api/transactions/${editingTransactionId}`, 'PUT', data);
    closeEditTransactionModal();
    loadAccounts();
    loadTransactions();
    updateAnalytics();
}

function toggleTransferFields() {
    const type = document.getElementById('type').value;
    const transferRow = document.getElementById('transfer-row');
    transferRow.style.display = type === 'transfer' ? 'flex' : 'none';
}

function toggleEditTransferFields() {
    const type = document.getElementById('edit-transaction-type').value;
    const transferRow = document.getElementById('edit-transfer-row');
    transferRow.style.display = type === 'transfer' ? 'flex' : 'none';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    sidebar.classList.toggle('collapsed');
    if (mainContent) {
        mainContent.classList.toggle('expanded');
    }
}

async function showCategoryDetails(category) {
    const filters = getAnalyticsFilters();
    const queryString = new URLSearchParams(filters).toString();
    
    const transactions = await apiCall(`/api/analytics/category/${encodeURIComponent(category)}?${queryString}`);
    
    document.getElementById('category-modal-title').textContent = `${category} Transactions`;
    
    const tableContainer = document.getElementById('category-transactions-table');
    
    if (transactions.length === 0) {
        tableContainer.innerHTML = '<p style="color: #6c757d; text-align: center; padding: 20px;">No transactions found for this category in the selected period.</p>';
    } else {
        let tableHtml = `
            <table style="width: 100%; margin-top: 15px;">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Account</th>
                        <th>Payee</th>
                        <th>Amount</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        transactions.forEach(t => {
            const isPositive = t.amount >= 0;
            tableHtml += `
                <tr>
                    <td>${t.date}</td>
                    <td>${t.account_name}</td>
                    <td>${t.payee || '-'}</td>
                    <td class="amount ${isPositive ? 'positive' : 'negative'}">
                        £${Math.abs(t.amount).toFixed(2)}
                    </td>
                    <td>${t.notes || '-'}</td>
                </tr>
            `;
        });
        
        tableHtml += '</tbody></table>';
        tableContainer.innerHTML = tableHtml;
    }
    
    document.getElementById('categoryDetailsModal').style.display = 'block';
}

function closeCategoryModal() {
    document.getElementById('categoryDetailsModal').style.display = 'none';
}

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}