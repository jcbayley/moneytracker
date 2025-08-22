let currentAccount = null;
let charts = {};

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
    
    accountsList.innerHTML = '';
    accountSelect.innerHTML = '<option value="">All Accounts</option>';
    
    accounts.forEach(account => {
        // Sidebar
        const div = document.createElement('div');
        div.className = 'account-item';
        if (account.id === currentAccount) div.classList.add('active');
        div.onclick = () => selectAccount(account.id);
        div.innerHTML = `
            <span>${account.name}</span>
            <span class="amount ${account.balance >= 0 ? 'positive' : 'negative'}">
                £${Math.abs(account.balance).toFixed(2)}
            </span>
        `;
        accountsList.appendChild(div);
        
        // Select dropdown
        const option = document.createElement('option');
        option.value = account.id;
        option.textContent = account.name;
        accountSelect.appendChild(option);
    });
}

async function loadTransactions() {
    const endpoint = currentAccount 
        ? `/api/transactions?account_id=${currentAccount}`
        : '/api/transactions';
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
    const data = {
        account_id: document.getElementById('account-select').value,
        amount: parseFloat(document.getElementById('amount').value),
        date: document.getElementById('date').value,
        type: document.getElementById('type').value,
        payee: document.getElementById('payee').value,
        category: document.getElementById('category').value,
        notes: document.getElementById('notes').value,
        is_recurring: document.getElementById('is-recurring').checked,
        frequency: document.getElementById('frequency').value,
        end_date: document.getElementById('end-date').value || null
    };
    
    if (!data.account_id || !data.amount || !data.date) {
        alert('Please fill in required fields: Account, Amount, and Date');
        return;
    }
    
    if (data.type === 'expense') {
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
    const stats = await apiCall('/api/analytics/stats');
    document.getElementById('total-balance').textContent = `£${stats.total_balance.toFixed(2)}`;
    document.getElementById('monthly-income').textContent = `£${stats.monthly_income.toFixed(2)}`;
    document.getElementById('monthly-expenses').textContent = `£${stats.monthly_expenses.toFixed(2)}`;
    document.getElementById('net-monthly').textContent = `£${stats.net_monthly.toFixed(2)}`;
    
    // Update charts
    updateCharts();
}

async function updateCharts() {
    const chartData = await apiCall('/api/analytics/charts');
    
    // Category Chart
    if (chartData.category.labels.length > 0) {
        const ctx1 = document.getElementById('categoryChart').getContext('2d');
        if (charts.category) charts.category.destroy();
        charts.category = new Chart(ctx1, {
            type: 'doughnut',
            data: chartData.category,
            options: { responsive: true, maintainAspectRatio: true }
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
    
    // Income vs Expense Chart
    if (chartData.income_expense.labels.length > 0) {
        const ctx4 = document.getElementById('incomeExpenseChart').getContext('2d');
        if (charts.incomeExpense) charts.incomeExpense.destroy();
        charts.incomeExpense = new Chart(ctx4, {
            type: 'pie',
            data: chartData.income_expense,
            options: { responsive: true }
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
        updateAnalytics();
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
    document.getElementById('is-recurring').checked = false;
    document.getElementById('recurring-section').classList.remove('active');
}

function showAddAccountModal() {
    document.getElementById('accountModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('accountModal').style.display = 'none';
    document.getElementById('new-account-name').value = '';
    document.getElementById('new-account-balance').value = '0';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    sidebar.classList.toggle('collapsed');
    if (mainContent) {
        mainContent.classList.toggle('expanded');
    }
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