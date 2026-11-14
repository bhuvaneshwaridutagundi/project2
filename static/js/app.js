// Prompt Injection Security Gateway - Frontend JavaScript

class SecurityGatewayUI {
    constructor() {
        this.healthInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkHealth();
        this.loadLogs();
        this.startHealthCheck();
    }

    setupEventListeners() {
        // Text scan form
        const scanForm = document.getElementById('scan-form');
        if (scanForm) {
            scanForm.addEventListener('submit', (e) => this.handleTextScan(e));
        }

        // File upload form
        const fileForm = document.getElementById('file-form');
        if (fileForm) {
            fileForm.addEventListener('submit', (e) => this.handleFileScan(e));
        }
    }

    startHealthCheck() {
        this.healthInterval = setInterval(() => this.checkHealth(), 30000);
    }

    async checkHealth() {
        const healthStatus = document.getElementById('health-status');
        const statusText = document.getElementById('status-text');
        const llmStatus = document.getElementById('llm-status');
        const llmBadge = document.getElementById('llm-status')?.querySelector('.badge');

        try {
            const response = await fetch('/health');
            const data = await response.json();

            if (healthStatus) {
                healthStatus.classList.remove('d-none');
            }

            if (statusText) {
                statusText.textContent = data.status || 'Unknown';
            }

            if (llmBadge) {
                llmBadge.textContent = data.llm_configured ? data.provider : 'Not Configured';
                llmBadge.className = data.llm_configured ? 'badge' : 'badge bg-secondary';
            }
        } catch (error) {
            if (statusText) {
                statusText.textContent = 'Unreachable';
                healthStatus?.classList.remove('d-none');
            }
        }
    }

    async handleTextScan(e) {
        e.preventDefault();

        const text = document.getElementById('prompt-text').value.trim();
        if (!text) {
            alert('Please enter a prompt to scan.');
            return;
        }

        if (e.submitter?.dataset.action === 'ask') {
            await this.askText(text);
        } else {
            await this.scanText(text);
        }
    }

    async handleFileScan(e) {
        e.preventDefault();

        const fileInput = document.getElementById('file-input');
        const file = fileInput.files[0];

        if (!file) {
            alert('Please select a file to scan.');
            return;
        }

        await this.scanFile(file);
    }

    async scanText(text) {
        this.showLoading(true);

        try {
            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || `Scan failed (${response.status}).`);
            }
            this.displayResult(data);
        } catch (error) {
            this.showError(`Scan failed: ${error.message || 'Unknown error during scan.'}`);
        } finally {
            this.showLoading(false);
            this.loadLogs(); // Update logs on completion/failure
        }
    }

    async askText(text) {
        this.showLoading(true);

        try {
            let data = await this.requestAsk(text, false);
            this.displayResult(data);

            if (
                data.decision === 'FLAG' &&
                data.requires_confirmation &&
                !data.forwarded_to_llm &&
                window.confirm(`${data.message}\n\nSend this flagged prompt to Gemini anyway?`)
            ) {
                data = await this.requestAsk(text, true);
                this.displayResult(data);
            }
        } catch (error) {
            this.showError(`Gemini request failed: ${error.message || 'Unknown error.'}`);
        } finally {
            this.showLoading(false);
            this.loadLogs();
        }
    }

    async requestAsk(text, flagConfirmation) {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                flag_confirmation: flagConfirmation,
            }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.message || `Gemini request failed (${response.status}).`);
        }
        return data;
    }

    async scanFile(file) {
        this.showLoading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/scan-file', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || `File scan failed (${response.status}).`);
            }
            this.displayResult(data);
        } catch (error) {
            this.showError(error.message || 'Network error during file scan.');
        } finally {
            this.showLoading(false);
            this.loadLogs();
        }
    }

    displayResult(data) {
        const resultPanel = document.getElementById('result-panel');
        const emptyResult = document.getElementById('empty-result');

        if (resultPanel) {
            resultPanel.classList.remove('d-none');
        }
        if (emptyResult) {
            emptyResult.classList.add('d-none');
        }

        // Decision badge
        const decisionBadge = document.getElementById('decision-badge');
        if (decisionBadge) {
            decisionBadge.textContent = data.decision;
            decisionBadge.className = `badge badge-${data.decision}`;
        }

        // Risk score
        const riskScore = document.getElementById('risk-score');
        if (riskScore) {
            riskScore.textContent = data.risk_score;
        }

        const riskSeverity = document.getElementById('risk-severity');
        if (riskSeverity) {
            riskSeverity.textContent = data.severity || '--';
        }

        const decisionMessage = document.getElementById('decision-message');
        if (decisionMessage) {
            decisionMessage.textContent = data.message || '';
        }

        // Findings
        this.displayFindings(data.findings);

        // AI response
        const aiResponse = document.getElementById('ai-response');
        if (aiResponse) {
            if (data.answer) {
                aiResponse.innerHTML = `<h6 class="mb-2">AI Response:</h6><p class="mb-0">${this.escapeHtml(data.answer)}</p>`;
                aiResponse.classList.remove('d-none');
            } else {
                aiResponse.classList.add('d-none');
            }
        }

        // Error message
        const errorAlert = document.getElementById('error-alert');
        if (errorAlert) {
            errorAlert.classList.add('d-none');
            if (data.error) {
                errorAlert.textContent = data.error;
                errorAlert.classList.remove('d-none', 'alert-info');
                errorAlert.classList.add('alert-warning');
            }
        }

        // Response time
        const responseTime = document.getElementById('response-time');
        if (responseTime) {
            const now = new Date();
            responseTime.textContent = now.toLocaleTimeString();
        }
    }

    displayFindings(findings) {
        const container = document.getElementById('findings-container');
        if (!container) return;

        if (!findings || findings.length === 0) {
            container.innerHTML = '<p class="text-muted">No suspicious indicators detected.</p>';
            return;
        }

        const list = document.createElement('ul');
        list.className = 'list-group findings-list';

        findings.forEach(finding => {
            const li = document.createElement('li');
            li.className = `warning ${finding.severity === 'HIGH' ? 'danger' : 'warning'}`;

            li.innerHTML = `
                <div class="d-flex justify-content-between">
                    <strong>${finding.code}</strong>
                    <span class="badge badge-${this.getSeverityBadge(finding.severity)}">${finding.severity}</span>
                </div>
                <small class="code text-muted">Source: ${finding.source}</small>
                <p class="mb-0 message">${finding.message}</p>
                ${finding.evidence ? `<small class="text-muted d-block mt-1">"...${finding.evidence}..."</small>` : ''}
            `;
            list.appendChild(li);
        });

        container.innerHTML = '';
        container.appendChild(list);
    }

    getSeverityBadge(severity) {
        const map = {
            'LOW': 'ALLOW',
            'MEDIUM': 'FLAG',
            'HIGH': 'BLOCK',
            'CRITICAL': 'BLOCK',
        };
        return map[severity] || 'FLAG';
    }

    showLoading(show) {
        const scanForm = document.getElementById('scan-form');
        const fileForm = document.getElementById('file-form');
        const submitBtns = document.querySelectorAll('button[type="submit"]');

        if (scanForm) scanForm.style.opacity = show ? '0.6' : '';
        if (fileForm) fileForm.style.opacity = show ? '0.6' : '';

        submitBtns.forEach(btn => {
            if (show) {
                if (!btn.dataset.idleHtml) {
                    btn.dataset.idleHtml = btn.innerHTML;
                }
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Working...';
            } else {
                btn.disabled = false;
                if (btn.dataset.idleHtml) {
                    btn.innerHTML = btn.dataset.idleHtml;
                    delete btn.dataset.idleHtml;
                }
            }
        });
    }

    showError(message) {
        const errorAlert = document.getElementById('error-alert');
        if (errorAlert) {
            errorAlert.textContent = message;
            errorAlert.classList.remove('d-none', 'alert-info', 'alert-warning');
            errorAlert.classList.add('alert-warning');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadLogs() {
        const container = document.getElementById('logs-container');
        if (!container) return;

        try {
            const response = await fetch('/api/logs?limit=10');
            const data = await response.json();

            if (!data.logs || data.logs.length === 0) {
                container.innerHTML = '<p class="text-muted">No scan history yet.</p>';
                return;
            }

            const list = document.createElement('div');
            list.className = 'list-group';

            data.logs.forEach(log => {
                const item = document.createElement('div');
                item.className = 'list-group-item';

                const decisionClass = `logs-badge-${log.decision}`;
                const decisionBadge = `<span class="badge ${decisionClass} mb-2">${log.decision}</span>`;

                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            ${decisionBadge}
                            <div class="small text-muted">
                                <span class="fw-medium">${log.input_type}</span> •
                                <span>${log.risk_score}</span> •
                                <span>${new Date(log.timestamp).toLocaleString()}</span>
                            </div>
                            ${log.file_extension ? `<small class="text-muted">File: ${log.file_extension}</small>` : ''}
                        </div>
                    </div>
                `;
                list.appendChild(item);
            });

            container.innerHTML = '';
            container.appendChild(list);
        } catch (error) {
            container.innerHTML = '<p class="text-danger">Error loading logs.</p>';
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new SecurityGatewayUI());
} else {
    new SecurityGatewayUI();
}

// Export for testing
window.SecurityGatewayUI = SecurityGatewayUI;