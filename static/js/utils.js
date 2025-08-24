/**
 * Utility functions for common tasks
 * Makes JavaScript easier to read and maintain
 */

const Utils = {
    // DOM Utilities - make DOM manipulation easier
    createElement(tag, className = '', text = '') {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text) element.textContent = text;
        return element;
    },

    getElement(id) {
        return document.getElementById(id);
    },

    getAllElements(selector) {
        return document.querySelectorAll(selector);
    },

    showElement(element) {
        if (element) element.style.display = '';
    },

    hideElement(element) {
        if (element) element.style.display = 'none';
    },

    // Currency formatting - consistent across the app
    formatCurrency(amount) {
        if (amount === null || amount === undefined) return '£0.00';
        const num = parseFloat(amount);
        return new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency: 'GBP'
        }).format(num);
    },

    // Create amount element with proper styling
    createAmountElement(amount) {
        const span = Utils.createElement('span');
        const num = parseFloat(amount);
        span.textContent = Utils.formatCurrency(Math.abs(num));
        span.className = num >= 0 ? 'positive-amount' : 'negative-amount';
        return span;
    },

    // Date utilities - make date handling simpler
    formatDate(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toLocaleDateString('en-GB');
    },

    getTodayString() {
        return new Date().toISOString().split('T')[0];
    },

    setInputToToday(inputId) {
        const input = Utils.getElement(inputId);
        if (input) {
            input.valueAsDate = new Date();
        }
    },

    // Validation helpers - simple and clear
    isRequired(value, fieldName) {
        if (!value || value.toString().trim() === '') {
            throw new Error(`${fieldName} is required`);
        }
        return value.toString().trim();
    },

    isValidNumber(value, fieldName) {
        const num = parseFloat(value);
        if (isNaN(num)) {
            throw new Error(`${fieldName} must be a valid number`);
        }
        return num;
    },

    isPositiveNumber(value, fieldName) {
        const num = Utils.isValidNumber(value, fieldName);
        if (num <= 0) {
            throw new Error(`${fieldName} must be greater than zero`);
        }
        return num;
    },

    // Array utilities - common operations made simple
    removeFromArray(array, item) {
        const index = array.indexOf(item);
        if (index > -1) {
            array.splice(index, 1);
        }
        return array;
    },

    uniqueArray(array) {
        return [...new Set(array)];
    },

    // Performance utility - prevents too many function calls
    debounce(func, waitMs) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), waitMs);
        };
    },

    // Local storage helpers - safe storage operations
    saveToStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.warn(`Could not save to storage: ${key}`, error);
            return false;
        }
    },

    loadFromStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.warn(`Could not load from storage: ${key}`, error);
            return defaultValue;
        }
    },

    // Simple notification system
    showNotification(message, type = 'info', durationMs = 3000) {
        // Create notification element
        const notification = Utils.createElement('div', `notification notification-${type}`);
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: inherit; margin-left: 10px; cursor: pointer;">×</button>
        `;
        
        // Add styles if not already added
        if (!document.getElementById('notification-styles')) {
            const styles = Utils.createElement('style');
            styles.id = 'notification-styles';
            styles.textContent = `
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 12px 16px;
                    border-radius: 4px;
                    color: white;
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    max-width: 400px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .notification-info { background-color: #3498db; }
                .notification-success { background-color: #27ae60; }
                .notification-error { background-color: #e74c3c; }
                .notification-warning { background-color: #f39c12; }
            `;
            document.head.appendChild(styles);
        }
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, durationMs);
        
        return notification;
    },

    // Simple confirmation dialog
    async confirmAction(message) {
        return window.confirm(message);
    },

    // Form helpers - make form handling easier
    getFormData(formId) {
        const form = Utils.getElement(formId);
        if (!form) return {};
        
        const data = {};
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                data[input.id] = input.checked;
            } else if (input.type === 'radio') {
                if (input.checked) data[input.name] = input.value;
            } else {
                data[input.id] = input.value;
            }
        });
        
        return data;
    },

    clearForm(formId) {
        const form = Utils.getElement(formId);
        if (form) {
            form.reset();
        }
    },

    // Populate select dropdown - very common operation
    populateSelect(selectId, options, valueKey = 'id', textKey = 'name', placeholder = null) {
        const select = Utils.getElement(selectId);
        if (!select) return;
        
        select.innerHTML = '';
        
        // Add placeholder if provided
        if (placeholder) {
            const option = Utils.createElement('option');
            option.value = '';
            option.textContent = placeholder;
            select.appendChild(option);
        }
        
        // Add options
        options.forEach(item => {
            const option = Utils.createElement('option');
            option.value = item[valueKey];
            option.textContent = item[textKey];
            select.appendChild(option);
        });
    },

    // Loading state helpers
    setLoading(elementId, isLoading) {
        const element = Utils.getElement(elementId);
        if (!element) return;
        
        if (isLoading) {
            element.style.opacity = '0.6';
            element.style.pointerEvents = 'none';
            if (element.tagName === 'BUTTON') {
                element.disabled = true;
                element.originalText = element.textContent;
                element.textContent = 'Loading...';
            }
        } else {
            element.style.opacity = '';
            element.style.pointerEvents = '';
            if (element.tagName === 'BUTTON') {
                element.disabled = false;
                if (element.originalText) {
                    element.textContent = element.originalText;
                    delete element.originalText;
                }
            }
        }
    }
};

// Make Utils available globally so all other files can use it
window.Utils = Utils;