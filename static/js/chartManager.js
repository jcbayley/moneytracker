/**
 * Chart management - broken down into small, easy-to-understand functions
 * Each function has one clear responsibility
 */

const ChartManager = {
    // Main function - now much simpler to read
    async updateAllCharts() {
        const safeUpdate = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            const chartData = await API.getAnalyticsCharts(filters);
            
            console.log('Chart data received:', chartData);
            
            // Destroy old charts
            appState.destroyAllCharts();
            
            // Create each chart type
            await ChartManager.createCategoryChart(chartData.category);
            await ChartManager.createTrendChart(chartData.trend);
            await ChartManager.createCategoryTrendsChart(chartData.category_trends);
            
            // Create new charts with separate API calls
            await ChartManager.createTopPayeesChart();
            await ChartManager.createFlowChart();
            await ChartManager.createNetWorthChart();
            
        }, 'updating charts');
        
        await safeUpdate();
    },

    // Get filters - simple and clear
    getAnalyticsFilters() {
        const filters = {};
        
        // Get selected account types
        const checkboxes = Utils.getAllElements('#account-type-filters input[type="checkbox"]:checked');
        const selectedTypes = Array.from(checkboxes).map(cb => cb.value);
        if (selectedTypes.length > 0) {
            filters.account_types = selectedTypes;
        }
        
        // Get date range
        const startDate = Utils.getElement('start-date')?.value;
        const endDate = Utils.getElement('analytics-end-date')?.value;
        
        if (startDate) filters.start_date = startDate;
        if (endDate) filters.end_date = endDate;
        
        return filters;
    },

    // Create category chart (pie/doughnut) - focused and readable
    async createCategoryChart(categoryData) {
        if (!categoryData?.labels?.length) return null;
        
        const canvas = Utils.getElement('categoryChart');
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: categoryData,
            options: ChartManager.getCategoryChartOptions(categoryData)
        });
        
        appState.setChart('category', chart);
        return chart;
    },

    // Category chart options - separated for clarity
    getCategoryChartOptions(categoryData) {
        return { 
            responsive: Config.get('CHARTS.RESPONSIVE'),
            maintainAspectRatio: Config.get('CHARTS.MAINTAIN_ASPECT_RATIO'),
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const category = categoryData.labels[index];
                    ChartManager.showCategoryDetails(category);
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') },
                        boxWidth: 12
                    }
                }
            }
        };
    },

    // Create trend chart (line) - clean and simple
    async createTrendChart(trendData) {
        if (!trendData?.labels?.length) return null;
        
        const canvas = Utils.getElement('trendChart');
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: trendData,
            options: ChartManager.getLineChartOptions()
        });
        
        appState.setChart('trend', chart);
        return chart;
    },

    // Line chart options - reusable
    getLineChartOptions() {
        return {
            responsive: Config.get('CHARTS.RESPONSIVE'),
            maintainAspectRatio: Config.get('CHARTS.MAINTAIN_ASPECT_RATIO'),
            scales: { 
                x: {
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                },
                y: { 
                    beginAtZero: true,
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                }
            }
        };
    },

    // Create account chart (bar) - straightforward
    async createAccountChart(accountData) {
        if (!accountData?.labels?.length) return null;
        
        const canvas = Utils.getElement('accountChart');
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: accountData,
            options: ChartManager.getBarChartOptions()
        });
        
        appState.setChart('account', chart);
        return chart;
    },

    // Bar chart options - consistent styling
    getBarChartOptions() {
        return {
            responsive: Config.get('CHARTS.RESPONSIVE'),
            maintainAspectRatio: Config.get('CHARTS.MAINTAIN_ASPECT_RATIO'),
            scales: { 
                x: {
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                },
                y: { 
                    beginAtZero: true,
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                }
            }
        };
    },

    // Create category trends chart (stacked bar) - clearer logic
    async createCategoryTrendsChart(categoryTrendsData) {
        if (!categoryTrendsData?.labels?.length) return null;
        
        const canvas = Utils.getElement('categoryTrendsChart');
        if (!canvas) return null;
        
        // Prepare data - separate concern
        const chartData = ChartManager.prepareCategoryTrendsData(categoryTrendsData);
        
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: ChartManager.getStackedBarChartOptions(chartData)
        });
        
        appState.setChart('categoryTrends', chart);
        return chart;
    },

    // Prepare category trends data - easier to understand
    prepareCategoryTrendsData(rawData) {
        const datasets = rawData.datasets.map(dataset => ({
            ...dataset,
            backgroundColor: dataset.borderColor,
            borderWidth: 1,
            type: 'bar',
            order: 1  // Higher order means it renders behind the line
        }));
        
        // Add income line if monthly_income data is available
        if (rawData.monthly_income && rawData.monthly_income.length > 0) {
            datasets.push({
                label: 'Monthly Income',
                data: rawData.monthly_income,
                borderColor: '#36A2EB',
                backgroundColor: 'transparent',
                borderWidth: 3,
                borderDash: [5, 5],
                type: 'line',
                yAxisID: 'income',
                tension: 0.4,
                fill: false,
                pointRadius: 4,
                pointBackgroundColor: '#36A2EB',
                order: 0  // Lower order means it renders on top
            });
        }
        
        return {
            ...rawData,
            datasets
        };
    },

    // Stacked bar chart options
    getStackedBarChartOptions(chartData) {
        return { 
            responsive: Config.get('CHARTS.RESPONSIVE'),
            maintainAspectRatio: Config.get('CHARTS.MAINTAIN_ASPECT_RATIO'),
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const datasetIndex = elements[0].datasetIndex;
                    const monthIndex = elements[0].index;
                    const dataset = chartData.datasets[datasetIndex];
                    const month = chartData.labels[monthIndex];
                    
                    // Check if clicked on income line
                    if (dataset.label === 'Monthly Income' || dataset.type === 'line') {
                        ChartManager.showIncomeDetailsForMonth(month);
                    } else {
                        // Clicked on spending category bar
                        const category = dataset.label;
                        ChartManager.showCategoryDetailsForMonth(category, month);
                    }
                }
            },
            scales: { 
                x: { 
                    stacked: true,
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                },
                y: { 
                    stacked: true,
                    beginAtZero: true,
                    position: 'left',
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } },
                    title: {
                        display: true,
                        text: 'Spending (£)'
                    }
                },
                income: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } },
                    title: {
                        display: true,
                        text: 'Income (£)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                },
                tooltip: {
                    callbacks: {
                        afterTitle: function(context) {
                            // Calculate and display total spent for the month
                            const monthIndex = context[0].dataIndex;
                            let totalSpent = 0;
                            chartData.datasets.forEach(dataset => {
                                if (dataset.data[monthIndex]) {
                                    totalSpent += dataset.data[monthIndex];
                                }
                            });
                            return `Total Spent: £${totalSpent.toFixed(2)}`;
                        }
                    }
                },
                datalabels: {
                    display: function(context) {
                        return context.datasetIndex === chartData.datasets.length - 1; // Only show on top dataset
                    },
                    anchor: 'end',
                    align: 'top',
                    formatter: function(value, context) {
                        // Calculate total spent for this month
                        const monthIndex = context.dataIndex;
                        let totalSpent = 0;
                        chartData.datasets.forEach(dataset => {
                            if (dataset.data[monthIndex]) {
                                totalSpent += dataset.data[monthIndex];
                            }
                        });
                        return `£${totalSpent.toFixed(0)}`;
                    },
                    color: '#333',
                    font: {
                        weight: 'bold',
                        size: 10
                    }
                }
            }
        };
    },

    // Show category details - clean and focused
    async showCategoryDetails(category) {
        const safeShow = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            const transactions = await API.getCategoryTransactions(category, filters);
            
            ChartManager.displayCategoryModal(category, transactions);
            
        }, 'loading category details');
        
        await safeShow();
    },

    // Show category details for specific month (for bar chart)
    async showCategoryDetailsForMonth(category, month) {
        const safeShow = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            
            // Calculate start and end dates for the specific month
            const monthFilters = ChartManager.getMonthFilters(month, filters);
            
            const transactions = await API.getCategoryTransactions(category, monthFilters);
            
            ChartManager.displayCategoryModalForMonth(category, month, transactions);
            
        }, 'loading category details for month');
        
        await safeShow();
    },

    // Show income details for specific month
    async showIncomeDetailsForMonth(month) {
        const safeShow = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            
            // Calculate start and end dates for the specific month
            const monthFilters = ChartManager.getMonthFilters(month, filters);
            
            const transactions = await API.getIncomeTransactions(monthFilters);
            
            ChartManager.displayIncomeModalForMonth(month, transactions);
            
        }, 'loading income details for month');
        
        await safeShow();
    },

    // Get month-specific filters
    getMonthFilters(month, baseFilters) {
        // Month format is typically "2024-01" or similar
        const [year, monthNum] = month.split('-');
        const startDate = `${year}-${monthNum.padStart(2, '0')}-01`;
        
        // Get last day of month
        const nextMonth = new Date(parseInt(year), parseInt(monthNum), 1);
        const lastDay = new Date(nextMonth.getTime() - 1);
        const endDate = lastDay.toISOString().split('T')[0];
        
        return {
            ...baseFilters,
            start_date: startDate,
            end_date: endDate
        };
    },

    // Display category modal - separated UI logic
    displayCategoryModal(category, transactions) {
        const titleElement = Utils.getElement('category-modal-title');
        const tableContainer = Utils.getElement('category-transactions-table');
        
        if (titleElement) {
            titleElement.textContent = `${category} Transactions`;
        }
        
        if (tableContainer) {
            if (transactions.length === 0) {
                tableContainer.innerHTML = ChartManager.getEmptyTransactionsMessage();
            } else {
                tableContainer.innerHTML = ChartManager.createTransactionsTable(transactions);
            }
        }
        
        UI.showModal('categoryDetailsModal');
    },

    // Display category modal for specific month
    displayCategoryModalForMonth(category, month, transactions) {
        const titleElement = Utils.getElement('category-modal-title');
        const tableContainer = Utils.getElement('category-transactions-table');
        
        if (titleElement) {
            // Format month for display (e.g., "2024-01" -> "January 2024")
            const monthDate = new Date(month + '-01');
            const monthName = monthDate.toLocaleDateString('en-US', { 
                month: 'long', 
                year: 'numeric' 
            });
            titleElement.textContent = `${category} Transactions - ${monthName}`;
        }
        
        if (tableContainer) {
            if (transactions.length === 0) {
                tableContainer.innerHTML = ChartManager.getEmptyTransactionsMessage();
            } else {
                tableContainer.innerHTML = ChartManager.createTransactionsTable(transactions);
            }
        }
        
        UI.showModal('categoryDetailsModal');
    },

    // Display income modal for specific month
    displayIncomeModalForMonth(month, transactions) {
        const titleElement = Utils.getElement('category-modal-title');
        const tableContainer = Utils.getElement('category-transactions-table');
        
        if (titleElement) {
            // Format month for display (e.g., "2024-01" -> "January 2024")
            const monthDate = new Date(month + '-01');
            const monthName = monthDate.toLocaleDateString('en-US', { 
                month: 'long', 
                year: 'numeric' 
            });
            titleElement.textContent = `Income Transactions - ${monthName}`;
        }
        
        if (tableContainer) {
            if (transactions.length === 0) {
                tableContainer.innerHTML = ChartManager.getEmptyIncomeTransactionsMessage();
            } else {
                tableContainer.innerHTML = ChartManager.createTransactionsTable(transactions);
            }
        }
        
        UI.showModal('categoryDetailsModal');
    },

    // Empty message - reusable
    getEmptyTransactionsMessage() {
        return '<p style="color: #6c757d; text-align: center; padding: 20px;">No transactions found for this category in the selected period.</p>';
    },

    // Empty message for income transactions
    getEmptyIncomeTransactionsMessage() {
        return '<p style="color: #6c757d; text-align: center; padding: 20px;">No income transactions found for this month in the selected period.</p>';
    },

    // Create transactions table - clean HTML generation
    createTransactionsTable(transactions) {
        const headers = ['Date', 'Account', 'Payee', 'Amount', 'Notes'];
        
        let tableHtml = `
            <table style="width: 100%; margin-top: 15px;">
                <thead>
                    <tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>
                </thead>
                <tbody>
        `;
        
        transactions.forEach(transaction => {
            tableHtml += ChartManager.createTransactionRow(transaction);
        });
        
        tableHtml += '</tbody></table>';
        return tableHtml;
    },

    // Create single transaction row - focused responsibility
    createTransactionRow(transaction) {
        const amountElement = Utils.createAmountElement(transaction.amount);
        
        return `
            <tr>
                <td>${transaction.date}</td>
                <td>${transaction.account_name}</td>
                <td>${transaction.payee || '-'}</td>
                <td>${amountElement.outerHTML}</td>
                <td>${transaction.notes || '-'}</td>
            </tr>
        `;
    },

    // Close category modal - simple
    closeCategoryModal() {
        UI.hideModal('categoryDetailsModal');
    },

    // Create top payees chart - new functionality
    async createTopPayeesChart() {
        const safeCreate = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            const payeesData = await API.getTopPayees(filters);
            
            if (!payeesData?.labels?.length) return null;
            
            const canvas = Utils.getElement('topPayeesChart');
            if (!canvas) return null;
            
            const ctx = canvas.getContext('2d');
            const chart = new Chart(ctx, {
                type: 'bar',
                data: payeesData,
                options: ChartManager.getBarChartOptions()
            });
            
            appState.setChart('topPayees', chart);
            return chart;
        }, 'creating top payees chart');
        
        return await safeCreate();
    },

    // Create flow analysis chart - new functionality
    async createFlowChart() {
        const safeCreate = safeAsync(async () => {
            const filters = ChartManager.getAnalyticsFilters();
            const flowData = await API.getSavingsInvestmentsFlow(filters);
            
            if (!flowData?.labels?.length) return null;
            
            const canvas = Utils.getElement('flowChart');
            if (!canvas) return null;
            
            // Prepare the data with income line
            const chartData = ChartManager.prepareFlowChartData(flowData);
            
            const ctx = canvas.getContext('2d');
            const chart = new Chart(ctx, {
                type: 'bar',
                data: chartData,
                options: ChartManager.getFlowChartOptions(chartData)
            });
            
            appState.setChart('flow', chart);
            return chart;
        }, 'creating flow analysis chart');
        
        return await safeCreate();
    },

    // Prepare flow chart data with income line
    prepareFlowChartData(rawData) {
        const datasets = rawData.datasets.map(dataset => ({
            ...dataset,
            type: 'bar',
            order: 1  // Higher order means it renders behind the line
        }));
        
        // Add income line if monthly_income data is available
        if (rawData.monthly_income && rawData.monthly_income.length > 0) {
            datasets.push({
                label: 'All Income',
                data: rawData.monthly_income,
                borderColor: '#36A2EB',
                backgroundColor: 'transparent',
                borderWidth: 3,
                borderDash: [5, 5],
                type: 'line',
                yAxisID: 'income',
                tension: 0.4,
                fill: false,
                pointRadius: 4,
                pointBackgroundColor: '#36A2EB',
                order: 0  // Lower order means it renders on top
            });
        }
        
        return {
            ...rawData,
            datasets
        };
    },

    // Flow chart specific options
    getFlowChartOptions(chartData) {
        return {
            responsive: Config.get('CHARTS.RESPONSIVE'),
            maintainAspectRatio: Config.get('CHARTS.MAINTAIN_ASPECT_RATIO'),
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const datasetIndex = elements[0].datasetIndex;
                    const monthIndex = elements[0].index;
                    const dataset = chartData.datasets[datasetIndex];
                    const month = chartData.labels[monthIndex];
                    
                    // Check if clicked on income line
                    if (dataset.label === 'All Income' || dataset.type === 'line') {
                        ChartManager.showIncomeDetailsForMonth(month);
                    }
                    // Note: Flow chart doesn't have clickable spending categories
                }
            },
            scales: { 
                x: { 
                    stacked: true,
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                },
                y: { 
                    stacked: true,
                    beginAtZero: true,
                    position: 'left',
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } },
                    title: {
                        display: true,
                        text: 'Net Flow (£)'
                    }
                },
                income: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    ticks: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } },
                    title: {
                        display: true,
                        text: 'Income (£)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { font: { size: Config.get('CHARTS.DEFAULT_FONT_SIZE') } }
                }
            }
        };
    },

    // Create net worth history chart - new functionality  
    async createNetWorthChart() {
        const safeCreate = safeAsync(async () => {
            const netWorthData = await API.getNetWorthHistory();
            
            if (!netWorthData?.labels?.length) return null;
            
            const canvas = Utils.getElement('netWorthChart');
            if (!canvas) return null;
            
            const ctx = canvas.getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: netWorthData,
                options: ChartManager.getLineChartOptions()
            });
            
            appState.setChart('netWorth', chart);
            return chart;
        }, 'creating net worth chart');
        
        return await safeCreate();
    }
};

// Make ChartManager available globally
window.ChartManager = ChartManager;