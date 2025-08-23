/**
 * API communication module
 */
class API {
    /**
     * Make API calls with consistent error handling
     */
    static async call(endpoint, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(endpoint, options);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Account endpoints
    static async getAccounts() {
        return this.call('/api/accounts');
    }

    static async createAccount(accountData) {
        return this.call('/api/accounts', 'POST', accountData);
    }

    static async updateAccount(id, accountData) {
        return this.call(`/api/accounts/${id}`, 'PUT', accountData);
    }

    // Transaction endpoints
    static async getTransactions(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.call(`/api/transactions?${params.toString()}`);
    }

    static async createTransaction(transactionData) {
        return this.call('/api/transactions', 'POST', transactionData);
    }

    static async updateTransaction(id, transactionData) {
        return this.call(`/api/transactions/${id}`, 'PUT', transactionData);
    }

    static async deleteTransaction(id) {
        return this.call(`/api/transactions/${id}`, 'DELETE');
    }

    // Payee endpoints
    static async getPayees() {
        return this.call('/api/payees');
    }

    static async createPayee(payeeData) {
        return this.call('/api/payees', 'POST', payeeData);
    }

    // Category endpoints
    static async getCategories() {
        return this.call('/api/categories');
    }

    static async createCategory(categoryData) {
        return this.call('/api/categories', 'POST', categoryData);
    }

    // Recurring endpoints
    static async getRecurringTransactions() {
        return this.call('/api/recurring');
    }

    static async deleteRecurringTransaction(id) {
        return this.call(`/api/recurring/${id}`, 'DELETE');
    }

    static async processRecurringTransactions() {
        return this.call('/api/recurring/process', 'POST');
    }

    // Analytics endpoints
    static async getAnalyticsStats(filters = {}) {
        const params = this._buildParams(filters);
        return this.call(`/api/analytics/stats?${params.toString()}`);
    }

    static async getAnalyticsCharts(filters = {}) {
        const params = this._buildParams(filters);
        return this.call(`/api/analytics/charts?${params.toString()}`);
    }

    static async getCategoryTransactions(category, filters = {}) {
        const params = this._buildParams(filters);
        return this.call(`/api/analytics/category/${encodeURIComponent(category)}?${params.toString()}`);
    }

    // Helper method to properly handle array parameters
    static _buildParams(filters) {
        const params = new URLSearchParams();
        
        for (const [key, value] of Object.entries(filters)) {
            if (Array.isArray(value)) {
                // Add each array item as a separate parameter with the same key
                value.forEach(item => params.append(key, item));
            } else {
                params.append(key, value);
            }
        }
        
        return params;
    }

    // Data endpoints
    static async getDatabaseInfo() {
        return this.call('/api/database/info');
    }

    // Settings endpoints
    static async getSettings() {
        return this.call('/api/settings');
    }

    static async saveSettings(settings) {
        return this.call('/api/settings', 'POST', settings);
    }
}