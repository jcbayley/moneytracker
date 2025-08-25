/**
 * AI Query component for natural language transaction analysis
 */
const AIQueryComponent = {
    async submitQuery() {
        const queryInput = document.getElementById('ai-query-input');
        const query = queryInput.value.trim();
        
        if (!query) {
            UI.showNotification('Please enter a question about your transactions', 'error');
            return;
        }
        
        this.showLoading(true);
        this.hideResults();
        
        try {
            const result = await API.submitAIQuery(query);
            this.displayResults(result);
            
        } catch (error) {
            console.error('AI Query error:', error);
            UI.showNotification('Failed to process AI query: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    },
    
    showLoading(show) {
        const loadingDiv = document.getElementById('ai-loading');
        const queryBtn = document.getElementById('ai-query-btn');
        
        if (show) {
            loadingDiv.classList.remove('hidden');
            queryBtn.disabled = true;
            queryBtn.textContent = 'Processing...';
        } else {
            loadingDiv.classList.add('hidden');
            queryBtn.disabled = false;
            queryBtn.textContent = 'Ask AI';
        }
    },
    
    hideResults() {
        const resultsDiv = document.getElementById('ai-results');
        const querySection = document.getElementById('ai-query-section');
        const dataSection = document.getElementById('ai-data-section');
        resultsDiv.classList.add('hidden');
        querySection.classList.add('hidden');
        dataSection.classList.add('hidden');
    },
    
    displayResults(result) {
        const resultsDiv = document.getElementById('ai-results');
        const responseDiv = document.getElementById('ai-response');
        const querySection = document.getElementById('ai-query-section');
        const queryDiv = document.getElementById('ai-database-query');
        const dataSection = document.getElementById('ai-data-section');
        const transactionsTable = document.getElementById('ai-transactions-table');
        
        // Show AI summary
        responseDiv.innerHTML = `
            <div style="font-size: 16px; line-height: 1.5;">
                ${this.formatSummary(result.summary)}
            </div>
        `;
        
        // Show database query if available
        if (result.database_query && result.database_query.trim()) {
            queryDiv.textContent = result.database_query;
            querySection.classList.remove('hidden');
        } else {
            querySection.classList.add('hidden');
        }
        
        // Show related transactions if any
        if (result.transactions && result.transactions.length > 0) {
            transactionsTable.innerHTML = this.createTransactionsTable(result.transactions);
            dataSection.classList.remove('hidden');
        } else {
            dataSection.classList.add('hidden');
        }
        
        resultsDiv.classList.remove('hidden');
        
        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },
    
    formatSummary(summary) {
        // Add some basic formatting to make the summary more readable
        return summary
            .replace(/£(\d+\.?\d*)/g, '<strong style="color: #28a745;">£$1</strong>') // Highlight money amounts
            .replace(/(\d+) transactions?/g, '<strong style="color: #007bff;">$1 transaction$2</strong>'); // Highlight transaction counts
    },
    
    createTransactionsTable(transactions) {
        const headers = ['Date', 'Account', 'Payee', 'Category', 'Amount', 'Type'];
        
        let tableHtml = `
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead style="background: #f8f9fa;">
                    <tr>
                        ${headers.map(h => `<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">${h}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
        `;
        
        transactions.forEach(transaction => {
            const amountClass = transaction.amount >= 0 ? 'positive' : 'negative';
            const amountColor = transaction.amount >= 0 ? '#28a745' : '#dc3545';
            
            tableHtml += `
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px; border: 1px solid #dee2e6;">${transaction.date}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">${transaction.account_name}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">${transaction.payee || '-'}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">${transaction.category || '-'}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; color: ${amountColor}; font-weight: bold;">
                        £${Math.abs(transaction.amount).toFixed(2)}
                    </td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">
                        <span style="background: ${this.getTypeColor(transaction.type)}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px;">
                            ${transaction.type}
                        </span>
                    </td>
                </tr>
            `;
        });
        
        tableHtml += '</tbody></table>';
        return tableHtml;
    },
    
    getTypeColor(type) {
        const colors = {
            'income': '#28a745',
            'expense': '#dc3545',
            'transfer': '#6c757d'
        };
        return colors[type] || '#6c757d';
    },
    
    setExampleQuery(exampleText) {
        const queryInput = document.getElementById('ai-query-input');
        queryInput.value = exampleText;
        queryInput.focus();
    },
    
    // Model management functions
    async checkModelStatus(showError = true) {
        try {
            const response = await fetch('/api/ai/model/status');
            const result = await response.json();
            this.updateModelStatus(result);
        } catch (error) {
            console.error('Error checking model status:', error);
            // Only show error notification if explicitly requested (not on startup)
            if (showError) {
                UI.showNotification('Failed to check model status', 'error');
            }
        }
    },

    async downloadModel() {
        const downloadBtn = document.getElementById('download-model-btn');
        const progressDiv = document.getElementById('download-progress');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        
        try {
            downloadBtn.disabled = true;
            downloadBtn.textContent = 'Downloading...';
            progressDiv.classList.remove('hidden');
            progressText.textContent = 'Initializing download...';
            
            const response = await fetch('/api/ai/model/download', { method: 'POST' });
            
            if (!response.ok) {
                throw new Error(`Download failed: ${response.statusText}`);
            }
            
            // Start polling for progress
            this.pollDownloadProgress();
            
        } catch (error) {
            console.error('Error downloading model:', error);
            UI.showNotification('Failed to start model download: ' + error.message, 'error');
            downloadBtn.disabled = false;
            downloadBtn.textContent = 'Download Model';
            progressDiv.classList.add('hidden');
        }
    },

    async pollDownloadProgress() {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const downloadBtn = document.getElementById('download-model-btn');
        
        try {
            const response = await fetch('/api/ai/model/download/progress');
            const result = await response.json();
            
            if (result.progress !== undefined) {
                const percentage = Math.round(result.progress);
                progressBar.style.width = percentage + '%';
                progressText.textContent = `${percentage}% - ${result.status || 'Downloading...'}`;
                
                if (percentage < 100 && result.status !== 'error' && result.status !== 'completed') {
                    // Continue polling
                    setTimeout(() => this.pollDownloadProgress(), 2000);
                } else if (percentage === 100 || result.status === 'completed') {
                    // Download complete
                    progressText.textContent = '100% - Download completed!';
                    downloadBtn.textContent = 'Download Model';
                    downloadBtn.disabled = false;
                    
                    setTimeout(() => {
                        document.getElementById('download-progress').classList.add('hidden');
                        this.checkModelStatus();
                    }, 2000);
                    
                    UI.showNotification('Model downloaded successfully!', 'success');
                } else {
                    // Error occurred
                    throw new Error(result.message || 'Download failed');
                }
            }
        } catch (error) {
            console.error('Error polling download progress:', error);
            progressText.textContent = 'Download failed';
            downloadBtn.disabled = false;
            downloadBtn.textContent = 'Download Model';
            UI.showNotification('Download failed: ' + error.message, 'error');
        }
    },

    updateModelStatus(status) {
        const statusSpan = document.getElementById('model-status');
        const statusSection = document.getElementById('model-status-section');
        const downloadBtn = document.getElementById('download-model-btn');
        const queryBtn = document.getElementById('ai-query-btn');
        
        if (status.downloaded) {
            statusSpan.textContent = 'Ready';
            statusSpan.style.color = '#28a745';
            statusSection.style.background = '#d4edda';
            statusSection.style.borderColor = '#c3e6cb';
            downloadBtn.textContent = 'Model Ready';
            downloadBtn.disabled = true;
            queryBtn.disabled = false;
        } else {
            statusSpan.textContent = 'Not Downloaded';
            statusSpan.style.color = '#dc3545';
            statusSection.style.background = '#fff3cd';
            statusSection.style.borderColor = '#ffeaa7';
            downloadBtn.textContent = 'Download Model';
            downloadBtn.disabled = false;
            queryBtn.disabled = true;
            queryBtn.title = 'Please download the AI model first';
        }
    },

    // Add enter key support for the input
    setupEventListeners() {
        const queryInput = document.getElementById('ai-query-input');
        if (queryInput) {
            queryInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.submitQuery();
                }
            });
        }
        
        // Setup model type switching
        const localRadio = document.getElementById('model-type-local');
        const apiRadio = document.getElementById('model-type-api');
        
        if (localRadio && apiRadio) {
            localRadio.addEventListener('change', () => this.switchModelType('local'));
            apiRadio.addEventListener('change', () => this.switchModelType('api'));
        }
        
        // Check model status on load (silently - don't show error popup)
        this.checkModelStatus(false);
    },

    switchModelType(type) {
        const localSection = document.getElementById('local-model-section');
        const apiSection = document.getElementById('api-model-section');
        
        if (type === 'local') {
            localSection.classList.remove('hidden');
            apiSection.classList.add('hidden');
        } else {
            localSection.classList.add('hidden');
            apiSection.classList.remove('hidden');
            this.loadApiConfig();
        }
    },

    async testApiConnection() {
        const url = document.getElementById('api-url').value.trim();
        const model = document.getElementById('api-model').value.trim();
        const apiKey = document.getElementById('api-key').value.trim();
        const statusDiv = document.getElementById('api-status');
        
        if (!url || !model) {
            statusDiv.innerHTML = '<span style="color: #dc3545;">Please enter API URL and model name</span>';
            return;
        }
        
        statusDiv.innerHTML = '<span style="color: #6c757d;">Testing connection...</span>';
        
        try {
            const response = await fetch('/api/ai/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, model, api_key: apiKey })
            });
            
            const result = await response.json();
            
            if (result.success) {
                statusDiv.innerHTML = '<span style="color: #28a745;">✓ Connection successful!</span>';
            } else {
                statusDiv.innerHTML = `<span style="color: #dc3545;">✗ Connection failed: ${result.error}</span>`;
            }
        } catch (error) {
            statusDiv.innerHTML = `<span style="color: #dc3545;">✗ Connection failed: ${error.message}</span>`;
        }
    },

    async saveApiConfig() {
        const url = document.getElementById('api-url').value.trim();
        const model = document.getElementById('api-model').value.trim();
        const apiKey = document.getElementById('api-key').value.trim();
        const statusDiv = document.getElementById('api-status');
        
        if (!url || !model) {
            statusDiv.innerHTML = '<span style="color: #dc3545;">Please enter API URL and model name</span>';
            return;
        }
        
        try {
            const response = await fetch('/api/ai/save-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    type: 'api',
                    url: url,
                    model: model,
                    api_key: apiKey 
                })
            });
            
            if (response.ok) {
                statusDiv.innerHTML = '<span style="color: #28a745;">✓ Configuration saved successfully!</span>';
                // Update query button status
                const queryBtn = document.getElementById('ai-query-btn');
                if (queryBtn) {
                    queryBtn.disabled = false;
                    queryBtn.title = '';
                }
            } else {
                statusDiv.innerHTML = '<span style="color: #dc3545;">✗ Failed to save configuration</span>';
            }
        } catch (error) {
            statusDiv.innerHTML = `<span style="color: #dc3545;">✗ Error: ${error.message}</span>`;
        }
    },

    loadApiConfig() {
        // Load saved API configuration
        fetch('/api/ai/get-config')
            .then(response => response.json())
            .then(config => {
                if (config.type === 'api') {
                    document.getElementById('api-url').value = config.url || '';
                    document.getElementById('api-model').value = config.model || '';
                    document.getElementById('api-key').value = config.api_key || '';
                    
                    const statusDiv = document.getElementById('api-status');
                    statusDiv.innerHTML = '<span style="color: #28a745;">✓ Configuration loaded</span>';
                }
            })
            .catch(() => {
                // No existing config, that's fine
            });
    }
};

// Model management functions
window.downloadModel = () => AIQueryComponent.downloadModel();
window.checkModelStatus = () => AIQueryComponent.checkModelStatus();
window.testApiConnection = () => AIQueryComponent.testApiConnection();
window.saveApiConfig = () => AIQueryComponent.saveApiConfig();

// Global functions for HTML handlers
window.submitAIQuery = () => AIQueryComponent.submitQuery();
window.setExampleQuery = (text) => AIQueryComponent.setExampleQuery(text);

// Initialize event listeners when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    AIQueryComponent.setupEventListeners();
});