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
        Utils.setInputToToday('date');

        // Load all data with better error handling
        const dataLoaders = [
            () => AccountsComponent.loadAccounts(),
            () => PayeesAndCategoriesComponent.loadPayees(),
            () => PayeesAndCategoriesComponent.loadCategories(),
            () => ProjectsComponent.loadProjectDropdown(),
            () => TransactionsComponent.loadTransactions(),
            () => loadRecurringTransactions(),
            () => AnalyticsManager.updateAnalytics(),
            () => getDatabaseInfo(),
            () => loadSettings(),
            () => UI.loadFontSize()
        ];
        
        // Load each with error handling - won't crash if one fails
        for (const loader of dataLoaders) {
            await ErrorHandler.safely(loader, null, loader.name || 'data loading');
        }

        // Load theme preference
        const savedTheme = Utils.loadFromStorage(Config.get('STORAGE.THEME'), Config.get('DEFAULTS.THEME'));
        setTheme(savedTheme);

        // Handle window resize for chart responsiveness
        window.addEventListener('resize', Utils.debounce(function() {
            appState.resizeCharts();
        }, Config.get('UI.DEBOUNCE_DELAY')));

        // Hide filter dropdowns when clicking outside
        document.addEventListener('click', function(event) {
            const filterHeaders = document.querySelectorAll('.filter-header');
            const filterDropdowns = document.querySelectorAll('.filter-dropdown');
            let clickedInsideFilter = false;
            
            // Check if clicked inside any filter header or dropdown
            filterHeaders.forEach(header => {
                if (header.contains(event.target)) {
                    clickedInsideFilter = true;
                }
            });
            
            filterDropdowns.forEach(dropdown => {
                if (dropdown.contains(event.target)) {
                    clickedInsideFilter = true;
                }
            });
            
            // Don't hide if clicking on filter buttons or filter inputs
            if (event.target.classList.contains('filter-btn') || 
                event.target.id.includes('filter') ||
                event.target.id.includes('transaction-date-')) {
                clickedInsideFilter = true;
            }
            
            if (!clickedInsideFilter && TransactionsComponent.hideAllFilterDropdowns) {
                TransactionsComponent.hideAllFilterDropdowns();
            }
        });

        console.log('App initialized successfully');
    } catch (error) {
        console.error('Error initializing app:', error);
        ErrorHandler.handleError(error, 'Application initialization');
    }
}

// Navigation functions
function switchTab(tab) {
    UI.setActiveTab(tab);
    
    if (tab === 'analytics') {
        AnalyticsManager.updateDateFilter();
    } else if (tab === 'settings') {
        getDatabaseInfo();
    } else if (tab === 'projects') {
        ProjectsComponent.loadProjects();
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
            list.innerHTML = '<p style="color: #6c757d; font-size: var(--base-font-size);">No recurring transactions set up yet.</p>';
            return;
        }

        recurring.forEach(r => {
            const div = document.createElement('div');
            div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #dee2e6;';
            
            const amountElement = UI.createAmountElement(r.amount);
            
            div.innerHTML = `
                <div>
                    <strong style="font-size: calc(var(--base-font-size) * 1.14);">${r.payee || 'Transaction'}</strong><span style="font-size: var(--base-font-size);"> - ${r.account_name}</span>
                    <br>
                    <small style="font-size: calc(var(--base-font-size) * 0.93);">${r.frequency} | ${r.category || 'No category'} | Next: ${r.next_date}${r.increment_amount ? ` | Inc: ${r.increment_amount > 0 ? '+' : ''}£${r.increment_amount.toFixed(2)}` : ''}</small>
                </div>
                <div>
                    ${amountElement.outerHTML}
                    <button class="btn btn-danger" style="margin-left: 10px; padding: 5px 10px; font-size: calc(var(--base-font-size) * 0.93);" 
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

// Analytics functions - now use the dedicated AnalyticsManager
async function updateAnalytics() {
    await AnalyticsManager.updateAnalytics();
}

function getAnalyticsFilters() {
    return ChartManager.getAnalyticsFilters();
}

async function updateCharts() {
    await ChartManager.updateAllCharts();
}

function updateDateFilter() {
    AnalyticsManager.updateDateFilter();
}

function navigateMonth(direction) {
    AnalyticsManager.navigateMonth(direction);
}

async function showCategoryDetails(category) {
    await ChartManager.showCategoryDetails(category);
}

function closeCategoryModal() {
    ChartManager.closeCategoryModal();
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
    try {
        UI.showNotification('Preparing database export...', 'info');
        
        // Create a proper download link with better browser support
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
        const filename = `money_tracker_backup_${timestamp}.db`;
        
        // Create and trigger download
        const link = document.createElement('a');
        link.href = '/api/export';
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        UI.showNotification('Database export started! Check your downloads folder.', 'success');
        
    } catch (error) {
        console.error('Export error:', error);
        UI.showNotification('Export failed: ' + error.message, 'error');
    }
}

async function exportCsv() {
    try {
        UI.showNotification('Preparing CSV export...', 'info');
        
        // Create a proper download link with better browser support
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
        const filename = `money_tracker_transactions_${timestamp}.csv`;
        
        // Create and trigger download
        const link = document.createElement('a');
        link.href = '/api/export/csv';
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        UI.showNotification('CSV export started! Check your downloads folder.', 'success');
        
    } catch (error) {
        console.error('CSV export error:', error);
        UI.showNotification('CSV export failed: ' + error.message, 'error');
    }
}

async function importData() {
    // Create file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.db,.sqlite,.sqlite3';
    fileInput.style.display = 'none';
    
    fileInput.onchange = async function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // Confirm with user since this will replace current data
        if (!confirm('This will replace your current database. Are you sure? This action cannot be undone.')) {
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            UI.showNotification('Importing database...', 'info');
            
            const response = await fetch('/api/import', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                UI.showNotification('Database imported successfully! Reloading page...', 'success');
                // Reload the page to refresh all data
                setTimeout(() => window.location.reload(), 1500);
            } else {
                UI.showNotification(result.error || 'Import failed', 'error');
            }
        } catch (error) {
            console.error('Import error:', error);
            UI.showNotification('Import failed: ' + error.message, 'error');
        } finally {
            // Clean up
            document.body.removeChild(fileInput);
        }
    };
    
    // Add to DOM and trigger click
    document.body.appendChild(fileInput);
    fileInput.click();
}

async function importCsv() {
    // Create file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.csv';
    fileInput.style.display = 'none';
    
    fileInput.onchange = async function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            UI.showNotification('Importing CSV...', 'info');
            
            const response = await fetch('/api/import/csv', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                UI.showNotification(`Successfully imported ${result.imported || 0} transactions`, 'success');
                // Reload transactions to show new data
                loadTransactions();
                loadAccounts();
            } else {
                UI.showNotification(result.error || 'CSV import failed', 'error');
            }
        } catch (error) {
            console.error('CSV import error:', error);
            UI.showNotification('CSV import failed: ' + error.message, 'error');
        } finally {
            // Clean up
            document.body.removeChild(fileInput);
        }
    };
    
    // Add to DOM and trigger click
    document.body.appendChild(fileInput);
    fileInput.click();
}

// Settings functions
async function loadSettings() {
    try {
        const settings = await API.getSettings();
        document.getElementById('database-path').value = settings.database_path || 'money_tracker.db';
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveDbLocation() {
    try {
        const dbPath = document.getElementById('database-path').value;
        if (!dbPath) {
            UI.showNotification('Please enter a database path', 'error');
            return;
        }
        
        await API.saveSettings({ database_path: dbPath });
        UI.showNotification('Database location saved. Restart the app to use the new location.', 'success');
    } catch (error) {
        console.error('Error saving database location:', error);
        UI.showNotification('Error saving database location', 'error');
    }
}

// Import functions would be implemented similarly...

// Theme functions
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || Config.get('DEFAULTS.THEME');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    Utils.saveToStorage(Config.get('STORAGE.THEME'), newTheme);
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
window.loadSettings = loadSettings;
window.saveDbLocation = saveDbLocation;
window.toggleTheme = toggleTheme;
window.toggleSidebar = toggleSidebar;