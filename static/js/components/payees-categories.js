/**
 * Payees and Categories component
 */
class PayeesAndCategoriesComponent {
    static async loadPayees() {
        try {
            const payees = await API.getPayees();
            appState.setPayees(payees);
        } catch (error) {
            console.error('Error loading payees:', error);
        }
    }

    static async loadCategories() {
        try {
            const categories = await API.getCategories();
            appState.setCategories(categories);
            this.populateCategorySelects(categories);
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    static populateCategorySelects(categories) {
        // Only populate the filter dropdown, as the input fields are handled by search dropdowns
        const filterSelect = document.getElementById('transaction-category-filter');
        if (filterSelect) {
            const currentValue = filterSelect.value;
            filterSelect.innerHTML = '<option value="">All Categories</option>';
            
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                filterSelect.appendChild(option);
            });
            
            if (currentValue) {
                filterSelect.value = currentValue;
            }
        }
    }

    // Payee dropdown functionality
    static showPayeeDropdown() {
        appState.clearDropdownTimeout();
        this.populatePayeeDropdown('');
        document.getElementById('payee-dropdown').style.display = 'block';
    }

    static hidePayeeDropdown() {
        const timeout = setTimeout(() => {
            document.getElementById('payee-dropdown').style.display = 'none';
        }, 200);
        appState.setDropdownTimeout(timeout);
    }

    static showEditPayeeDropdown() {
        appState.clearDropdownTimeout();
        this.populateEditPayeeDropdown('');
        document.getElementById('edit-payee-dropdown').style.display = 'block';
    }

    static hideEditPayeeDropdown() {
        const timeout = setTimeout(() => {
            document.getElementById('edit-payee-dropdown').style.display = 'none';
        }, 200);
        appState.setDropdownTimeout(timeout);
    }

    static filterPayees() {
        const input = document.getElementById('payee');
        const filter = input.value.toLowerCase();
        this.populatePayeeDropdown(filter);
    }

    static filterEditPayees() {
        const input = document.getElementById('edit-transaction-payee');
        const filter = input.value.toLowerCase();
        this.populateEditPayeeDropdown(filter);
    }

    static populatePayeeDropdown(filter) {
        const dropdown = document.getElementById('payee-dropdown');
        dropdown.innerHTML = '';

        const payees = appState.getPayees();
        const accountPayees = payees.filter(p => p.is_account && p.name.toLowerCase().includes(filter));
        const regularPayees = payees.filter(p => !p.is_account && p.name.toLowerCase().includes(filter));

        // Add account payees
        accountPayees.forEach(payee => {
            const item = document.createElement('div');
            item.className = 'dropdown-item transfer';
            item.textContent = `${payee.name} (Transfer)`;
            item.onclick = () => this.selectPayee(payee.name, true, payee.account_id);
            dropdown.appendChild(item);
        });

        if (accountPayees.length > 0 && regularPayees.length > 0) {
            const separator = document.createElement('div');
            separator.className = 'dropdown-item separator';
            separator.textContent = '────────────';
            dropdown.appendChild(separator);
        }

        // Add regular payees
        regularPayees.forEach(payee => {
            const item = document.createElement('div');
            item.className = 'dropdown-item';
            item.textContent = payee.name;
            item.onclick = () => this.selectPayee(payee.name, false);
            dropdown.appendChild(item);
        });

        // Add new payee option
        const addNew = document.createElement('div');
        addNew.className = 'dropdown-item add-new';
        addNew.textContent = '+ Add New Payee';
        addNew.onclick = () => this.addNewPayee();
        dropdown.appendChild(addNew);
    }

    static populateEditPayeeDropdown(filter) {
        const dropdown = document.getElementById('edit-payee-dropdown');
        dropdown.innerHTML = '';

        const payees = appState.getPayees();
        const accountPayees = payees.filter(p => p.is_account && p.name.toLowerCase().includes(filter));
        const regularPayees = payees.filter(p => !p.is_account && p.name.toLowerCase().includes(filter));

        // Add account payees
        accountPayees.forEach(payee => {
            const item = document.createElement('div');
            item.className = 'dropdown-item transfer';
            item.textContent = `${payee.name} (Transfer)`;
            item.onclick = () => this.selectEditPayee(payee.name, true, payee.account_id);
            dropdown.appendChild(item);
        });

        if (accountPayees.length > 0 && regularPayees.length > 0) {
            const separator = document.createElement('div');
            separator.className = 'dropdown-item separator';
            separator.textContent = '────────────';
            dropdown.appendChild(separator);
        }

        // Add regular payees
        regularPayees.forEach(payee => {
            const item = document.createElement('div');
            item.className = 'dropdown-item';
            item.textContent = payee.name;
            item.onclick = () => this.selectEditPayee(payee.name, false);
            dropdown.appendChild(item);
        });

        // Add new payee option
        const addNew = document.createElement('div');
        addNew.className = 'dropdown-item add-new';
        addNew.textContent = '+ Add New Payee';
        addNew.onclick = () => this.addNewEditPayee();
        dropdown.appendChild(addNew);
    }

    static selectPayee(name, isAccount, accountId = null) {
        const payeeInput = document.getElementById('payee');
        const typeSelect = document.getElementById('type');
        const transferAccount = document.getElementById('transfer-account');

        payeeInput.value = name;

        if (isAccount) {
            typeSelect.value = 'transfer';
            transferAccount.value = accountId;
            UI.toggleVisibility('transfer-row', true);
        } else if (typeSelect.value === 'transfer') {
            typeSelect.value = 'expense';
            UI.toggleVisibility('transfer-row', false);
        }

        document.getElementById('payee-dropdown').style.display = 'none';
    }

    static selectEditPayee(name, isAccount, accountId = null) {
        const payeeInput = document.getElementById('edit-transaction-payee');
        const typeSelect = document.getElementById('edit-transaction-type');
        const transferAccount = document.getElementById('edit-transfer-account');

        payeeInput.value = name;

        if (isAccount) {
            typeSelect.value = 'transfer';
            transferAccount.value = accountId;
            UI.toggleVisibility('edit-transfer-row', true);
        } else if (typeSelect.value === 'transfer') {
            typeSelect.value = 'expense';
            UI.toggleVisibility('edit-transfer-row', false);
        }

        document.getElementById('edit-payee-dropdown').style.display = 'none';
    }

    static async addNewPayee() {
        const newPayee = await UI.getUserInput('Enter new payee name:');
        if (newPayee) {
            try {
                await API.createPayee({ name: newPayee });
                await this.loadPayees();
                document.getElementById('payee').value = newPayee;
                document.getElementById('payee-dropdown').style.display = 'none';
            } catch (error) {
                console.error('Error creating payee:', error);
                UI.showNotification('Error creating payee', 'error');
            }
        } else {
            document.getElementById('payee-dropdown').style.display = 'none';
        }
    }

    static async addNewEditPayee() {
        const newPayee = await UI.getUserInput('Enter new payee name:');
        if (newPayee) {
            try {
                await API.createPayee({ name: newPayee });
                await this.loadPayees();
                document.getElementById('edit-transaction-payee').value = newPayee;
                document.getElementById('edit-payee-dropdown').style.display = 'none';
            } catch (error) {
                console.error('Error creating payee:', error);
                UI.showNotification('Error creating payee', 'error');
            }
        } else {
            document.getElementById('edit-payee-dropdown').style.display = 'none';
        }
    }

    // Category dropdown functionality
    static showCategoryDropdown() {
        appState.clearDropdownTimeout();
        this.populateCategoryDropdown('');
        document.getElementById('category-dropdown').style.display = 'block';
    }

    static hideCategoryDropdown() {
        const timeout = setTimeout(() => {
            document.getElementById('category-dropdown').style.display = 'none';
        }, 200);
        appState.setDropdownTimeout(timeout);
    }

    static showEditCategoryDropdown() {
        appState.clearDropdownTimeout();
        this.populateEditCategoryDropdown('');
        document.getElementById('edit-category-dropdown').style.display = 'block';
    }

    static hideEditCategoryDropdown() {
        const timeout = setTimeout(() => {
            document.getElementById('edit-category-dropdown').style.display = 'none';
        }, 200);
        appState.setDropdownTimeout(timeout);
    }

    static filterCategories() {
        const input = document.getElementById('category');
        const filter = input.value.toLowerCase();
        this.populateCategoryDropdown(filter);
    }

    static filterEditCategories() {
        const input = document.getElementById('edit-transaction-category');
        const filter = input.value.toLowerCase();
        this.populateEditCategoryDropdown(filter);
    }

    static populateCategoryDropdown(filter) {
        const dropdown = document.getElementById('category-dropdown');
        dropdown.innerHTML = '';

        const categories = appState.getCategories();
        const filteredCategories = categories.filter(category => 
            category.toLowerCase().includes(filter)
        );

        // Add filtered categories
        filteredCategories.forEach(category => {
            const item = document.createElement('div');
            item.className = 'dropdown-item';
            item.textContent = category;
            item.onclick = () => this.selectCategory(category);
            dropdown.appendChild(item);
        });

        // Add new category option
        const addNew = document.createElement('div');
        addNew.className = 'dropdown-item add-new';
        addNew.textContent = '+ Add New Category';
        addNew.onclick = () => this.addNewCategory();
        dropdown.appendChild(addNew);
    }

    static populateEditCategoryDropdown(filter) {
        const dropdown = document.getElementById('edit-category-dropdown');
        dropdown.innerHTML = '';

        const categories = appState.getCategories();
        const filteredCategories = categories.filter(category => 
            category.toLowerCase().includes(filter)
        );

        // Add filtered categories
        filteredCategories.forEach(category => {
            const item = document.createElement('div');
            item.className = 'dropdown-item';
            item.textContent = category;
            item.onclick = () => this.selectEditCategory(category);
            dropdown.appendChild(item);
        });

        // Add new category option
        const addNew = document.createElement('div');
        addNew.className = 'dropdown-item add-new';
        addNew.textContent = '+ Add New Category';
        addNew.onclick = () => this.addNewEditCategory();
        dropdown.appendChild(addNew);
    }

    static selectCategory(category) {
        document.getElementById('category').value = category;
        document.getElementById('category-dropdown').style.display = 'none';
    }

    static selectEditCategory(category) {
        document.getElementById('edit-transaction-category').value = category;
        document.getElementById('edit-category-dropdown').style.display = 'none';
    }

    static async addNewCategory() {
        const newCategory = await UI.getUserInput('Enter new category name:');
        if (newCategory) {
            try {
                await API.createCategory({ name: newCategory });
                await this.loadCategories();
                document.getElementById('category').value = newCategory;
                document.getElementById('category-dropdown').style.display = 'none';
            } catch (error) {
                console.error('Error creating category:', error);
                UI.showNotification('Error creating category', 'error');
            }
        } else {
            document.getElementById('category-dropdown').style.display = 'none';
        }
    }

    static async addNewEditCategory() {
        const newCategory = await UI.getUserInput('Enter new category name:');
        if (newCategory) {
            try {
                await API.createCategory({ name: newCategory });
                await this.loadCategories();
                document.getElementById('edit-transaction-category').value = newCategory;
                document.getElementById('edit-category-dropdown').style.display = 'none';
            } catch (error) {
                console.error('Error creating category:', error);
                UI.showNotification('Error creating category', 'error');
            }
        } else {
            document.getElementById('edit-category-dropdown').style.display = 'none';
        }
    }
}

// Global functions for HTML handlers
window.showPayeeDropdown = () => PayeesAndCategoriesComponent.showPayeeDropdown();
window.hidePayeeDropdown = () => PayeesAndCategoriesComponent.hidePayeeDropdown();
window.showEditPayeeDropdown = () => PayeesAndCategoriesComponent.showEditPayeeDropdown();
window.hideEditPayeeDropdown = () => PayeesAndCategoriesComponent.hideEditPayeeDropdown();
window.filterPayees = () => PayeesAndCategoriesComponent.filterPayees();
window.filterEditPayees = () => PayeesAndCategoriesComponent.filterEditPayees();

// Category search functions
window.showCategoryDropdown = () => PayeesAndCategoriesComponent.showCategoryDropdown();
window.hideCategoryDropdown = () => PayeesAndCategoriesComponent.hideCategoryDropdown();
window.showEditCategoryDropdown = () => PayeesAndCategoriesComponent.showEditCategoryDropdown();
window.hideEditCategoryDropdown = () => PayeesAndCategoriesComponent.hideEditCategoryDropdown();
window.filterCategories = () => PayeesAndCategoriesComponent.filterCategories();
window.filterEditCategories = () => PayeesAndCategoriesComponent.filterEditCategories();