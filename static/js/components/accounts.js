/**
 * Account management component
 */
const AccountsComponent = {
    async loadAccounts() {
        try {
            const accounts = await API.getAccounts();
            this.renderAccountsList(accounts);
            this.populateAccountSelects(accounts);
        } catch (error) {
            console.error('Error loading accounts:', error);
            UI.showNotification('Error loading accounts', 'error');
        }
    },

    renderAccountsList(accounts) {
        const accountsList = document.getElementById('accounts-list');
        if (!accountsList) return;

        accountsList.innerHTML = '';

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
                const div = document.createElement('div');
                div.className = 'account-item';
                if (account.id === appState.getCurrentAccount()) {
                    div.classList.add('active');
                }
                div.onclick = () => this.selectAccount(account.id);

                const amountElement = UI.createAmountElement(account.balance);
                
                div.innerHTML = `
                    <div>
                        <button class="btn-edit" onclick="editAccount(${account.id}, '${account.name}', '${account.type}'); event.stopPropagation();">✏️</button>
                    </div>
                    <span>${account.name}</span>
                    <div>
                        ${amountElement.outerHTML}
                    </div>
                `;
                accountsList.appendChild(div);
            });
        });
    },

    populateAccountSelects(accounts) {
        const selects = [
            { id: 'account-select', defaultOption: { value: '', text: 'All Accounts' } },
            { id: 'transaction-account-filter', defaultOption: { value: '', text: 'All Accounts' } },
            { id: 'edit-transaction-account' },
            { id: 'transfer-account', defaultOption: { value: '', text: 'Select destination account' } },
            { id: 'edit-transfer-account', defaultOption: { value: '', text: 'Select destination account' } }
        ];

        selects.forEach(selectConfig => {
            UI.populateSelect(
                selectConfig.id, 
                accounts, 
                'id', 
                'name', 
                selectConfig.defaultOption
            );
        });
    },

    selectAccount(accountId) {
        appState.setCurrentAccount(accountId);
        this.loadAccounts(); // Refresh to show active state
        TransactionsComponent.loadTransactions();
    },

    async showAddAccountModal() {
        UI.showModal('accountModal');
    },

    async addAccount() {
        try {
            const data = {
                name: document.getElementById('new-account-name').value,
                type: document.getElementById('new-account-type').value,
                balance: parseFloat(document.getElementById('new-account-balance').value) || 0
            };

            if (!data.name) {
                UI.showNotification('Please enter an account name', 'error');
                return;
            }

            await API.createAccount(data);
            this.closeModal();
            this.loadAccounts();
            UI.showNotification('Account created successfully', 'success');
        } catch (error) {
            console.error('Error creating account:', error);
            UI.showNotification('Error creating account', 'error');
        }
    },

    editAccount(id, name, type) {
        appState.setEditingAccount(id);
        document.getElementById('edit-account-name').value = name;
        document.getElementById('edit-account-type').value = type;
        UI.showModal('editAccountModal');
    },

    async updateAccount() {
        try {
            const editingId = appState.getEditingAccount();
            if (!editingId) return;

            const data = {
                name: document.getElementById('edit-account-name').value,
                type: document.getElementById('edit-account-type').value
            };

            if (!data.name) {
                UI.showNotification('Please enter an account name', 'error');
                return;
            }

            await API.updateAccount(editingId, data);
            this.closeEditModal();
            this.loadAccounts();
            UI.showNotification('Account updated successfully', 'success');
        } catch (error) {
            console.error('Error updating account:', error);
            UI.showNotification('Error updating account', 'error');
        }
    },

    closeModal() {
        UI.hideModal('accountModal');
        UI.clearForm('accountModal');
    },

    closeEditModal() {
        UI.hideModal('editAccountModal');
        appState.clearEditingAccount();
    }
};

// Global functions for HTML onclick handlers
window.showAddAccountModal = () => AccountsComponent.showAddAccountModal();
window.addAccount = () => AccountsComponent.addAccount();
window.closeModal = () => AccountsComponent.closeModal();
window.editAccount = (id, name, type) => AccountsComponent.editAccount(id, name, type);
window.updateAccount = () => AccountsComponent.updateAccount();
window.closeEditModal = () => AccountsComponent.closeEditModal();