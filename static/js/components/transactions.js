/**
 * Transaction management component
 */
class TransactionsComponent {
    static async loadTransactions() {
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
            
            const transactions = await API.getTransactions(filters);
            this.renderTransactionsList(transactions);
        } catch (error) {
            console.error('Error loading transactions:', error);
            UI.showNotification('Error loading transactions', 'error');
        }
    }

    static renderTransactionsList(transactions) {
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
                            onclick="TransactionsComponent.editTransaction(${t.id})">✏️</button>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" 
                            onclick="TransactionsComponent.deleteTransaction(${t.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    static async addTransaction() {
        try {
            // Get category value from input
            let category = document.getElementById('category').value;

            const data = {
                account_id: document.getElementById('account-select').value,
                amount: parseFloat(document.getElementById('amount').value),
                date: document.getElementById('date').value,
                type: document.getElementById('type').value,
                payee: document.getElementById('payee').value,
                category: category,
                notes: document.getElementById('notes').value,
                project: document.getElementById('project').value,
                is_recurring: document.getElementById('is-recurring').checked,
                frequency: document.getElementById('frequency').value,
                end_date: document.getElementById('end-date').value || null
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
            this.clearForm();
            AccountsComponent.loadAccounts();
            this.loadTransactions();
            RecurringComponent.loadRecurringTransactions();
            AnalyticsComponent.updateAnalytics();
            UI.showNotification('Transaction added successfully', 'success');
        } catch (error) {
            console.error('Error adding transaction:', error);
            UI.showNotification('Error adding transaction', 'error');
        }
    }

    static async editTransaction(id) {
        try {
            const transactions = await API.getTransactions();
            const transaction = transactions.find(t => t.id === id);

            if (!transaction) return;

            appState.setEditingTransaction(id);

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
                const accounts = await API.getAccounts();
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
    }

    static async updateTransaction() {
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
            AnalyticsComponent.updateAnalytics();
            UI.showNotification('Transaction updated successfully', 'success');
        } catch (error) {
            console.error('Error updating transaction:', error);
            UI.showNotification('Error updating transaction', 'error');
        }
    }

    static async deleteTransaction(id) {
        try {
            const confirmed = await UI.confirmAction('Are you sure you want to delete this transaction?');
            if (!confirmed) return;

            await API.deleteTransaction(id);
            AccountsComponent.loadAccounts();
            this.loadTransactions();
            AnalyticsComponent.updateAnalytics();
            UI.showNotification('Transaction deleted successfully', 'success');
        } catch (error) {
            console.error('Error deleting transaction:', error);
            UI.showNotification('Error deleting transaction', 'error');
        }
    }

    static toggleTransferFields() {
        const type = document.getElementById('type').value;
        UI.toggleVisibility('transfer-row', type === 'transfer');
    }

    static toggleEditTransferFields() {
        const type = document.getElementById('edit-transaction-type').value;
        UI.toggleVisibility('edit-transfer-row', type === 'transfer');
    }

    static toggleRecurring() {
        const checkbox = document.getElementById('is-recurring');
        const section = document.getElementById('recurring-section');
        if (section) {
            section.classList.toggle('active', checkbox.checked);
        }
    }

    static clearForm() {
        UI.clearForm();
        document.getElementById('date').valueAsDate = new Date();
        document.getElementById('type').value = 'expense';
        UI.toggleVisibility('transfer-row', false);
        UI.toggleVisibility('recurring-section', false);
    }

    static closeEditTransactionModal() {
        UI.hideModal('editTransactionModal');
        appState.clearEditingTransaction();
    }

    // Filter dropdown functions
    static toggleDateFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('date-filter-dropdown', true);
    }

    static toggleAccountFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('account-filter-dropdown', true);
    }

    static toggleCategoryFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('category-filter-dropdown', true);
    }

    static toggleTypeFilter() {
        this.hideAllFilterDropdowns();
        UI.toggleVisibility('type-filter-dropdown', true);
    }

    static hideAllFilterDropdowns() {
        const dropdowns = [
            'date-filter-dropdown',
            'account-filter-dropdown', 
            'category-filter-dropdown',
            'type-filter-dropdown'
        ];
        
        dropdowns.forEach(id => {
            UI.toggleVisibility(id, false);
        });
    }
}

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