/**
 * Transaction management component
 */
const TransactionsComponent = {
    lastTransactionDate: null,
    lastTransactionAccount: null,
    
    async loadTransactions() {
        try {
            // Build query parameters
            const filters = {};
            
            // Account filter (either from sidebar or filter dropdown)
            const accountFilter = document.getElementById('transaction-account-filter');
            const selectedAccount = accountFilter ? accountFilter.value : '';
            
            if (appState.getCurrentAccount()) {
                filters.account_id = appState.getCurrentAccount();
            } else if (selectedAccount) {
                filters.account_id = selectedAccount;
            }
            
            // Other filters
            const categoryFilter = document.getElementById('transaction-category-filter');
            if (categoryFilter && categoryFilter.value) {
                filters.category = categoryFilter.value;
            }
            
            const typeFilter = document.getElementById('transaction-type-filter');
            if (typeFilter && typeFilter.value) {
                filters.type = typeFilter.value;
            }
            
            const dateFrom = document.getElementById('transaction-date-from');
            if (dateFrom && dateFrom.value) {
                filters.date_from = dateFrom.value;
            }
            
            const dateTo = document.getElementById('transaction-date-to');
            if (dateTo && dateTo.value) {
                filters.date_to = dateTo.value;
            }
            
            const searchInput = document.getElementById('transaction-search');
            if (searchInput && searchInput.value.trim()) {
                filters.search = searchInput.value.trim();
            }
            
            const transactions = await API.getTransactions(filters);
            this.renderTransactionsList(transactions);
        } catch (error) {
            console.error('Error loading transactions:', error);
            UI.showNotification('Error loading transactions', 'error');
        }
    },

    renderTransactionsList(transactions) {
        const tbody = document.getElementById('transactions-list');
        if (!tbody) return;

        tbody.innerHTML = '';
        
        transactions.forEach(t => {
            const tr = document.createElement('tr');
            const recurring = t.frequency ? `<span class="recurring-badge">${t.frequency}</span>` : '';
            const amountElement = UI.createAmountElement(t.amount);
            
            tr.innerHTML = `
                <td>${t.date}</td>
                <td>${t.account_name}</td>
                <td>${t.payee || '-'}${recurring}</td>
                <td>${t.category || '-'}</td>
                <td>${amountElement.outerHTML}</td>
                <td>${t.type}</td>
                <td>${t.notes || '-'}</td>
                <td>${t.project || '-'}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 5px 8px; font-size: 12px; margin-right: 5px;" 
                            onclick="editTransaction(${t.id})">✏️</button>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" 
                            onclick="deleteTransaction(${t.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    async addTransaction() {
        try {
            // Get category value from input
            let category = document.getElementById('category').value;

            // Get recurring data from modal (if it was opened)
            const isRecurringCheckbox = document.getElementById('modal-is-recurring');
            const isRecurring = isRecurringCheckbox ? isRecurringCheckbox.checked : false;
            
            const data = {
                account_id: document.getElementById('account-select').value,
                amount: parseFloat(document.getElementById('amount').value),
                date: document.getElementById('date').value,
                type: document.getElementById('type').value,
                payee: document.getElementById('payee').value,
                category: category,
                notes: document.getElementById('notes').value,
                project: document.getElementById('project').value,
                is_recurring: isRecurring,
                frequency: isRecurring ? document.getElementById('modal-frequency').value : null,
                end_date: isRecurring ? (document.getElementById('modal-end-date').value || null) : null,
                increment_amount: isRecurring ? (parseFloat(document.getElementById('modal-increment-amount').value) || 0) : 0
            };

            if (!data.account_id || !data.amount || !data.date) {
                UI.showNotification('Please fill in required fields: Account, Amount, and Date', 'error');
                return;
            }

            // Handle transfer
            if (data.type === 'transfer') {
                const transferAccountId = document.getElementById('transfer-account').value;
                if (!transferAccountId) {
                    UI.showNotification('Please select a destination account for the transfer', 'error');
                    return;
                }
                data.transfer_account_id = transferAccountId;
                
                // Set payee to destination account name
                const accounts = await API.getAccounts();
                const destAccount = accounts.find(a => a.id == transferAccountId);
                data.payee = destAccount ? destAccount.name : 'Transfer';
            } else if (data.type === 'expense') {
                data.amount = -Math.abs(data.amount);
            } else {
                data.amount = Math.abs(data.amount);
            }

            await API.createTransaction(data);
            
            // Store the date and account for reuse
            this.lastTransactionDate = data.date;
            this.lastTransactionAccount = data.account_id;
            
            try {
                this.clearForm();
            } catch (error) {
                console.error('Error clearing form:', error);
            }
            
            // Refresh UI components with individual error handling
            try {
                await AccountsComponent.loadAccounts();
            } catch (error) {
                console.error('Error refreshing accounts:', error);
            }
            
            try {
                await this.loadTransactions();
            } catch (error) {
                console.error('Error refreshing transactions:', error);
            }
            
            try {
                await loadRecurringTransactions();
            } catch (error) {
                console.error('Error refreshing recurring transactions:', error);
            }
            
            try {
                await updateAnalytics();
            } catch (error) {
                console.error('Error refreshing analytics:', error);
            }
            
            // Transaction added successfully - no notification needed
        } catch (error) {
            console.error('Error adding transaction:', error);
            const errorMessage = error.message || 'Unknown error occurred';
            UI.showNotification(`Error adding transaction: ${errorMessage}`, 'error');
        }
    },

    async editTransaction(id) {
        try {
            // Get ALL transactions, not filtered ones
            const transactions = await API.getTransactions({limit: 10000});
            const transaction = transactions.find(t => t.id === id);

            if (!transaction) {
                UI.showNotification('Transaction not found', 'error');
                return;
            }

            appState.setEditingTransaction(id);

            // Ensure account select is populated
            const accounts = await API.getAccounts();
            UI.populateSelect('edit-transaction-account', accounts, 'id', 'name');
            UI.populateSelect('edit-transfer-account', accounts, 'id', 'name', { value: '', text: 'Select destination account' });

            // Populate form
            document.getElementById('edit-transaction-account').value = transaction.account_id;
            document.getElementById('edit-transaction-amount').value = Math.abs(transaction.amount);
            document.getElementById('edit-transaction-date').value = transaction.date;
            document.getElementById('edit-transaction-type').value = transaction.type;
            document.getElementById('edit-transaction-payee').value = transaction.payee || '';
            document.getElementById('edit-transaction-category').value = transaction.category || '';
            document.getElementById('edit-transaction-notes').value = transaction.notes || '';
            document.getElementById('edit-transaction-project').value = transaction.project || '';

            // Handle transfer fields
            if (transaction.type === 'transfer') {
                const destAccount = accounts.find(a => a.name === transaction.payee);
                if (destAccount) {
                    document.getElementById('edit-transfer-account').value = destAccount.id;
                }
                this.toggleEditTransferFields();
            }

            UI.showModal('editTransactionModal');
        } catch (error) {
            console.error('Error loading transaction for editing:', error);
            UI.showNotification('Error loading transaction', 'error');
        }
    },

    async updateTransaction() {
        try {
            const editingId = appState.getEditingTransaction();
            if (!editingId) return;

            // Get category value from input
            let category = document.getElementById('edit-transaction-category').value;

            const data = {
                account_id: parseInt(document.getElementById('edit-transaction-account').value),
                amount: parseFloat(document.getElementById('edit-transaction-amount').value),
                date: document.getElementById('edit-transaction-date').value,
                type: document.getElementById('edit-transaction-type').value,
                payee: document.getElementById('edit-transaction-payee').value,
                category: category,
                notes: document.getElementById('edit-transaction-notes').value,
                project: document.getElementById('edit-transaction-project').value
            };

            if (!data.account_id || !data.amount || !data.date) {
                UI.showNotification('Please fill in required fields: Account, Amount, and Date', 'error');
                return;
            }

            // Handle transfer
            if (data.type === 'transfer') {
                const transferAccountId = document.getElementById('edit-transfer-account').value;
                if (!transferAccountId) {
                    UI.showNotification('Please select a destination account for the transfer', 'error');
                    return;
                }
                data.transfer_account_id = transferAccountId;
                
                // Set payee to destination account name
                const accounts = await API.getAccounts();
                const destAccount = accounts.find(a => a.id == transferAccountId);
                data.payee = destAccount ? destAccount.name : 'Transfer';
            }

            await API.updateTransaction(editingId, data);
            this.closeEditTransactionModal();
            AccountsComponent.loadAccounts();
            this.loadTransactions();
            updateAnalytics();
            // Transaction updated successfully - no notification needed
        } catch (error) {
            console.error('Error updating transaction:', error);
            const errorMessage = error.message || 'Unknown error occurred';
            UI.showNotification(`Error updating transaction: ${errorMessage}`, 'error');
        }
    },

    async deleteTransaction(id) {
        try {
            const confirmed = await UI.confirmAction('Are you sure you want to delete this transaction?');
            if (!confirmed) return;

            await API.deleteTransaction(id);
            AccountsComponent.loadAccounts();
            this.loadTransactions();
            updateAnalytics();
            UI.showNotification('Transaction deleted successfully', 'success');
        } catch (error) {
            console.error('Error deleting transaction:', error);
            UI.showNotification('Error deleting transaction', 'error');
        }
    },

    toggleTransferFields() {
        const type = document.getElementById('type').value;
        UI.toggleVisibility('transfer-row', type === 'transfer');
    },

    toggleEditTransferFields() {
        const type = document.getElementById('edit-transaction-type').value;
        UI.toggleVisibility('edit-transfer-row', type === 'transfer');
    },

    toggleRecurring() {
        const checkbox = document.getElementById('is-recurring');
        const section = document.getElementById('recurring-section');
        if (section) {
            section.classList.toggle('active', checkbox.checked);
        }
    },

    clearForm() {
        UI.clearForm();
        
        // Use last transaction date if available, otherwise use today
        const dateInput = document.getElementById('date');
        if (this.lastTransactionDate) {
            dateInput.value = this.lastTransactionDate;
        } else {
            dateInput.valueAsDate = new Date();
        }
        
        // Use last transaction account if available
        const accountSelect = document.getElementById('account-select');
        if (this.lastTransactionAccount && accountSelect) {
            accountSelect.value = this.lastTransactionAccount;
        }
        
        document.getElementById('type').value = 'expense';
        UI.toggleVisibility('transfer-row', false);
        
        // Reset recurring section - since UI.clearForm() unchecks is-recurring, 
        // we need to remove the 'active' class from the section
        const recurringSection = document.getElementById('recurring-section');
        if (recurringSection) {
            recurringSection.classList.remove('active');
        }
    },

    closeEditTransactionModal() {
        UI.hideModal('editTransactionModal');
        appState.clearEditingTransaction();
    },

    // Filter dropdown functions
    toggleDateFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('date-filter-dropdown', true);
    },

    toggleAccountFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('account-filter-dropdown', true);
    },

    toggleCategoryFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('category-filter-dropdown', true);
    },

    toggleTypeFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('type-filter-dropdown', true);
    },

    hideAllFilterDropdowns() {
        const dropdowns = [
            'date-filter-dropdown',
            'account-filter-dropdown', 
            'category-filter-dropdown',
            'type-filter-dropdown'
        ];
        
        dropdowns.forEach(id => {
            UI.toggleVisibility(id, false);
        });
    },

    clearSearch() {
        const searchInput = document.getElementById('transaction-search');
        if (searchInput) {
            searchInput.value = '';
            this.loadTransactions();
        }
    },

    showRecurringModal() {
        const modal = document.getElementById('recurringModal');
        if (modal) {
            modal.style.display = 'block';
        }
    },

    closeRecurringModal() {
        const modal = document.getElementById('recurringModal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    toggleRecurringOptions() {
        const checkbox = document.getElementById('modal-is-recurring');
        const section = document.getElementById('modal-recurring-section');
        if (checkbox && section) {
            section.style.display = checkbox.checked ? 'block' : 'none';
        }
    }
};

// Global functions for HTML onclick handlers
window.addTransaction = () => TransactionsComponent.addTransaction();
window.deleteTransaction = (id) => TransactionsComponent.deleteTransaction(id);
window.editTransaction = (id) => TransactionsComponent.editTransaction(id);
window.updateTransaction = () => TransactionsComponent.updateTransaction();
window.toggleTransferFields = () => TransactionsComponent.toggleTransferFields();
window.toggleEditTransferFields = () => TransactionsComponent.toggleEditTransferFields();
window.toggleRecurring = () => TransactionsComponent.toggleRecurring();
window.clearForm = () => TransactionsComponent.clearForm();
window.closeEditTransactionModal = () => TransactionsComponent.closeEditTransactionModal();
window.loadTransactions = () => TransactionsComponent.loadTransactions();

// Filter toggle functions
window.toggleDateFilter = () => TransactionsComponent.toggleDateFilter();
window.toggleAccountFilter = () => TransactionsComponent.toggleAccountFilter();
window.toggleCategoryFilter = () => TransactionsComponent.toggleCategoryFilter();
window.toggleTypeFilter = () => TransactionsComponent.toggleTypeFilter();

// Search functions
let searchTimeout;
window.debounceSearch = () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        TransactionsComponent.loadTransactions();
    }, 300);
};
window.clearSearch = () => TransactionsComponent.clearSearch();

// Recurring modal functions
window.showRecurringModal = () => TransactionsComponent.showRecurringModal();
window.closeRecurringModal = () => TransactionsComponent.closeRecurringModal();
window.toggleRecurringOptions = () => TransactionsComponent.toggleRecurringOptions();