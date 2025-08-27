/**
 * Projects Component
 * Handles project management, analytics, and dropdown functionality
 */

let projects = [];
let currentProjectAnalytics = null;

const ProjectsComponent = {
    /**
     * Load and display all projects
     */
    async loadProjects() {
        try {
            projects = await API.getProjects();
            this.renderProjectsList();
        } catch (error) {
            console.error('Error loading projects:', error);
            UI.showNotification('Error loading projects', 'error');
        }
    },
    
    /**
     * Render the projects list
     */
    renderProjectsList() {
        const list = document.getElementById('projects-list');
        if (!list) return;
        
        list.innerHTML = '';
        
        if (projects.length === 0) {
            list.innerHTML = '<p style="color: #6c757d; font-size: var(--base-font-size);">No projects created yet.</p>';
            return;
        }
        
        projects.forEach(project => {
            const div = document.createElement('div');
            div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid #dee2e6; border-left: 4px solid #007bff;';
            
            const netSpent = project.total_spent - project.total_earned;
            const spentElement = UI.createAmountElement(-Math.abs(netSpent));
            
            div.innerHTML = `
                <div onclick="showProjectAnalytics(${project.id})" style="cursor: pointer; flex: 1;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: calc(var(--base-font-size) * 1.14);">${project.name}</strong>
                            ${project.description ? `<br><small style="color: #6c757d; font-size: calc(var(--base-font-size) * 0.93);">${project.description}</small>` : ''}
                        </div>
                        <div style="text-align: right;">
                            ${spentElement.outerHTML}
                            <br><small style="color: #6c757d; font-size: calc(var(--base-font-size) * 0.93);">${project.transaction_count} transactions</small>
                        </div>
                    </div>
                </div>
                <div style="margin-left: 15px;">
                    <button class="btn btn-secondary" style="padding: 5px 10px; font-size: calc(var(--base-font-size) * 0.93); margin-right: 5px;" 
                            onclick="editProject(${project.id})">Edit</button>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: calc(var(--base-font-size) * 0.93);" 
                            onclick="deleteProject(${project.id})">Delete</button>
                </div>
            `;
            list.appendChild(div);
        });
    },
    
    /**
     * Show project analytics
     */
    async showProjectAnalytics(projectId) {
        try {
            currentProjectAnalytics = await API.getProjectAnalytics(projectId);
            
            // Hide projects list, show analytics
            document.getElementById('projects-list').parentElement.style.display = 'none';
            document.getElementById('project-analytics').style.display = 'block';
            
            // Update title
            document.getElementById('project-analytics-title').textContent = 
                `${currentProjectAnalytics.project.name} Analytics`;
            
            // Update project details
            this.renderProjectDetails();
            
            // Update stats
            document.getElementById('project-total-spent').textContent = 
                `£${currentProjectAnalytics.totals.total_spent.toFixed(2)}`;
            document.getElementById('project-total-earned').textContent = 
                `£${currentProjectAnalytics.totals.total_earned.toFixed(2)}`;
            document.getElementById('project-transaction-count').textContent = 
                currentProjectAnalytics.totals.transaction_count;
            
            // Calculate and display net spend (total_earned - total_spent)
            const netSpend = currentProjectAnalytics.totals.total_earned - currentProjectAnalytics.totals.total_spent;
            const netSpendElement = document.getElementById('project-net-spend');
            netSpendElement.textContent = `£${netSpend.toFixed(2)}`;
            
            // Color the net spend based on whether it's positive or negative
            if (netSpend >= 0) {
                netSpendElement.style.color = '#28a745'; // Green for positive (earned more than spent)
            } else {
                netSpendElement.style.color = '#dc3545'; // Red for negative (spent more than earned)
            }
            
            // Render pie chart
            this.renderCategoryChart();
            
            // Render transactions with filters
            this.renderProjectTransactions();
            
        } catch (error) {
            console.error('Error loading project analytics:', error);
            UI.showNotification('Error loading project analytics', 'error');
        }
    },
    
    /**
     * Render project details (category and notes)
     */
    renderProjectDetails() {
        const project = currentProjectAnalytics.project;
        let detailsHtml = '';
        
        if (project.category || project.notes) {
            detailsHtml = '<div style="background: var(--bg-secondary, #f8f9fa); padding: 15px; border-radius: 8px; margin-bottom: 20px;">';
            
            if (project.category) {
                detailsHtml += `<div style="margin-bottom: 10px;"><strong>Category:</strong> ${project.category}</div>`;
            }
            
            if (project.notes) {
                detailsHtml += `<div><strong>Notes:</strong> ${project.notes}</div>`;
            }
            
            detailsHtml += '</div>';
        }
        
        // Insert after the title but before the stats
        const analyticsContainer = document.getElementById('project-analytics');
        const titleElement = document.getElementById('project-analytics-title').parentElement;
        const existingDetails = document.getElementById('project-details');
        
        if (existingDetails) {
            existingDetails.remove();
        }
        
        if (detailsHtml) {
            const detailsDiv = document.createElement('div');
            detailsDiv.id = 'project-details';
            detailsDiv.innerHTML = detailsHtml;
            titleElement.insertAdjacentElement('afterend', detailsDiv);
        }
    },
    
    /**
     * Hide project analytics and return to projects list
     */
    hideProjectAnalytics() {
        document.getElementById('projects-list').parentElement.style.display = 'block';
        document.getElementById('project-analytics').style.display = 'none';
        currentProjectAnalytics = null;
    },
    
    /**
     * Render category pie chart
     */
    renderCategoryChart() {
        const canvas = document.getElementById('project-category-chart');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!currentProjectAnalytics.categories.length) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No spending data', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 20;
        
        const total = currentProjectAnalytics.categories.reduce((sum, cat) => sum + cat.total, 0);
        let currentAngle = -Math.PI / 2; // Start from top
        
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
        ];
        
        // Draw pie slices
        currentProjectAnalytics.categories.forEach((category, index) => {
            const sliceAngle = (category.total / total) * 2 * Math.PI;
            
            // Draw slice
            ctx.fillStyle = colors[index % colors.length];
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.closePath();
            ctx.fill();
            
            // Draw label
            const labelAngle = currentAngle + sliceAngle / 2;
            const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
            const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);
            
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            const percentage = ((category.total / total) * 100).toFixed(1);
            ctx.fillText(`${percentage}%`, labelX, labelY);
            
            currentAngle += sliceAngle;
        });
        
        // Draw legend
        const legendY = canvas.height - 100;
        currentProjectAnalytics.categories.forEach((category, index) => {
            const legendX = 20 + (index % 2) * 180;
            const legendYPos = legendY + Math.floor(index / 2) * 20;
            
            // Color box
            ctx.fillStyle = colors[index % colors.length];
            ctx.fillRect(legendX, legendYPos, 15, 15);
            
            // Legend text with background for dark mode compatibility
            const text = `${category.category || 'No category'}: £${category.total.toFixed(2)}`;
            ctx.font = '12px Arial';
            ctx.textAlign = 'left';
            
            // Measure text width for background box
            const textMetrics = ctx.measureText(text);
            const textWidth = textMetrics.width;
            const textHeight = 16;
            
            // Draw background box for text (semi-transparent white)
            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            ctx.fillRect(legendX + 18, legendYPos - 2, textWidth + 4, textHeight);
            
            // Draw border around text box
            ctx.strokeStyle = '#dee2e6';
            ctx.lineWidth = 1;
            ctx.strokeRect(legendX + 18, legendYPos - 2, textWidth + 4, textHeight);
            
            // Draw text
            ctx.fillStyle = '#333';
            ctx.fillText(text, legendX + 20, legendYPos + 12);
        });
    },
    
    /**
     * Render project transactions with filtering
     */
    renderProjectTransactions() {
        const container = document.getElementById('project-transactions');
        
        if (!currentProjectAnalytics.recent_transactions.length) {
            container.innerHTML = '<p style="color: #6c757d;">No transactions found.</p>';
            return;
        }
        
        // Create filters and table structure with unique IDs
        let html = `
            <div style="margin-bottom: 15px;">
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div class="form-group" style="flex: 1;">
                        <label style="font-size: 12px;">Category</label>
                        <select id="project-category-filter" onchange="filterProjectTransactions()" style="font-size: 12px; padding: 4px;">
                            <option value="">All Categories</option>
                        </select>
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label style="font-size: 12px;">From Date</label>
                        <input type="date" id="project-date-from" onchange="filterProjectTransactions()" style="font-size: 12px; padding: 4px;">
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label style="font-size: 12px;">To Date</label>
                        <input type="date" id="project-date-to" onchange="filterProjectTransactions()" style="font-size: 12px; padding: 4px;">
                    </div>
                </div>
            </div>
            <div style="height: 350px; overflow-y: auto; overflow-x: hidden; border: 1px solid #dee2e6; border-radius: 4px;">
                <table style="width: 100%; border-collapse: collapse; table-layout: fixed;">
                    <thead style="position: sticky; top: 0; background: white; z-index: 1; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                        <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                            <th style="width: 80px; padding: 8px; text-align: left; cursor: pointer; font-size: 12px;" onclick="sortProjectTransactions('date')">Date</th>
                            <th style="width: 80px; padding: 8px; text-align: left; font-size: 12px;">Account</th>
                            <th style="width: 70px; padding: 8px; text-align: left; font-size: 12px;">Payee</th>
                            <th style="width: 70px; padding: 8px; text-align: left; cursor: pointer; font-size: 12px;" onclick="sortProjectTransactions('category')">Category</th>
                            <th style="padding: 8px; text-align: left; font-size: 12px;">Notes</th>
                            <th style="width: 70px; padding: 8px; text-align: right; cursor: pointer; font-size: 12px;" onclick="sortProjectTransactions('amount')">Amount</th>
                        </tr>
                    </thead>
                    <tbody id="project-transactions-body">
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Populate category filter using global categories (like the main transactions page)
        this.populateProjectCategoryFilter();
        
        // Render all transactions initially
        this.renderFilteredTransactions(currentProjectAnalytics.recent_transactions);
    },
    
    /**
     * Populate project category filter using global categories
     */
    async populateProjectCategoryFilter() {
        try {
            const categories = await API.getCategories();
            const categoryFilter = document.getElementById('project-category-filter');
            
            if (categoryFilter) {
                // Clear existing options except the first "All Categories"
                categoryFilter.innerHTML = '<option value="">All Categories</option>';
                
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading categories for project filter:', error);
        }
    },

    /**
     * Render filtered transactions
     */
    renderFilteredTransactions(transactions) {
        const tbody = document.getElementById('project-transactions-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        transactions.forEach(t => {
            const row = document.createElement('tr');
            row.style.cssText = 'border-bottom: 1px solid #dee2e6;';
            row.onmouseover = () => row.style.backgroundColor = '#f8f9fa';
            row.onmouseout = () => row.style.backgroundColor = '';
            
            const amountElement = UI.createAmountElement(t.amount);
            
            row.innerHTML = `
                <td style="padding: 8px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.date}">${t.date}</td>
                <td style="padding: 8px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.account_name}">${t.account_name}</td>
                <td style="padding: 8px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.payee || '-'}">${t.payee || '-'}</td>
                <td style="padding: 8px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.category || '-'}">${t.category || '<span style="color: #6c757d;">-</span>'}</td>
                <td style="padding: 8px; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.notes || ''}">
                    ${t.notes || '<span style="color: #6c757d;">-</span>'}
                </td>
                <td style="padding: 8px; font-size: 12px; text-align: right;">${amountElement.outerHTML}</td>
            `;
            tbody.appendChild(row);
        });
    },
    
    /**
     * Filter transactions based on category and date
     */
    filterTransactions() {
        // Safety check for data availability
        if (!currentProjectAnalytics || !currentProjectAnalytics.recent_transactions) {
            console.warn('No project analytics data available for filtering');
            return;
        }
        
        const categoryFilter = document.getElementById('project-category-filter')?.value || '';
        const dateFromFilter = document.getElementById('project-date-from')?.value || '';
        const dateToFilter = document.getElementById('project-date-to')?.value || '';
        
        let filtered = currentProjectAnalytics.recent_transactions.filter(transaction => {
            // Category filter - handle null/undefined categories
            if (categoryFilter && (transaction.category || '') !== categoryFilter) {
                return false;
            }
            
            // Date filters - handle invalid dates
            if (dateFromFilter || dateToFilter) {
                const transactionDate = new Date(transaction.date);
                
                // Skip invalid dates
                if (isNaN(transactionDate.getTime())) {
                    return false;
                }
                
                if (dateFromFilter) {
                    const fromDate = new Date(dateFromFilter);
                    if (!isNaN(fromDate.getTime()) && transactionDate < fromDate) {
                        return false;
                    }
                }
                
                if (dateToFilter) {
                    const toDate = new Date(dateToFilter);
                    // Add end of day for "to date" inclusive filtering
                    toDate.setHours(23, 59, 59, 999);
                    if (!isNaN(toDate.getTime()) && transactionDate > toDate) {
                        return false;
                    }
                }
            }
            
            return true;
        });
        
        this.renderFilteredTransactions(filtered);
    },
    
    /**
     * Sort transactions by field
     */
    sortTransactions(field) {
        // Safety check for data availability
        if (!currentProjectAnalytics || !currentProjectAnalytics.recent_transactions) {
            console.warn('No project analytics data available for sorting');
            return;
        }
        
        const sorted = [...currentProjectAnalytics.recent_transactions].sort((a, b) => {
            let aVal = a[field];
            let bVal = b[field];
            
            if (field === 'date') {
                const dateA = new Date(a[field]);
                const dateB = new Date(b[field]);
                
                // Handle invalid dates
                if (isNaN(dateA.getTime()) && isNaN(dateB.getTime())) return 0;
                if (isNaN(dateA.getTime())) return 1;
                if (isNaN(dateB.getTime())) return -1;
                
                return dateB - dateA; // Most recent first
            }
            
            if (field === 'amount') {
                const numA = Number(a[field]) || 0;
                const numB = Number(b[field]) || 0;
                return numB - numA; // Largest amounts first
            }
            
            if (typeof aVal === 'string' || typeof bVal === 'string') {
                return (aVal || '').toString().localeCompare((bVal || '').toString());
            }
            
            return (aVal || 0) - (bVal || 0);
        });
        
        this.renderFilteredTransactions(sorted);
    },
    
    /**
     * Create or update project
     */
    async saveProject() {
        const name = document.getElementById('modal-project-name').value.trim();
        const description = document.getElementById('modal-project-description').value.trim();
        const category = document.getElementById('modal-project-category').value.trim();
        const notes = document.getElementById('modal-project-notes').value.trim();
        
        if (!name) {
            UI.showNotification('Project name is required', 'error');
            return;
        }
        
        try {
            const isEdit = appState.editingProject;
            const projectData = { name, description, category, notes };
            
            if (isEdit) {
                await API.updateProject(appState.editingProject.id, projectData);
                UI.showNotification('Project updated successfully');
            } else {
                await API.createProject(projectData);
                UI.showNotification('Project created successfully');
            }
            
            this.closeProjectModal();
            await this.loadProjects();
            await this.loadProjectDropdown(); // Update dropdown
        } catch (error) {
            console.error('Error saving project:', error);
            UI.showNotification('Error saving project', 'error');
        }
    },
    
    /**
     * Delete project
     */
    async deleteProject(projectId) {
        const confirmed = await UI.confirmAction('Are you sure you want to delete this project?');
        if (!confirmed) return;
        
        try {
            await API.deleteProject(projectId);
            UI.showNotification('Project deleted successfully');
            await this.loadProjects();
            await this.loadProjectDropdown(); // Update dropdown
        } catch (error) {
            console.error('Error deleting project:', error);
            UI.showNotification('Error deleting project', 'error');
        }
    },
    
    /**
     * Show create project modal
     */
    showCreateProjectModal() {
        appState.clearEditingProject();
        document.getElementById('project-modal-title').textContent = 'Add Project';
        document.getElementById('modal-project-name').value = '';
        document.getElementById('modal-project-description').value = '';
        document.getElementById('modal-project-category').value = '';
        document.getElementById('modal-project-notes').value = '';
        UI.showModal('projectModal');
    },
    
    /**
     * Show edit project modal
     */
    editProject(projectId) {
        const project = projects.find(p => p.id === projectId);
        if (!project) return;
        
        appState.setEditingProject(project);
        document.getElementById('project-modal-title').textContent = 'Edit Project';
        document.getElementById('modal-project-name').value = project.name;
        document.getElementById('modal-project-description').value = project.description || '';
        document.getElementById('modal-project-category').value = project.category || '';
        document.getElementById('modal-project-notes').value = project.notes || '';
        UI.showModal('projectModal');
    },
    
    /**
     * Close project modal
     */
    closeProjectModal() {
        UI.hideModal('projectModal');
        appState.clearEditingProject();
    },
    
    /**
     * Load project dropdown for transaction form
     */
    async loadProjectDropdown() {
        try {
            const projectNames = await API.getProjectNames();
            const dropdown = document.getElementById('project-dropdown');
            
            if (!dropdown) return;
            
            dropdown.innerHTML = '';
            
            // Add "Create New Project" option
            const createOption = document.createElement('div');
            createOption.className = 'dropdown-item';
            createOption.textContent = '+ Create New Project';
            createOption.style.fontStyle = 'italic';
            createOption.style.color = '#007bff';
            createOption.onclick = () => {
                document.getElementById('project').value = '';
                this.hideProjectDropdown();
                this.showCreateProjectModal();
            };
            dropdown.appendChild(createOption);
            
            if (projectNames.length > 0) {
                // Add separator
                const separator = document.createElement('div');
                separator.style.borderTop = '1px solid #dee2e6';
                separator.style.margin = '5px 0';
                dropdown.appendChild(separator);
                
                // Add existing projects
                projectNames.forEach(project => {
                    const option = document.createElement('div');
                    option.className = 'dropdown-item';
                    option.textContent = project.name;
                    option.onclick = () => {
                        document.getElementById('project').value = project.name;
                        this.hideProjectDropdown();
                    };
                    dropdown.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading project dropdown:', error);
        }
    },
    
    /**
     * Filter projects in dropdown
     */
    filterProjects() {
        const searchTerm = document.getElementById('project').value.toLowerCase();
        const dropdown = document.getElementById('project-dropdown');
        const items = dropdown.querySelectorAll('.dropdown-item');
        
        items.forEach(item => {
            if (item.textContent.includes('Create New Project')) {
                item.style.display = 'block'; // Always show create option
            } else {
                const isMatch = item.textContent.toLowerCase().includes(searchTerm);
                item.style.display = isMatch ? 'block' : 'none';
            }
        });
    },
    
    /**
     * Show project dropdown
     */
    showProjectDropdown() {
        document.getElementById('project-dropdown').style.display = 'block';
    },
    
    /**
     * Hide project dropdown
     */
    hideProjectDropdown() {
        setTimeout(() => {
            document.getElementById('project-dropdown').style.display = 'none';
        }, 200);
    },

    /**
     * Load project dropdown for edit transaction form
     */
    async loadEditProjectDropdown() {
        try {
            const projectNames = await API.getProjectNames();
            const dropdown = document.getElementById('edit-project-dropdown');
            
            if (!dropdown) return;
            
            dropdown.innerHTML = '';
            
            // Add "Create New Project" option
            const createOption = document.createElement('div');
            createOption.className = 'dropdown-item';
            createOption.textContent = '+ Create New Project';
            createOption.style.fontStyle = 'italic';
            createOption.style.color = '#007bff';
            createOption.onclick = () => {
                document.getElementById('edit-transaction-project').value = '';
                this.hideEditProjectDropdown();
                this.showCreateProjectModal();
            };
            dropdown.appendChild(createOption);
            
            if (projectNames.length > 0) {
                // Add separator
                const separator = document.createElement('div');
                separator.style.borderTop = '1px solid #dee2e6';
                separator.style.margin = '5px 0';
                dropdown.appendChild(separator);
                
                // Add existing projects
                projectNames.forEach(project => {
                    const option = document.createElement('div');
                    option.className = 'dropdown-item';
                    option.textContent = project.name;
                    option.onclick = () => {
                        document.getElementById('edit-transaction-project').value = project.name;
                        this.hideEditProjectDropdown();
                    };
                    dropdown.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading edit project dropdown:', error);
        }
    },
    
    /**
     * Filter projects in edit dropdown
     */
    filterEditProjects() {
        const searchTerm = document.getElementById('edit-transaction-project').value.toLowerCase();
        const dropdown = document.getElementById('edit-project-dropdown');
        const items = dropdown.querySelectorAll('.dropdown-item');
        
        items.forEach(item => {
            if (item.textContent.includes('Create New Project')) {
                item.style.display = 'block'; // Always show create option
            } else {
                const isMatch = item.textContent.toLowerCase().includes(searchTerm);
                item.style.display = isMatch ? 'block' : 'none';
            }
        });
    },
    
    /**
     * Show edit project dropdown
     */
    showEditProjectDropdown() {
        this.loadEditProjectDropdown();
        document.getElementById('edit-project-dropdown').style.display = 'block';
    },
    
    /**
     * Hide edit project dropdown
     */
    hideEditProjectDropdown() {
        setTimeout(() => {
            document.getElementById('edit-project-dropdown').style.display = 'none';
        }, 200);
    }
};

// Global functions for HTML onclick handlers
window.showProjectAnalytics = (projectId) => ProjectsComponent.showProjectAnalytics(projectId);
window.hideProjectAnalytics = () => ProjectsComponent.hideProjectAnalytics();
window.showCreateProjectModal = () => ProjectsComponent.showCreateProjectModal();
window.editProject = (projectId) => ProjectsComponent.editProject(projectId);
window.deleteProject = (projectId) => ProjectsComponent.deleteProject(projectId);
window.saveProject = () => ProjectsComponent.saveProject();
window.closeProjectModal = () => ProjectsComponent.closeProjectModal();
window.filterProjects = () => ProjectsComponent.filterProjects();
window.showProjectDropdown = () => ProjectsComponent.showProjectDropdown();
window.hideProjectDropdown = () => ProjectsComponent.hideProjectDropdown();
window.filterEditProjects = () => ProjectsComponent.filterEditProjects();
window.showEditProjectDropdown = () => ProjectsComponent.showEditProjectDropdown();
window.hideEditProjectDropdown = () => ProjectsComponent.hideEditProjectDropdown();

// Global functions for project analytics transaction filtering
window.filterProjectTransactions = () => ProjectsComponent.filterTransactions();
window.sortProjectTransactions = (field) => ProjectsComponent.sortTransactions(field);