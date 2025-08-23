/**
 * Main application initialization and global functions
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    try {
        // Set default date
        const dateInput = document.getElementById('date');
        if (dateInput) {
            dateInput.valueAsDate = new Date();
        }

        // Load all data
        await Promise.all([
            AccountsComponent.loadAccounts(),
            PayeesAndCategoriesComponent.loadPayees(),
            PayeesAndCategoriesComponent.loadCategories(),
            TransactionsComponent.loadTransactions(),
            loadRecurringTransactions(),
            updateAnalytics(),
            getDatabaseInfo()
        ]);

        // Load theme preference
        const savedTheme = localStorage.getItem('theme') || 'light';
        setTheme(savedTheme);

        // Handle window resize for chart responsiveness
        window.addEventListener('resize', UI.debounce(function() {
            appState.resizeCharts();
        }, 250));

        // Hide filter dropdowns when clicking outside
        document.addEventListener('click', function(event) {
            const filterHeaders = document.querySelectorAll('.filter-header');
            let clickedInsideFilter = false;
            
            filterHeaders.forEach(header => {
                if (header.contains(event.target)) {
                    clickedInsideFilter = true;
                }
            });
            
            if (!clickedInsideFilter && TransactionsComponent.hideAllFilterDropdowns) {
                TransactionsComponent.hideAllFilterDropdowns();
            }
        });

        console.log('App initialized successfully');
    } catch (error) {
        console.error('Error initializing app:', error);
        UI.showNotification('Error initializing application', 'error');
    }
}

// Navigation functions
function switchTab(tab) {
    UI.setActiveTab(tab);
    
    if (tab === 'analytics') {
        updateDateFilter();
    } else if (tab === 'settings') {
        getDatabaseInfo();
    }
}

// Recurring transactions functions
async function loadRecurringTransactions() {
    try {
        const recurring = await API.getRecurringTransactions();
        const list = document.getElementById('recurring-list');
        if (!list) return;

        list.innerHTML = '';
        if (recurring.length === 0) {
            list.innerHTML = '<p style="color: #6c757d;">No recurring transactions set up yet.</p>';
            return;
        }

        recurring.forEach(r => {
            const div = document.createElement('div');
            div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #dee2e6;';
            
            const amountElement = UI.createAmountElement(r.amount);
            
            div.innerHTML = `
                <div>
                    <strong>${r.payee || 'Transaction'}</strong> - ${r.account_name}
                    <br>
                    <small>${r.frequency} | ${r.category || 'No category'} | Next: ${r.next_date}</small>
                </div>
                <div>
                    ${amountElement.outerHTML}
                    <button class="btn btn-danger" style="margin-left: 10px; padding: 5px 10px; font-size: 12px;" 
                            onclick="deleteRecurring(${r.id})">Delete</button>
                </div>
            `;
            list.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading recurring transactions:', error);
        UI.showNotification('Error loading recurring transactions', 'error');
    }
}

async function deleteRecurring(id) {
    try {
        const confirmed = await UI.confirmAction('Are you sure you want to delete this recurring transaction?');
        if (!confirmed) return;

        await API.deleteRecurringTransaction(id);
        loadRecurringTransactions();
        UI.showNotification('Recurring transaction deleted successfully', 'success');
    } catch (error) {
        console.error('Error deleting recurring transaction:', error);
        UI.showNotification('Error deleting recurring transaction', 'error');
    }
}

async function processRecurring() {
    try {
        const result = await API.processRecurringTransactions();
        UI.showNotification(result.message, 'info');
        
        if (result.processed > 0) {
            AccountsComponent.loadAccounts();
            TransactionsComponent.loadTransactions();
            updateAnalytics();
        }
    } catch (error) {
        console.error('Error processing recurring transactions:', error);
        UI.showNotification('Error processing recurring transactions', 'error');
    }
}

// Analytics functions (simplified versions - full implementation would be in separate component)
async function updateAnalytics() {
    try {
        const filters = getAnalyticsFilters();
        const stats = await API.getAnalyticsStats(filters);
        
        document.getElementById('total-balance').textContent = UI.formatCurrency(stats.total_balance);
        document.getElementById('monthly-income').textContent = UI.formatCurrency(stats.monthly_income);
        document.getElementById('monthly-expenses').textContent = UI.formatCurrency(stats.monthly_expenses);
        document.getElementById('net-monthly').textContent = UI.formatCurrency(stats.net_monthly);
        
        updateCharts();
    } catch (error) {
        console.error('Error updating analytics:', error);
    }
}

function getAnalyticsFilters() {
    const filters = {};
    
    // Get selected account types
    const accountTypeChecks = document.querySelectorAll('#account-type-filters input[type="checkbox"]:checked');
    const selectedTypes = Array.from(accountTypeChecks).map(cb => cb.value);
    if (selectedTypes.length > 0) {
        // Flask expects multiple values for the same key as separate parameters
        selectedTypes.forEach(type => {
            if (!filters['account_types']) filters['account_types'] = [];
            filters['account_types'].push(type);
        });
    }
    
    // Get date range
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    
    if (startDate) filters['start_date'] = startDate;
    if (endDate) filters['end_date'] = endDate;
    
    return filters;
}

async function updateCharts() {
    try {
        const filters = getAnalyticsFilters();
        const chartData = await API.getAnalyticsCharts(filters);
        
        console.log('Chart data received:', chartData); // Debug log
        
        // Destroy existing charts
        appState.destroyAllCharts();
        
        // Category Chart (Pie/Doughnut)
        if (chartData.category && chartData.category.labels && chartData.category.labels.length > 0) {
            const ctx1 = document.getElementById('categoryChart')?.getContext('2d');
            if (ctx1) {
                const categoryChart = new Chart(ctx1, {
                    type: 'doughnut',
                    data: chartData.category,
                    options: { 
                        responsive: true, 
                        maintainAspectRatio: false,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const category = chartData.category.labels[index];
                                showCategoryDetails(category);
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    font: {
                                        size: 14
                                    },
                                    boxWidth: 12
                                }
                            }
                        }
                    }
                });
                appState.setChart('category', categoryChart);
            }
        }
        
        // Trend Chart (Line)
        if (chartData.trend && chartData.trend.labels && chartData.trend.labels.length > 0) {
            const ctx2 = document.getElementById('trendChart')?.getContext('2d');
            if (ctx2) {
                const trendChart = new Chart(ctx2, {
                    type: 'line',
                    data: chartData.trend,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { 
                            x: {
                                ticks: {
                                    font: {
                                        size: 14
                                    }
                                }
                            },
                            y: { 
                                beginAtZero: true,
                                ticks: {
                                    font: {
                                        size: 14
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    font: {
                                        size: 14
                                    }
                                }
                            }
                        }
                    }
                });
                appState.setChart('trend', trendChart);
            }
        }
        
        // Account Chart (Bar)
        if (chartData.accounts && chartData.accounts.labels && chartData.accounts.labels.length > 0) {
            const ctx3 = document.getElementById('accountChart')?.getContext('2d');
            if (ctx3) {
                const accountChart = new Chart(ctx3, {
                    type: 'bar',
                    data: chartData.accounts,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { 
                            x: {
                                ticks: {
                                    font: {
                                        size: 14
                                    }
                                }
                            },
                            y: { 
                                beginAtZero: true,
                                ticks: {
                                    font: {
                                        size: 14
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    font: {
                                        size: 14
                                    }
                                }
                            }
                        }
                    }
                });
                appState.setChart('account', accountChart);
            }
        }
        
        // Category Trends Chart (Stacked Bar)
        if (chartData.category_trends && chartData.category_trends.labels.length > 0) {
            const ctx4 = document.getElementById('categoryTrendsChart')?.getContext('2d');
            if (ctx4) {
                // Remove alpha from colors
                const datasetsWithoutAlpha = chartData.category_trends.datasets.map(dataset => ({
                    ...dataset,
                    backgroundColor: dataset.borderColor,
                    borderWidth: 1
                }));
                
                const categoryTrendsChart = new Chart(ctx4, {
                    type: 'bar',
                    data: {
                        ...chartData.category_trends,
                        datasets: datasetsWithoutAlpha
                    },
                    options: { 
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { 
                            x: { 
                                stacked: true,
                                ticks: {
                                    font: {
                                        size: 14
                                    }
                                }
                            },
                            y: { 
                                stacked: true,
                                beginAtZero: true,
                                ticks: {
                                    font: {
                                        size: 14
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'bottom',
                                labels: {
                                    font: {
                                        size: 14
                                    }
                                }
                            }
                        }
                    }
                });
                appState.setChart('categoryTrends', categoryTrendsChart);
            }
        }
        
    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

function updateDateFilter() {
    const period = document.getElementById('date-period')?.value;
    if (!period) return;
    
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    const prevBtn = document.getElementById('prev-month');
    const nextBtn = document.getElementById('next-month');
    const currentPeriodSpan = document.getElementById('current-period');
    
    if (!startDate || !endDate) return;
    
    // Reset
    startDate.disabled = true;
    endDate.disabled = true;
    if (prevBtn) prevBtn.style.display = 'none';
    if (nextBtn) nextBtn.style.display = 'none';
    
    const now = new Date();
    let start, end;
    
    if (period === 'custom') {
        startDate.disabled = false;
        endDate.disabled = false;
        if (currentPeriodSpan) currentPeriodSpan.textContent = 'Custom Range';
        return;
    }
    
    if (period === 'current_month' || period === 'last_month') {
        if (prevBtn) prevBtn.style.display = 'inline-block';
        if (nextBtn) nextBtn.style.display = 'inline-block';
    }
    
    switch (period) {
        case 'current_month':
            const currentMonth = appState.getAnalyticsMonth();
            start = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
            end = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
            if (currentPeriodSpan) {
                currentPeriodSpan.textContent = currentMonth.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
            }
            break;
        case 'last_month':
            const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            start = lastMonth;
            end = new Date(now.getFullYear(), now.getMonth(), 0);
            if (currentPeriodSpan) {
                currentPeriodSpan.textContent = lastMonth.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
            }
            break;
        case 'last_3_months':
            start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
            end = now;
            if (currentPeriodSpan) currentPeriodSpan.textContent = 'Last 3 Months';
            break;
        case 'last_6_months':
            start = new Date(now.getFullYear(), now.getMonth() - 6, 1);
            end = now;
            if (currentPeriodSpan) currentPeriodSpan.textContent = 'Last 6 Months';
            break;
        case 'this_year':
            start = new Date(now.getFullYear(), 0, 1);
            end = now;
            if (currentPeriodSpan) currentPeriodSpan.textContent = now.getFullYear().toString();
            break;
    }
    
    if (start && end) {
        startDate.value = start.toISOString().split('T')[0];
        endDate.value = end.toISOString().split('T')[0];
    }
    
    updateAnalytics();
}

function navigateMonth(direction) {
    appState.navigateAnalyticsMonth(direction);
    updateDateFilter();
}

async function showCategoryDetails(category) {
    try {
        const filters = getAnalyticsFilters();
        const transactions = await API.getCategoryTransactions(category, filters);
        
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
                const amountElement = UI.createAmountElement(t.amount);
                tableHtml += `
                    <tr>
                        <td>${t.date}</td>
                        <td>${t.account_name}</td>
                        <td>${t.payee || '-'}</td>
                        <td>${amountElement.outerHTML}</td>
                        <td>${t.notes || '-'}</td>
                    </tr>
                `;
            });
            
            tableHtml += '</tbody></table>';
            tableContainer.innerHTML = tableHtml;
        }
        
        UI.showModal('categoryDetailsModal');
    } catch (error) {
        console.error('Error showing category details:', error);
        UI.showNotification('Error loading category details', 'error');
    }
}

function closeCategoryModal() {
    UI.hideModal('categoryDetailsModal');
}

// Database functions
async function getDatabaseInfo() {
    try {
        const info = await API.getDatabaseInfo();
        document.getElementById('db-size').textContent = `Size: ${info.size}`;
    } catch (error) {
        console.error('Error getting database info:', error);
    }
}

async function exportData() {
    window.location.href = '/api/export';
}

async function exportCsv() {
    window.location.href = '/api/export/csv';
}

// Import functions would be implemented similarly...

// Theme functions
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

// Sidebar functions
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    if (sidebar) sidebar.classList.toggle('collapsed');
    if (mainContent) mainContent.classList.toggle('expanded');
}

// Global exports for HTML handlers
window.switchTab = switchTab;
window.loadRecurringTransactions = loadRecurringTransactions;
window.deleteRecurring = deleteRecurring;
window.processRecurring = processRecurring;
window.updateAnalytics = updateAnalytics;
window.updateDateFilter = updateDateFilter;
window.navigateMonth = navigateMonth;
window.showCategoryDetails = showCategoryDetails;
window.closeCategoryModal = closeCategoryModal;
window.exportData = exportData;
window.exportCsv = exportCsv;
window.toggleTheme = toggleTheme;
window.toggleSidebar = toggleSidebar;