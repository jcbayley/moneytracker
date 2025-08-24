/**
 * UI management utilities
 */
const UI = {
    /**
     * Populate a select element with options
     */
    populateSelect(selectId, options, valueKey = 'value', textKey = 'text', defaultOption = null) {
        const select = document.getElementById(selectId);
        if (!select) return;

        const currentValue = select.value;
        select.innerHTML = '';

        if (defaultOption) {
            const option = document.createElement('option');
            option.value = defaultOption.value || '';
            option.textContent = defaultOption.text;
            select.appendChild(option);
        }

        options.forEach(item => {
            const option = document.createElement('option');
            if (typeof item === 'string') {
                option.value = item;
                option.textContent = item;
            } else {
                option.value = item[valueKey];
                option.textContent = item[textKey];
            }
            select.appendChild(option);
        });

        // Restore previous value if it exists
        if (currentValue) {
            select.value = currentValue;
        }
    },

    /**
     * Show/hide modal
     */
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
        }
    },

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    },

    /**
     * Clear form fields
     */
    clearForm(formId) {
        const form = document.getElementById(formId) || document;
        const inputs = form.querySelectorAll('input, select, textarea');
        
        // Don't clear these filter inputs
        const filterInputIds = ['transaction-date-from', 'transaction-date-to', 'transaction-account-filter', 'transaction-category-filter', 'transaction-type-filter'];
        
        inputs.forEach(input => {
            // Skip filter inputs
            if (filterInputIds.includes(input.id)) {
                return;
            }
            
            if (input.type === 'checkbox' || input.type === 'radio') {
                input.checked = false;
            } else if (input.type === 'date') {
                input.valueAsDate = new Date();
            } else {
                input.value = input.defaultValue || '';
            }
        });
    },

    /**
     * Format currency
     */
    formatCurrency(amount, currency = '£') {
        return `${currency}${Math.abs(amount).toFixed(2)}`;
    },

    /**
     * Create amount element with positive/negative styling
     */
    createAmountElement(amount, currency = '£') {
        const span = document.createElement('span');
        span.className = `amount ${amount >= 0 ? 'positive' : 'negative'}`;
        span.textContent = this.formatCurrency(amount, currency);
        return span;
    },

    /**
     * Debounce function calls
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Show notification/alert
     */
    showNotification(message, type = 'info') {
        // For now, use alert - can be enhanced with a proper notification system
        if (type === 'error') {
            alert('Error: ' + message);
        } else if (type === 'success') {
            alert('Success: ' + message);
        } else {
            alert(message);
        }
    },

    /**
     * Confirm action
     */
    async confirmAction(message) {
        return confirm(message);
    },

    /**
     * Get user input
     */
    async getUserInput(message, defaultValue = '') {
        return prompt(message, defaultValue);
    },

    /**
     * Toggle element visibility
     */
    toggleVisibility(elementId, visible = null) {
        const element = document.getElementById(elementId);
        if (!element) return;

        if (visible === null) {
            element.style.display = element.style.display === 'none' ? '' : 'none';
        } else {
            element.style.display = visible ? '' : 'none';
        }
    },

    /**
     * Set active tab
     */
    setActiveTab(activeTabId) {
        const tabs = ['transactions', 'recurring', 'projects', 'analytics', 'ai-query', 'settings'];
        
        tabs.forEach(tab => {
            const tabElement = document.getElementById(`${tab}-tab`);
            if (tabElement) {
                tabElement.classList.toggle('hidden', tab !== activeTabId);
            }
        });

        // Update tab buttons
        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        event.target.classList.add('active');
    },

    /**
     * Create table row
     */
    createTableRow(data, columns) {
        const tr = document.createElement('tr');
        
        columns.forEach(column => {
            const td = document.createElement('td');
            
            if (typeof column === 'function') {
                td.appendChild(column(data));
            } else if (typeof column === 'object') {
                if (column.type === 'amount') {
                    td.appendChild(this.createAmountElement(data[column.key], column.currency));
                } else {
                    td.textContent = data[column.key] || column.default || '-';
                }
            } else {
                td.textContent = data[column] || '-';
            }
            
            tr.appendChild(td);
        });

        return tr;
    }
};