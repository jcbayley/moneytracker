/**
 * Configuration settings for the Money Tracker app
 * All settings in one place - easy to modify
 */

const Config = {
    // API Configuration
    API: {
        BASE_URL: '/api',
        TIMEOUT: 30000, // 30 seconds
        RETRY_ATTEMPTS: 3,
        RETRY_DELAY: 1000 // 1 second
    },

    // UI Configuration
    UI: {
        DEBOUNCE_DELAY: 250, // milliseconds
        NOTIFICATION_DURATION: 3000, // 3 seconds
        LOADING_DELAY: 500, // Show loading after 500ms
        ANIMATION_DURATION: 200
    },

    // Chart Configuration
    CHARTS: {
        COLORS: [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
        ],
        DEFAULT_FONT_SIZE: 14,
        RESPONSIVE: true,
        MAINTAIN_ASPECT_RATIO: false
    },

    // Transaction Configuration
    TRANSACTIONS: {
        DEFAULT_LIMIT: 100,
        MAX_LIMIT: 1000,
        TYPES: ['income', 'expense', 'transfer']
    },

    // Recurring Transaction Configuration
    RECURRING: {
        FREQUENCIES: [
            'daily', 'weekly', 'biweekly', 
            'monthly', 'quarterly', 'yearly'
        ]
    },

    // Account Configuration
    ACCOUNT: {
        TYPES: ['checking', 'savings', 'credit', 'investment'],
        DEFAULT_TYPE: 'checking'
    },

    // Date Configuration
    DATES: {
        FORMAT: 'en-GB',
        INPUT_FORMAT: 'YYYY-MM-DD'
    },

    // Local Storage Keys
    STORAGE: {
        THEME: 'theme',
        LAST_ACCOUNT: 'lastSelectedAccount',
        FILTERS: 'transactionFilters',
        USER_PREFERENCES: 'userPreferences'
    },

    // Validation Rules
    VALIDATION: {
        MIN_AMOUNT: 0.01,
        MAX_AMOUNT: 999999.99,
        MAX_NAME_LENGTH: 255,
        MAX_NOTES_LENGTH: 500
    },

    // Feature Flags - easy to turn features on/off
    FEATURES: {
        DARK_MODE: true,
        BACKUP_REMINDERS: true,
        ADVANCED_ANALYTICS: true,
        EXPORT_FEATURES: true
    },

    // Default Values
    DEFAULTS: {
        CURRENCY: 'GBP',
        CURRENCY_SYMBOL: '£',
        THEME: 'light',
        DATE_RANGE: 'current_month'
    }
};

// Helper functions to access config easily
Config.get = function(path, defaultValue = null) {
    const keys = path.split('.');
    let current = this;
    
    for (const key of keys) {
        if (current[key] === undefined) {
            return defaultValue;
        }
        current = current[key];
    }
    
    return current;
};

// Examples of how to use Config.get():
// Config.get('API.BASE_URL') returns '/api'
// Config.get('CHARTS.COLORS.0') returns '#FF6384'
// Config.get('NONEXISTENT.KEY', 'fallback') returns 'fallback'

// Make Config available globally
window.Config = Config;