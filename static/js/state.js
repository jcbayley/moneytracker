/**
 * Application state management
 */
class AppState {
    constructor() {
        this.currentAccount = null;
        this.editingAccountId = null;
        this.editingTransactionId = null;
        this.editingProject = null;
        this.currentAnalyticsMonth = new Date();
        this.charts = {};
        this.payeesList = [];
        this.categoriesList = [];
        this.dropdownTimeout = null;
    }

    // Account state
    setCurrentAccount(accountId) {
        this.currentAccount = accountId === this.currentAccount ? null : accountId;
    }

    getCurrentAccount() {
        return this.currentAccount;
    }

    setEditingAccount(accountId) {
        this.editingAccountId = accountId;
    }

    getEditingAccount() {
        return this.editingAccountId;
    }

    clearEditingAccount() {
        this.editingAccountId = null;
    }

    // Transaction state
    setEditingTransaction(transactionId) {
        this.editingTransactionId = transactionId;
    }

    getEditingTransaction() {
        return this.editingTransactionId;
    }

    clearEditingTransaction() {
        this.editingTransactionId = null;
    }

    // Project state
    setEditingProject(project) {
        this.editingProject = project;
    }

    getEditingProject() {
        return this.editingProject;
    }

    clearEditingProject() {
        this.editingProject = null;
    }

    // Analytics state
    setAnalyticsMonth(month) {
        this.currentAnalyticsMonth = month;
    }

    getAnalyticsMonth() {
        return this.currentAnalyticsMonth;
    }

    navigateAnalyticsMonth(direction) {
        this.currentAnalyticsMonth.setMonth(this.currentAnalyticsMonth.getMonth() + direction);
    }

    // Charts state
    setChart(name, chart) {
        if (this.charts[name]) {
            this.charts[name].destroy();
        }
        this.charts[name] = chart;
    }

    getChart(name) {
        return this.charts[name];
    }

    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }

    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }

    // Data state
    setPayees(payees) {
        this.payeesList = payees;
    }

    getPayees() {
        return this.payeesList;
    }

    setCategories(categories) {
        this.categoriesList = categories;
    }

    getCategories() {
        return this.categoriesList;
    }

    // Dropdown state
    setDropdownTimeout(timeout) {
        this.dropdownTimeout = timeout;
    }

    clearDropdownTimeout() {
        if (this.dropdownTimeout) {
            clearTimeout(this.dropdownTimeout);
            this.dropdownTimeout = null;
        }
    }
}

// Global state instance
window.appState = new AppState();