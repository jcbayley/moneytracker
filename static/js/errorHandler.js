/**
 * Error handling utilities
 * Makes error handling consistent and easy to understand
 */

const ErrorHandler = {
    // Wrap any function with error handling
    withErrorHandling(fn, context = 'Unknown operation') {
        return async function(...args) {
            try {
                Utils.setLoading(this.loadingElementId, true);
                const result = await fn.apply(this, args);
                return result;
            } catch (error) {
                ErrorHandler.handleError(error, context);
                return null;
            } finally {
                if (this.loadingElementId) {
                    Utils.setLoading(this.loadingElementId, false);
                }
            }
        };
    },

    // Main error handler - all errors go through here
    handleError(error, context = 'Application') {
        console.error(`Error in ${context}:`, error);
        
        // Get user-friendly error message
        const message = ErrorHandler.getUserFriendlyMessage(error);
        
        // Show notification to user
        Utils.showNotification(`${context}: ${message}`, 'error');
        
        // Log to server if needed (optional)
        if (Config.get('FEATURES.ERROR_REPORTING', false)) {
            ErrorHandler.logToServer(error, context);
        }
    },

    // Convert technical errors to user-friendly messages
    getUserFriendlyMessage(error) {
        if (typeof error === 'string') return error;
        if (error.message) {
            // Handle specific error types
            if (error.message.includes('fetch')) {
                return 'Could not connect to server. Please check your connection.';
            }
            if (error.message.includes('JSON')) {
                return 'Received invalid data from server.';
            }
            if (error.message.includes('NetworkError')) {
                return 'Network connection problem. Please try again.';
            }
            if (error.message.includes('timeout')) {
                return 'Request took too long. Please try again.';
            }
            return error.message;
        }
        return 'An unexpected error occurred. Please try again.';
    },

    // API-specific error handling
    handleApiError(error, endpoint = '') {
        console.error(`API Error at ${endpoint}:`, error);
        
        let message = 'Server error occurred';
        
        if (error.status) {
            switch (error.status) {
                case 400:
                    message = 'Invalid request. Please check your input.';
                    break;
                case 401:
                    message = 'You are not authorized to perform this action.';
                    break;
                case 403:
                    message = 'Access denied.';
                    break;
                case 404:
                    message = 'The requested resource was not found.';
                    break;
                case 500:
                    message = 'Server error. Please try again later.';
                    break;
                default:
                    message = `Server error (${error.status}). Please try again.`;
            }
        } else if (error.message) {
            message = ErrorHandler.getUserFriendlyMessage(error);
        }
        
        Utils.showNotification(message, 'error');
        return { success: false, error: message };
    },

    // Validation error handling
    handleValidationError(fieldName, value, rule) {
        let message = `Invalid ${fieldName}`;
        
        switch (rule) {
            case 'required':
                message = `${fieldName} is required`;
                break;
            case 'number':
                message = `${fieldName} must be a valid number`;
                break;
            case 'positive':
                message = `${fieldName} must be greater than zero`;
                break;
            case 'email':
                message = `Please enter a valid email address`;
                break;
            case 'minLength':
                message = `${fieldName} is too short`;
                break;
            case 'maxLength':
                message = `${fieldName} is too long`;
                break;
        }
        
        Utils.showNotification(message, 'error');
        return { success: false, error: message };
    },

    // Network connection checker
    async checkConnection() {
        try {
            const response = await fetch('/api/ping', { 
                method: 'GET',
                timeout: 5000 
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    },

    // Retry helper for failed operations
    async retry(fn, maxAttempts = 3, delay = 1000) {
        let lastError;
        
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                console.warn(`Attempt ${attempt} failed:`, error);
                
                if (attempt < maxAttempts) {
                    await new Promise(resolve => setTimeout(resolve, delay));
                    delay *= 2; // Exponential backoff
                }
            }
        }
        
        throw lastError;
    },

    // Safe async wrapper - won't crash the app if something goes wrong
    async safely(asyncFn, fallbackValue = null, context = 'Operation') {
        try {
            return await asyncFn();
        } catch (error) {
            ErrorHandler.handleError(error, context);
            return fallbackValue;
        }
    },

    // Log errors to server (optional feature)
    async logToServer(error, context) {
        try {
            await fetch('/api/log-error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    error: error.message || error.toString(),
                    context: context,
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    userAgent: navigator.userAgent
                })
            });
        } catch (logError) {
            console.warn('Could not log error to server:', logError);
        }
    }
};

// Helper functions to make error handling easier

// Wrap any async function to handle errors automatically
window.safeAsync = function(fn, context) {
    return ErrorHandler.withErrorHandling(fn, context);
};

// Quick way to handle API calls
window.safeApiCall = async function(apiCall, context) {
    return ErrorHandler.safely(apiCall, null, context);
};

// Make ErrorHandler available globally
window.ErrorHandler = ErrorHandler;