/**
 * Analytics management - simplified and easy to understand
 * Each function has a single, clear purpose
 */

const AnalyticsManager = {
    // Main analytics update - clean and simple
    async updateAnalytics() {
        const safeUpdate = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            const stats = await API.getAnalyticsStats(filters);
            
            AnalyticsManager.displayStats(stats);
            await ChartManager.updateAllCharts();
            
        }, 'updating analytics');
        
        await safeUpdate();
    },

    // Display stats - focused on one task
    displayStats(stats) {
        const statsMapping = {
            'total-balance': stats.total_balance,
            'monthly-income': stats.monthly_income,
            'monthly-expenses': stats.monthly_expenses,
            'net-monthly': stats.net_monthly
        };
        
        Object.entries(statsMapping).forEach(([elementId, value]) => {
            const element = Utils.getElement(elementId);
            if (element) {
                element.textContent = Utils.formatCurrency(value);
            }
        });
    },

    // Date filter management - broken into logical steps
    updateDateFilter() {
        const period = AnalyticsManager.getSelectedPeriod();
        if (!period) return;
        
        const dateInputs = AnalyticsManager.getDateInputElements();
        if (!dateInputs.startDate || !dateInputs.endDate) return;
        
        // Reset controls first
        AnalyticsManager.resetDateControls(dateInputs);
        
        // Handle custom period
        if (period === 'custom') {
            AnalyticsManager.enableCustomDateInputs(dateInputs);
            return;
        }
        
        // Handle predefined periods
        const dateRange = AnalyticsManager.calculateDateRange(period);
        if (dateRange) {
            AnalyticsManager.setDateInputs(dateInputs, dateRange);
            AnalyticsManager.showNavigationIfNeeded(period, dateInputs);
            AnalyticsManager.updatePeriodLabel(dateRange.label);
        }
        
        AnalyticsManager.updateAnalytics();
    },

    // Get selected period - simple getter
    getSelectedPeriod() {
        const periodSelect = Utils.getElement('date-period');
        return periodSelect?.value;
    },

    // Get date input elements - organized
    getDateInputElements() {
        return {
            startDate: Utils.getElement('start-date'),
            endDate: Utils.getElement('end-date'),
            prevBtn: Utils.getElement('prev-month'),
            nextBtn: Utils.getElement('next-month'),
            currentPeriodSpan: Utils.getElement('current-period')
        };
    },

    // Reset date controls - clear responsibility
    resetDateControls({ startDate, endDate, prevBtn, nextBtn }) {
        if (startDate) startDate.disabled = true;
        if (endDate) endDate.disabled = true;
        if (prevBtn) Utils.hideElement(prevBtn);
        if (nextBtn) Utils.hideElement(nextBtn);
    },

    // Enable custom date inputs - focused function
    enableCustomDateInputs({ startDate, endDate, currentPeriodSpan }) {
        if (startDate) startDate.disabled = false;
        if (endDate) endDate.disabled = false;
        if (currentPeriodSpan) currentPeriodSpan.textContent = 'Custom Range';
    },

    // Show navigation buttons for monthly views
    showNavigationIfNeeded(period, { prevBtn, nextBtn }) {
        if (period === 'current_month' || period === 'last_month') {
            if (prevBtn) Utils.showElement(prevBtn);
            if (nextBtn) Utils.showElement(nextBtn);
        }
    },

    // Update period label - simple UI update
    updatePeriodLabel(label) {
        const currentPeriodSpan = Utils.getElement('current-period');
        if (currentPeriodSpan && label) {
            currentPeriodSpan.textContent = label;
        }
    },

    // Calculate date range - each period type handled clearly
    calculateDateRange(period) {
        const now = new Date();
        
        const periodHandlers = {
            current_month: () => AnalyticsManager.getCurrentMonthRange(),
            last_month: () => AnalyticsManager.getLastMonthRange(now),
            last_3_months: () => AnalyticsManager.getLastNMonthsRange(now, 3),
            last_6_months: () => AnalyticsManager.getLastNMonthsRange(now, 6),
            this_year: () => AnalyticsManager.getThisYearRange(now)
        };
        
        const handler = periodHandlers[period];
        return handler ? handler() : null;
    },

    // Current month range - uses app state
    getCurrentMonthRange() {
        const currentMonth = appState.getAnalyticsMonth();
        const start = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
        const end = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
        const label = currentMonth.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
        
        return { start, end, label };
    },

    // Last month range - clear calculation
    getLastMonthRange(now) {
        const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const end = new Date(now.getFullYear(), now.getMonth(), 0);
        const label = start.toLocaleDateString('en-US', {month: 'long', year: 'numeric'});
        
        return { start, end, label };
    },

    // Last N months range - reusable
    getLastNMonthsRange(now, months) {
        const start = new Date(now.getFullYear(), now.getMonth() - months, 1);
        const end = now;
        const label = `Last ${months} Months`;
        
        return { start, end, label };
    },

    // This year range - straightforward
    getThisYearRange(now) {
        const start = new Date(now.getFullYear(), 0, 1);
        const end = now;
        const label = now.getFullYear().toString();
        
        return { start, end, label };
    },

    // Set date inputs - helper function
    setDateInputs({ startDate, endDate }, { start, end }) {
        if (startDate && start) {
            startDate.value = start.toISOString().split('T')[0];
        }
        if (endDate && end) {
            endDate.value = end.toISOString().split('T')[0];
        }
    },

    // Navigate month - simple wrapper
    navigateMonth(direction) {
        appState.navigateAnalyticsMonth(direction);
        AnalyticsManager.updateDateFilter();
    }
};

// Make AnalyticsManager available globally
window.AnalyticsManager = AnalyticsManager;