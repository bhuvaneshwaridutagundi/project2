const SVG_NS = 'http://www.w3.org/2000/svg';

class SecurityGatewayUI {
    constructor() {
        this.logs = [];
        this.summary = null;
        this.selectedFile = null;
        this.maxUploadBytes = null;
        this.busy = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupNavigation();
        this.checkHealth();
        this.loadLogs();
        this.healthInterval = window.setInterval(() => this.checkHealth(), 30000);
    }

    setupEventListeners() {
        document.getElementById('scan-form')?.addEventListener('submit', (event) => {
            this.handleTextScan(event);
        });
        document.getElementById('file-form')?.addEventListener('submit', (event) => {
            this.handleFileScan(event);
        });
        document.getElementById('prompt-text')?.addEventListener('input', (event) => {
            this.updateCharacterCount(event.target.value);
        });
        document.getElementById('clear-prompt')?.addEventListener('click', () => {
            const prompt = document.getElementById('prompt-text');
            prompt.value = '';
            this.updateCharacterCount('');
            prompt.focus();
        });

        const fileInput = document.getElementById('file-input');
        const dropZone = document.getElementById('drop-zone');
        fileInput?.addEventListener('change', () => {
            this.selectFile(fileInput.files?.[0] || null);
        });
        dropZone?.addEventListener('click', () => fileInput?.click());
        dropZone?.addEventListener('dragover', (event) => {
            event.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone?.addEventListener('dragleave', (event) => {
            if (!dropZone.contains(event.relatedTarget)) {
                dropZone.classList.remove('drag-over');
            }
        });
        dropZone?.addEventListener('drop', (event) => {
            event.preventDefault();
            dropZone.classList.remove('drag-over');
            this.selectFile(event.dataTransfer?.files?.[0] || null);
        });
        document.getElementById('remove-file')?.addEventListener('click', () => {
            this.clearSelectedFile();
        });

        document.getElementById('scan-search')?.addEventListener('input', () => {
            this.renderHistory();
        });
        document.getElementById('decision-filter')?.addEventListener('change', () => {
            this.renderHistory();
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeMobileNavigation();
            }
        });
    }

    setupNavigation() {
        const sidebar = document.getElementById('sidebar');
        document.getElementById('menu-toggle')?.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-open');
        });
        document.getElementById('sidebar-scrim')?.addEventListener('click', () => {
            this.closeMobileNavigation();
        });
        document.querySelectorAll('.side-nav .nav-link').forEach((link) => {
            link.addEventListener('click', () => {
                this.closeMobileNavigation();
                this.setActiveSection(link.dataset.section);
            });
        });
        document.querySelectorAll('.page-section').forEach((section) => {
            section.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') {
                    this.closeMobileNavigation();
                }
            });
        });

        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                const visible = entries
                    .filter((entry) => entry.isIntersecting)
                    .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
                if (visible) {
                    this.setActiveSection(visible.target.id);
                }
            }, { rootMargin: '-15% 0px -68% 0px', threshold: [0, 0.1, 0.3] });
            document.querySelectorAll('.page-section').forEach((section) => observer.observe(section));
        }
    }

    closeMobileNavigation() {
        document.body.classList.remove('sidebar-open');
    }

    setActiveSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (!section) return;
        document.querySelectorAll('.side-nav .nav-link').forEach((link) => {
            const isActive = link.dataset.section === sectionId;
            link.classList.toggle('active', isActive);
            if (isActive) link.setAttribute('aria-current', 'page');
            else link.removeAttribute('aria-current');
        });
        const pageTitle = section.dataset.pageTitle || 'Dashboard';
        const currentPage = document.getElementById('current-page');
        if (currentPage) currentPage.textContent = pageTitle;
    }

    async checkHealth() {
        try {
            const response = await fetch('/health', { headers: { Accept: 'application/json' } });
            const data = await response.json();
            if (!response.ok || data.status !== 'healthy') {
                throw new Error('Gateway is unavailable.');
            }

            if (Number.isFinite(Number(data.max_upload_size_bytes)) && Number(data.max_upload_size_bytes) > 0) {
                this.maxUploadBytes = Number(data.max_upload_size_bytes);
            }
            this.renderHealth(data);
        } catch (_error) {
            this.renderHealth(null);
        }
    }

    renderHealth(data) {
        const isOnline = Boolean(data);
        const statusText = document.getElementById('status-text');
        const sidebarHealth = document.getElementById('sidebar-health');
        if (statusText) statusText.textContent = isOnline ? 'Gateway online' : 'Gateway offline';
        if (sidebarHealth) sidebarHealth.textContent = isOnline ? 'Gateway operational' : 'Gateway unavailable';

        document.querySelectorAll('.gateway-status .status-pulse, .sidebar-version .status-pulse').forEach((pulse) => {
            pulse.classList.toggle('offline', !isOnline);
        });

        const llmConfigured = Boolean(data?.llm_configured);
        this.setText('settings-health', isOnline ? 'Operational' : 'Unavailable');
        this.setText(
            'settings-provider',
            llmConfigured ? (data.provider || 'Configured') : 'Not configured'
        );
        this.setText('settings-model', llmConfigured ? (data.model || 'Provider default') : '—');

        if (this.maxUploadBytes) {
            const limit = this.formatBytes(this.maxUploadBytes);
            this.setText('upload-limit', limit);
            this.setText('settings-upload-limit', limit);
            const selectedFile = this.selectedFile;
            if (selectedFile && selectedFile.size > this.maxUploadBytes) {
                this.clearSelectedFile();
                this.showToast(`The selected file exceeds the ${limit} upload limit.`);
            }
        } else {
            this.setText('upload-limit', 'configured limit');
            this.setText('settings-upload-limit', 'Configured by gateway');
        }
    }

    async handleTextScan(event) {
        event.preventDefault();
        if (this.busy) return;

        const text = document.getElementById('prompt-text').value.trim();
        if (!text) {
            this.showToast('Enter a prompt before starting a scan.');
            document.getElementById('prompt-text').focus();
            return;
        }

        this.setBusy(true);
        try {
            if (event.submitter?.dataset.action === 'ask') {
                await this.askText(text);
            } else {
                await this.scanText(text);
            }
        } finally {
            this.setBusy(false);
            this.loadLogs();
        }
    }

    async scanText(text) {
        try {
            const data = await this.requestJson('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            this.displayResult(data);
        } catch (error) {
            this.showError(`Scan failed: ${error.message}`);
        }
    }

    async askText(text) {
        try {
            let data = await this.requestJson('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, flag_confirmation: false }),
            });
            this.displayResult(data);

            if (
                data.decision === 'FLAG' &&
                data.requires_confirmation &&
                !data.forwarded_to_llm &&
                await this.confirmFlag(data.message)
            ) {
                data = await this.requestJson('/api/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, flag_confirmation: true }),
                });
                this.displayResult(data);
            }
        } catch (error) {
            this.showError(`AI request failed: ${error.message}`);
        }
    }

    confirmFlag(message) {
        const dialog = document.getElementById('flag-confirm-dialog');
        const confirmMessage = document.getElementById('confirm-message');
        if (!dialog || typeof dialog.showModal !== 'function') {
            return Promise.resolve(window.confirm(
                `${message || 'This prompt has been flagged for review.'}\n\nSend it to the configured LLM anyway?`
            ));
        }
        confirmMessage.textContent = message || 'Review the findings before deciding whether to continue.';
        return new Promise((resolve) => {
            const onClose = () => {
                dialog.removeEventListener('close', onClose);
                resolve(dialog.returnValue === 'confirm');
            };
            dialog.addEventListener('close', onClose);
            dialog.showModal();
        });
    }

    async requestJson(url, options) {
        const response = await fetch(url, options);
        let data;
        try {
            data = await response.json();
        } catch (_error) {
            throw new Error(`The server returned an invalid response (${response.status}).`);
        }
        if (!response.ok) {
            throw new Error(data.message || data.error || `Request failed (${response.status}).`);
        }
        return data;
    }

    handleFileScan(event) {
        event.preventDefault();
        if (this.busy) return;
        const file = this.selectedFile || document.getElementById('file-input').files?.[0];
        if (!file) {
            this.showToast('Choose a document before starting a scan.');
            return;
        }

        this.setBusy(true);
        this.setUploadProgress(0, 'Uploading document');
        this.uploadFile(file)
            .then((data) => this.displayResult(data))
            .catch((error) => this.showError(`Document scan failed: ${error.message}`))
            .finally(() => {
                this.setBusy(false);
                window.setTimeout(() => this.hideUploadProgress(), 700);
                this.loadLogs();
            });
    }

    uploadFile(file) {
        return new Promise((resolve, reject) => {
            const request = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);
            request.open('POST', '/api/scan-file');
            request.responseType = 'json';
            request.timeout = 120000;

            request.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    this.setUploadProgress(
                        Math.round((event.loaded / event.total) * 100),
                        event.loaded === event.total ? 'Analyzing extracted content' : 'Uploading document'
                    );
                }
            });
            request.addEventListener('load', () => {
                const data = request.response;
                if (request.status < 200 || request.status >= 300) {
                    reject(new Error(data?.message || `Request failed (${request.status}).`));
                    return;
                }
                if (!data || typeof data !== 'object') {
                    reject(new Error('The server returned an invalid response.'));
                    return;
                }
                this.setUploadProgress(100, 'Scan complete');
                resolve(data);
            });
            request.addEventListener('error', () => reject(new Error('Unable to reach the gateway.')));
            request.addEventListener('timeout', () => reject(new Error('The document scan timed out.')));
            request.addEventListener('abort', () => reject(new Error('The document scan was canceled.')));
            request.send(formData);
        });
    }

    selectFile(file) {
        if (!file) return;
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        if (!['txt', 'pdf', 'docx'].includes(extension)) {
            this.clearSelectedFile();
            this.showToast('Unsupported file type. Choose a TXT, PDF, or DOCX document.');
            return;
        }
        if (this.maxUploadBytes && file.size > this.maxUploadBytes) {
            this.clearSelectedFile();
            this.showToast(`The selected file exceeds the ${this.formatBytes(this.maxUploadBytes)} upload limit.`);
            return;
        }

        this.selectedFile = file;
        this.setText('file-name', file.name);
        this.setText('file-size', this.formatBytes(file.size));
        this.setText('file-type-mark', extension.toUpperCase());
        document.getElementById('file-details').hidden = false;
        document.getElementById('drop-zone').hidden = true;
        document.getElementById('file-submit').disabled = false;
        this.hideUploadProgress();
    }

    clearSelectedFile() {
        this.selectedFile = null;
        const input = document.getElementById('file-input');
        if (input) input.value = '';
        const fileDetails = document.getElementById('file-details');
        if (fileDetails) fileDetails.hidden = true;
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) dropZone.hidden = false;
        const submit = document.getElementById('file-submit');
        if (submit) submit.disabled = true;
        this.hideUploadProgress();
    }

    setUploadProgress(value, label) {
        const progress = document.getElementById('upload-progress');
        if (!progress) return;
        progress.hidden = false;
        this.setText('progress-label', label);
        this.setText('progress-value', `${value}%`);
        const fill = document.getElementById('progress-fill');
        if (fill) fill.style.width = `${Math.max(0, Math.min(100, value))}%`;
    }

    hideUploadProgress() {
        const progress = document.getElementById('upload-progress');
        if (progress) progress.hidden = true;
    }

    displayResult(data) {
        const panel = document.getElementById('result-panel');
        panel.hidden = false;
        const decision = ['ALLOW', 'FLAG', 'BLOCK'].includes(data.decision) ? data.decision : 'BLOCK';
        const score = Math.max(0, Math.min(100, Number(data.risk_score) || 0));
        const badge = document.getElementById('decision-badge');
        badge.textContent = decision;
        badge.className = `decision-badge decision-${decision}`;
        this.setText('result-scan-id', data.scan_id ? `SCAN ${data.scan_id}` : '');
        this.setText('risk-score', String(score));
        this.setText('risk-severity', data.severity || '—');
        this.setText('decision-message', data.message || 'Scan completed.');

        const scoreFill = document.getElementById('score-fill');
        scoreFill.style.width = `${score}%`;
        scoreFill.style.setProperty(
            '--score-color',
            decision === 'BLOCK' ? 'var(--red)' : decision === 'FLAG' ? 'var(--amber)' : 'var(--green)'
        );
        document.getElementById('result-summary').dataset.decision = decision;
        this.renderFindings(data.findings);

        const aiResponse = document.getElementById('ai-response');
        aiResponse.hidden = !data.answer;
        this.setText('ai-response-text', data.answer || '');

        const errorAlert = document.getElementById('error-alert');
        errorAlert.hidden = !data.error;
        errorAlert.textContent = data.error || '';
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    renderFindings(findings) {
        const container = document.getElementById('findings-container');
        container.replaceChildren();
        if (!Array.isArray(findings) || findings.length === 0) {
            const message = document.createElement('p');
            message.className = 'muted-copy';
            message.textContent = 'No suspicious indicators were detected.';
            container.appendChild(message);
            return;
        }

        const list = document.createElement('div');
        list.className = 'findings-list';
        findings.forEach((finding) => {
            const item = document.createElement('article');
            item.className = 'finding-item';
            const severity = String(finding.severity || 'MEDIUM').toUpperCase();
            const color = severity === 'CRITICAL' || severity === 'HIGH'
                ? 'var(--red)'
                : severity === 'MEDIUM' ? 'var(--amber)' : 'var(--blue)';
            item.style.setProperty('--finding-color', color);

            const top = document.createElement('div');
            top.className = 'finding-top';
            const code = document.createElement('strong');
            code.className = 'finding-code';
            code.textContent = finding.code || 'SECURITY_SIGNAL';
            const severityLabel = document.createElement('span');
            severityLabel.className = 'finding-severity';
            severityLabel.textContent = severity;
            top.append(code, severityLabel);
            item.appendChild(top);

            const explanation = document.createElement('p');
            explanation.textContent = finding.message || 'Suspicious pattern detected.';
            item.appendChild(explanation);

            const metadata = document.createElement('div');
            metadata.className = 'finding-meta';
            if (finding.source) metadata.append(`Source: ${finding.source}`);
            if (finding.confidence !== undefined) metadata.append(`Confidence: ${finding.confidence}`);
            if (metadata.childNodes.length) item.appendChild(metadata);

            if (finding.evidence) {
                const evidence = document.createElement('span');
                evidence.className = 'finding-evidence';
                evidence.textContent = `Evidence: ${finding.evidence}`;
                item.appendChild(evidence);
            }
            list.appendChild(item);
        });
        container.appendChild(list);
    }

    showError(message) {
        const panel = document.getElementById('result-panel');
        panel.hidden = false;
        this.setText('result-scan-id', '');
        this.setText('decision-badge', '—');
        document.getElementById('decision-badge').className = 'decision-badge';
        this.setText('risk-score', '—');
        this.setText('risk-severity', '—');
        this.setText('decision-message', '');
        document.getElementById('score-fill').style.width = '0';
        document.getElementById('findings-container').replaceChildren();
        document.getElementById('ai-response').hidden = true;
        const alert = document.getElementById('error-alert');
        alert.textContent = message;
        alert.hidden = false;
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    setBusy(isBusy) {
        this.busy = isBusy;
        const buttons = document.querySelectorAll('#scan-form button[type="submit"], #file-submit');
        buttons.forEach((button) => {
            const label = button.querySelector('span');
            if (isBusy) {
                button.disabled = true;
                button.setAttribute('aria-busy', 'true');
                if (label) {
                    button.dataset.idleLabel = label.textContent;
                    label.textContent = 'Working…';
                }
                const spinner = document.createElement('span');
                spinner.className = 'button-spinner';
                spinner.setAttribute('aria-hidden', 'true');
                button.prepend(spinner);
            } else {
                button.disabled = button.id === 'file-submit' && !this.selectedFile;
                button.removeAttribute('aria-busy');
                button.querySelector('.button-spinner')?.remove();
                if (label && button.dataset.idleLabel) {
                    label.textContent = button.dataset.idleLabel;
                    delete button.dataset.idleLabel;
                }
            }
        });
    }

    updateCharacterCount(text) {
        this.setText('char-count', `${text.length.toLocaleString()} / 20,000`);
    }

    async loadLogs() {
        try {
            const data = await this.requestJson('/api/logs?limit=1000', {
                headers: { Accept: 'application/json' },
            });
            if (!Array.isArray(data.logs) || !data.summary) {
                throw new Error('The scan history response is incomplete.');
            }
            this.logs = data.logs;
            this.summary = data.summary;
            this.renderSummary(data.summary);
            this.renderHistory();
            this.renderActivity(data.summary.activity);
            this.renderDecisionCharts(data.summary);
            this.renderRiskDistribution(data.summary);
        } catch (error) {
            this.renderHistoryError(error.message);
            this.renderSummaryError();
        }
    }

    renderSummary(summary) {
        this.setText('metric-total', this.formatNumber(summary.total_scans));
        this.setText('metric-threats', this.formatNumber(summary.threats_detected));
        this.setText('metric-safe', this.formatNumber(summary.safe_prompts));
        this.setText('metric-blocked', this.formatNumber(summary.blocked_prompts));
    }

    renderSummaryError() {
        ['metric-total', 'metric-threats', 'metric-safe', 'metric-blocked'].forEach((id) => {
            this.setText(id, '—');
        });
        ['donut-total', 'donut-total-large'].forEach((id) => this.setText(id, '—'));
        ['decision-chart', 'decision-chart-large'].forEach((id) => {
            const chart = document.getElementById(id);
            if (chart) chart.style.background = 'conic-gradient(#2c3a50 0deg 360deg)';
        });
        ['activity-chart', 'analytics-activity-chart', 'decision-legend', 'decision-legend-large', 'risk-chart'].forEach((id) => {
            const container = document.getElementById(id);
            if (!container) return;
            container.replaceChildren();
            const message = document.createElement('div');
            message.className = 'chart-empty';
            message.textContent = 'Analytics unavailable.';
            container.appendChild(message);
        });
    }

    renderHistoryError(message) {
        ['activity-table-body', 'history-table-body'].forEach((id) => {
            const body = document.getElementById(id);
            if (!body) return;
            body.replaceChildren();
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'table-empty';
            cell.textContent = `Unable to load scan history: ${message}`;
            row.appendChild(cell);
            body.appendChild(row);
        });
        this.setText('history-count', 'History unavailable');
    }

    renderHistory() {
        const query = (document.getElementById('scan-search')?.value || '').trim().toLowerCase();
        const decision = document.getElementById('decision-filter')?.value || 'all';
        const filtered = this.logs.filter((log) => {
            const matchesQuery = String(log.scan_id || '').toLowerCase().includes(query);
            return matchesQuery && (decision === 'all' || log.decision === decision);
        });
        this.renderScanRows('history-table-body', filtered);
        this.renderScanRows('activity-table-body', this.logs.slice(0, 5));

        if (this.logs.length === 0) {
            this.setText('history-count', 'No scans recorded yet');
        } else {
            this.setText('history-count', `Showing ${filtered.length.toLocaleString()} of ${this.logs.length.toLocaleString()} recent records`);
        }
    }

    renderScanRows(bodyId, logs) {
        const body = document.getElementById(bodyId);
        if (!body) return;
        body.replaceChildren();
        if (logs.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'table-empty';
            cell.textContent = this.logs.length === 0
                ? 'No scan history yet. Run a prompt or document scan to get started.'
                : 'No scans match these filters.';
            row.appendChild(cell);
            body.appendChild(row);
            return;
        }

        logs.forEach((log) => {
            const row = document.createElement('tr');
            const scanId = document.createElement('td');
            scanId.className = 'scan-id';
            scanId.textContent = log.scan_id || '—';

            const input = document.createElement('td');
            const inputLabel = document.createElement('span');
            inputLabel.className = 'input-type';
            const inputIcon = document.createElementNS(SVG_NS, 'svg');
            inputIcon.setAttribute('class', 'icon');
            const use = document.createElementNS(SVG_NS, 'use');
            use.setAttribute('href', log.input_type === 'file' ? '#icon-file' : '#icon-scan');
            inputIcon.appendChild(use);
            inputLabel.append(inputIcon, document.createTextNode(
                log.input_type === 'file'
                    ? (log.file_extension ? `${log.file_extension.replace('.', '').toUpperCase()} document` : 'Document')
                    : 'Text prompt'
            ));
            input.appendChild(inputLabel);

            const decisionCell = document.createElement('td');
            const badge = document.createElement('span');
            const decisionName = ['ALLOW', 'FLAG', 'BLOCK'].includes(log.decision) ? log.decision : 'BLOCK';
            badge.className = `decision-badge decision-${decisionName}`;
            badge.textContent = decisionName;
            decisionCell.appendChild(badge);

            const riskCell = document.createElement('td');
            riskCell.appendChild(this.createRiskCell(log.risk_score));

            const timestamp = document.createElement('td');
            timestamp.textContent = this.formatTimestamp(log.timestamp || log.created_at);
            row.append(scanId, input, decisionCell, riskCell, timestamp);
            body.appendChild(row);
        });
    }

    createRiskCell(value) {
        const score = Math.max(0, Math.min(100, Number(value) || 0));
        const wrapper = document.createElement('span');
        wrapper.className = 'risk-cell';
        const label = document.createElement('span');
        label.textContent = String(score);
        const track = document.createElement('span');
        track.className = 'risk-mini-track';
        const fill = document.createElement('span');
        fill.className = 'risk-mini-fill';
        fill.style.width = `${score}%`;
        fill.style.setProperty(
            '--risk-color',
            score >= 70 ? 'var(--red)' : score >= 30 ? 'var(--amber)' : 'var(--green)'
        );
        track.appendChild(fill);
        wrapper.append(label, track);
        return wrapper;
    }

    renderDecisionCharts(summary) {
        const decisions = summary.decisions || {};
        const rows = [
            { key: 'ALLOW', label: 'Allowed', color: '#38d99b' },
            { key: 'FLAG', label: 'Flagged', color: '#ffbf5b' },
            { key: 'BLOCK', label: 'Blocked', color: '#ff6d7f' },
        ].map((item) => ({ ...item, value: Number(decisions[item.key]) || 0 }));
        const total = rows.reduce((sum, item) => sum + item.value, 0);

        [['decision-chart', 'decision-legend', 'donut-total'], ['decision-chart-large', 'decision-legend-large', 'donut-total-large']]
            .forEach(([chartId, legendId, totalId]) => {
                const chart = document.getElementById(chartId);
                const legend = document.getElementById(legendId);
                if (!chart || !legend) return;
                this.setText(totalId, this.formatNumber(total));
                let position = 0;
                const stops = [];
                rows.forEach((item) => {
                    const start = position;
                    position += total ? (item.value / total) * 360 : 0;
                    stops.push(`${item.color} ${start}deg ${position}deg`);
                });
                chart.style.background = total
                    ? `conic-gradient(${stops.join(', ')})`
                    : 'conic-gradient(#2c3a50 0deg 360deg)';
                chart.setAttribute(
                    'aria-label',
                    `Decision distribution: ${rows.map((item) => `${item.label} ${item.value}`).join(', ')}`
                );

                legend.replaceChildren();
                rows.forEach((item) => {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'legend-item';
                    button.title = `Show ${item.label.toLowerCase()} scans`;
                    const dot = document.createElement('span');
                    dot.className = 'legend-dot';
                    dot.style.backgroundColor = item.color;
                    const label = document.createElement('span');
                    label.textContent = item.label;
                    const count = document.createElement('strong');
                    count.textContent = this.formatNumber(item.value);
                    button.append(dot, label, count);
                    button.addEventListener('click', () => this.filterByDecision(item.key));
                    legend.appendChild(button);
                });
            });
    }

    filterByDecision(decision) {
        const filter = document.getElementById('decision-filter');
        if (filter) filter.value = decision;
        this.renderHistory();
        document.getElementById('recent-scans')?.scrollIntoView({ behavior: 'smooth' });
    }

    renderRiskDistribution(summary) {
        const chart = document.getElementById('risk-chart');
        if (!chart) return;
        chart.replaceChildren();
        const total = Number(summary.total_scans) || 0;
        const risk = summary.risk_distribution || {};
        [
            { key: 'low', label: 'Low risk', range: '0–29', color: 'var(--green)' },
            { key: 'medium', label: 'Medium', range: '30–69', color: 'var(--amber)' },
            { key: 'high', label: 'High risk', range: '70–100', color: 'var(--red)' },
        ].forEach((item) => {
            const value = Number(risk[item.key]) || 0;
            const row = document.createElement('div');
            row.className = 'risk-bar-row';
            row.setAttribute('role', 'img');
            row.setAttribute('aria-label', `${item.label}, score ${item.range}: ${value} scans`);
            const label = document.createElement('span');
            label.textContent = item.label;
            const track = document.createElement('span');
            track.className = 'risk-bar-track';
            const fill = document.createElement('span');
            fill.className = 'risk-bar-fill';
            fill.style.setProperty('--risk-color', item.color);
            fill.style.width = `${total ? (value / total) * 100 : 0}%`;
            track.appendChild(fill);
            const count = document.createElement('strong');
            count.textContent = this.formatNumber(value);
            row.append(label, track, count);
            chart.appendChild(row);
        });
    }

    renderActivity(activity) {
        const activityByDate = new Map(
            (Array.isArray(activity) ? activity : []).map((item) => [item.date, Number(item.scans) || 0])
        );
        const days = [];
        const today = new Date();
        today.setUTCHours(0, 0, 0, 0);
        for (let offset = 6; offset >= 0; offset -= 1) {
            const date = new Date(today);
            date.setUTCDate(date.getUTCDate() - offset);
            const key = date.toISOString().slice(0, 10);
            days.push({ key, date, scans: activityByDate.get(key) || 0 });
        }
        this.drawActivityChart(document.getElementById('activity-chart'), days, false);
        this.drawActivityChart(document.getElementById('analytics-activity-chart'), days, true);
    }

    drawActivityChart(container, days, large) {
        if (!container) return;
        container.replaceChildren();
        const width = 700;
        const height = large ? 230 : 190;
        const left = 39;
        const right = 12;
        const top = 17;
        const bottom = height - 31;
        const plotHeight = bottom - top;
        const maxValue = Math.max(1, ...days.map((day) => day.scans));
        const scaleMax = Math.max(4, Math.ceil(maxValue / 4) * 4);
        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('class', 'activity-svg');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.setAttribute('role', 'img');
        svg.setAttribute(
            'aria-label',
            `Scans over the last seven days: ${days.map((day) => `${day.key}, ${day.scans}`).join('; ')}`
        );
        const title = document.createElementNS(SVG_NS, 'title');
        title.textContent = 'Daily scan count for the last seven days';
        svg.appendChild(title);

        const defs = document.createElementNS(SVG_NS, 'defs');
        const gradient = document.createElementNS(SVG_NS, 'linearGradient');
        gradient.id = large ? 'analytics-activity-gradient' : 'activity-gradient';
        gradient.setAttribute('x1', '0');
        gradient.setAttribute('x2', '0');
        gradient.setAttribute('y1', '0');
        gradient.setAttribute('y2', '1');
        const colorStart = document.createElementNS(SVG_NS, 'stop');
        colorStart.setAttribute('offset', '0%');
        colorStart.setAttribute('stop-color', '#75a9ff');
        const colorEnd = document.createElementNS(SVG_NS, 'stop');
        colorEnd.setAttribute('offset', '100%');
        colorEnd.setAttribute('stop-color', '#477de1');
        colorEnd.setAttribute('stop-opacity', '.42');
        gradient.append(colorStart, colorEnd);
        defs.appendChild(gradient);
        svg.appendChild(defs);

        [0, scaleMax / 2, scaleMax].forEach((value) => {
            const y = bottom - (value / scaleMax) * plotHeight;
            const line = document.createElementNS(SVG_NS, 'line');
            line.setAttribute('x1', String(left));
            line.setAttribute('x2', String(width - right));
            line.setAttribute('y1', String(y));
            line.setAttribute('y2', String(y));
            line.setAttribute('class', 'chart-grid-line');
            svg.appendChild(line);

            const label = document.createElementNS(SVG_NS, 'text');
            label.setAttribute('x', String(left - 9));
            label.setAttribute('y', String(y + 3));
            label.setAttribute('text-anchor', 'end');
            label.setAttribute('class', 'chart-axis-label');
            label.textContent = this.formatNumber(value);
            svg.appendChild(label);
        });

        const slot = (width - left - right) / days.length;
        const barWidth = Math.min(48, slot * 0.55);
        days.forEach((day, index) => {
            const barHeight = day.scans ? Math.max(3, (day.scans / scaleMax) * plotHeight) : 2;
            const x = left + slot * index + (slot - barWidth) / 2;
            const y = bottom - barHeight;
            const bar = document.createElementNS(SVG_NS, 'rect');
            bar.setAttribute('x', String(x));
            bar.setAttribute('y', String(y));
            bar.setAttribute('width', String(barWidth));
            bar.setAttribute('height', String(barHeight));
            bar.setAttribute('rx', '4');
            bar.setAttribute('class', `chart-bar${index === days.length - 1 ? ' today' : ''}`);
            bar.setAttribute('fill', `url(#${large ? 'analytics-activity-gradient' : 'activity-gradient'})`);
            const tooltip = document.createElementNS(SVG_NS, 'title');
            tooltip.textContent = `${this.formatLongDate(day.date)}: ${day.scans} ${day.scans === 1 ? 'scan' : 'scans'}`;
            bar.appendChild(tooltip);
            svg.appendChild(bar);

            if (day.scans > 0) {
                const value = document.createElementNS(SVG_NS, 'text');
                value.setAttribute('x', String(x + barWidth / 2));
                value.setAttribute('y', String(Math.max(top + 10, y - 6)));
                value.setAttribute('text-anchor', 'middle');
                value.setAttribute('class', 'chart-value-label');
                value.textContent = this.formatNumber(day.scans);
                svg.appendChild(value);
            }

            const dayLabel = document.createElementNS(SVG_NS, 'text');
            dayLabel.setAttribute('x', String(x + barWidth / 2));
            dayLabel.setAttribute('y', String(height - 8));
            dayLabel.setAttribute('text-anchor', 'middle');
            dayLabel.setAttribute('class', 'chart-bar-label');
            dayLabel.textContent = new Intl.DateTimeFormat(undefined, { weekday: 'short', timeZone: 'UTC' }).format(day.date);
            svg.appendChild(dayLabel);
        });
        container.appendChild(svg);
    }

    formatLongDate(date) {
        return new Intl.DateTimeFormat(undefined, {
            month: 'short',
            day: 'numeric',
            timeZone: 'UTC',
        }).format(date);
    }

    formatTimestamp(value) {
        if (!value) return '—';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'Unknown time';
        return new Intl.DateTimeFormat(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        }).format(date);
    }

    formatBytes(bytes) {
        if (!Number.isFinite(Number(bytes)) || Number(bytes) < 0) return '—';
        const megabytes = Number(bytes) / (1024 * 1024);
        return `${Number.isInteger(megabytes) ? megabytes : megabytes.toFixed(1)} MB`;
    }

    formatNumber(value) {
        const count = Number(value);
        return Number.isFinite(count) && count >= 0 ? Math.floor(count).toLocaleString() : '—';
    }

    setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    showToast(message) {
        const region = document.getElementById('toast-region');
        const toast = document.createElement('div');
        toast.className = 'toast-message';
        toast.textContent = message;
        region.appendChild(toast);
        window.setTimeout(() => toast.remove(), 4200);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new SecurityGatewayUI());
} else {
    new SecurityGatewayUI();
}

window.SecurityGatewayUI = SecurityGatewayUI;
