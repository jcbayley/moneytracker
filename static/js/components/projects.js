/**
 * Projects Component
 * Handles project management, analytics, and dropdown functionality
 */

let projects = [];
let currentProjectAnalytics = null;

class ProjectsComponent {
    /**
     * Load and display all projects
     */
    static async loadProjects() {
        try {
            projects = await API.getProjects();
            this.renderProjectsList();
        } catch (error) {
            console.error('Error loading projects:', error);
            UI.showNotification('Error loading projects', 'error');
        }
    }
    
    /**
     * Render the projects list
     */
    static renderProjectsList() {
        const list = document.getElementById('projects-list');
        if (!list) return;
        
        list.innerHTML = '';
        
        if (projects.length === 0) {
            list.innerHTML = '<p style="color: #6c757d;">No projects created yet.</p>';
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
                            <strong style="font-size: 16px;">${project.name}</strong>
                            ${project.description ? `<br><small style="color: #6c757d;">${project.description}</small>` : ''}
                        </div>
                        <div style="text-align: right;">
                            ${spentElement.outerHTML}
                            <br><small style="color: #6c757d;">${project.transaction_count} transactions</small>
                        </div>
                    </div>
                </div>
                <div style="margin-left: 15px;">
                    <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 12px; margin-right: 5px;" 
                            onclick="editProject(${project.id})">Edit</button>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" 
                            onclick="deleteProject(${project.id})">Delete</button>
                </div>
            `;
            list.appendChild(div);
        });
    }
    
    /**
     * Show project analytics
     */
    static async showProjectAnalytics(projectId) {
        try {
            currentProjectAnalytics = await API.getProjectAnalytics(projectId);
            
            // Hide projects list, show analytics
            document.getElementById('projects-list').parentElement.style.display = 'none';
            document.getElementById('project-analytics').style.display = 'block';
            
            // Update title
            document.getElementById('project-analytics-title').textContent = 
                `${currentProjectAnalytics.project.name} Analytics`;
            
            // Update stats
            document.getElementById('project-total-spent').textContent = 
                `£${currentProjectAnalytics.totals.total_spent.toFixed(2)}`;
            document.getElementById('project-total-earned').textContent = 
                `£${currentProjectAnalytics.totals.total_earned.toFixed(2)}`;
            document.getElementById('project-transaction-count').textContent = 
                currentProjectAnalytics.totals.transaction_count;
            
            // Render pie chart
            this.renderCategoryChart();
            
            // Render recent transactions
            this.renderRecentTransactions();
            
        } catch (error) {
            console.error('Error loading project analytics:', error);
            UI.showNotification('Error loading project analytics', 'error');
        }
    }
    
    /**
     * Hide project analytics and return to projects list
     */
    static hideProjectAnalytics() {
        document.getElementById('projects-list').parentElement.style.display = 'block';
        document.getElementById('project-analytics').style.display = 'none';
        currentProjectAnalytics = null;
    }
    
    /**
     * Render category pie chart
     */
    static renderCategoryChart() {
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
            
            // Label
            ctx.fillStyle = '#333';
            ctx.font = '12px Arial';
            ctx.textAlign = 'left';
            ctx.fillText(`${category.category || 'No category'}: £${category.total.toFixed(2)}`, 
                         legendX + 20, legendYPos + 12);
        });
    }
    
    /**
     * Render recent transactions for project
     */
    static renderRecentTransactions() {
        const container = document.getElementById('project-transactions');
        
        if (!currentProjectAnalytics.recent_transactions.length) {
            container.innerHTML = '<p style="color: #6c757d;">No transactions found.</p>';
            return;
        }
        
        let html = '<table style="width: 100%; border-collapse: collapse;">';
        html += '<thead><tr style="background: #f8f9fa;"><th style="padding: 8px; text-align: left;">Date</th><th style="padding: 8px; text-align: left;">Account</th><th style="padding: 8px; text-align: left;">Payee</th><th style="padding: 8px; text-align: right;">Amount</th></tr></thead>';
        html += '<tbody>';
        
        currentProjectAnalytics.recent_transactions.forEach(t => {
            const amountElement = UI.createAmountElement(t.amount);
            html += `
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px;">${t.date}</td>
                    <td style="padding: 8px;">${t.account_name}</td>
                    <td style="padding: 8px;">${t.payee || '-'}</td>
                    <td style="padding: 8px; text-align: right;">${amountElement.outerHTML}</td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
    }
    
    /**
     * Create or update project
     */
    static async saveProject() {
        const name = document.getElementById('modal-project-name').value.trim();
        const description = document.getElementById('modal-project-description').value.trim();
        
        if (!name) {
            UI.showNotification('Project name is required', 'error');
            return;
        }
        
        try {
            const isEdit = appState.editingProject;
            
            if (isEdit) {
                await API.updateProject(appState.editingProject.id, { name, description });
                UI.showNotification('Project updated successfully');
            } else {
                await API.createProject({ name, description });
                UI.showNotification('Project created successfully');
            }
            
            this.closeProjectModal();
            await this.loadProjects();
            await this.loadProjectDropdown(); // Update dropdown
        } catch (error) {
            console.error('Error saving project:', error);
            UI.showNotification('Error saving project', 'error');
        }
    }
    
    /**
     * Delete project
     */
    static async deleteProject(projectId) {
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
    }
    
    /**
     * Show create project modal
     */
    static showCreateProjectModal() {
        appState.clearEditingProject();
        document.getElementById('project-modal-title').textContent = 'Add Project';
        document.getElementById('modal-project-name').value = '';
        document.getElementById('modal-project-description').value = '';
        UI.showModal('projectModal');
    }
    
    /**
     * Show edit project modal
     */
    static editProject(projectId) {
        const project = projects.find(p => p.id === projectId);
        if (!project) return;
        
        appState.setEditingProject(project);
        document.getElementById('project-modal-title').textContent = 'Edit Project';
        document.getElementById('modal-project-name').value = project.name;
        document.getElementById('modal-project-description').value = project.description || '';
        UI.showModal('projectModal');
    }
    
    /**
     * Close project modal
     */
    static closeProjectModal() {
        UI.hideModal('projectModal');
        appState.clearEditingProject();
    }
    
    /**
     * Load project dropdown for transaction form
     */
    static async loadProjectDropdown() {
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
    }
    
    /**
     * Filter projects in dropdown
     */
    static filterProjects() {
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
    }
    
    /**
     * Show project dropdown
     */
    static showProjectDropdown() {
        document.getElementById('project-dropdown').style.display = 'block';
    }
    
    /**
     * Hide project dropdown
     */
    static hideProjectDropdown() {
        setTimeout(() => {
            document.getElementById('project-dropdown').style.display = 'none';
        }, 200);
    }
}

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