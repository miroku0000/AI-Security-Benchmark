// ui.js - Main UI interaction logic for SAST mapping interface

class VulnerabilityUI {
    constructor() {
        this.currentFile = null;
        this.currentSession = null;
        this.fileData = {};
        this.initializeEventListeners();
        this.restoreSession();
    }

    initializeEventListeners() {
        // Upload button
        document.getElementById('upload-btn').addEventListener('click', () => this.showUploadModal());

        // Modal controls
        document.getElementById('cancel-upload').addEventListener('click', () => this.closeUploadModal());
        document.getElementById('confirm-upload').addEventListener('click', () => this.handleUpload());

        // File inputs
        document.getElementById('benchmark-upload').addEventListener('change', (e) => this.onBenchmarkSelected(e));
        document.getElementById('sast-upload').addEventListener('change', (e) => this.onSastSelected(e));

        // Confidence slider
        document.getElementById('confidence-slider').addEventListener('input', (e) => this.onConfidenceChange(e));

        // Export button
        document.getElementById('export-btn').addEventListener('click', () => this.handleExport());

        // Mapping actions
        document.getElementById('accept-all-btn').addEventListener('click', () => this.acceptAllVisible());
        document.getElementById('reject-all-btn').addEventListener('click', () => this.rejectAllVisible());

        // Close modal on background click
        document.getElementById('upload-modal').addEventListener('click', (e) => {
            if (e.target.id === 'upload-modal') {
                this.closeUploadModal();
            }
        });
    }

    restoreSession() {
        const sessionId = sessionManager.getSessionId();
        if (sessionId) {
            this.loadSessionData();
        }
    }

    showUploadModal() {
        document.getElementById('upload-modal').classList.add('show');
    }

    closeUploadModal() {
        document.getElementById('upload-modal').classList.remove('show');
        document.getElementById('benchmark-upload').value = '';
        document.getElementById('sast-upload').value = '';
        document.getElementById('benchmark-info').textContent = '';
        document.getElementById('sast-info').textContent = '';
        document.getElementById('confirm-upload').disabled = true;
    }

    onBenchmarkSelected(event) {
        const file = event.target.files[0];
        if (file) {
            document.getElementById('benchmark-info').textContent = `Selected: ${file.name} (${this.formatFileSize(file.size)})`;
            this.updateUploadButton();
        }
    }

    onSastSelected(event) {
        const file = event.target.files[0];
        if (file) {
            document.getElementById('sast-info').textContent = `Selected: ${file.name} (${this.formatFileSize(file.size)})`;
            this.updateUploadButton();
        }
    }

    updateUploadButton() {
        const benchmarkFile = document.getElementById('benchmark-upload').files[0];
        const sastFile = document.getElementById('sast-upload').files[0];
        document.getElementById('confirm-upload').disabled = !(benchmarkFile && sastFile);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    async handleUpload() {
        const benchmarkFile = document.getElementById('benchmark-upload').files[0];
        const sastFile = document.getElementById('sast-upload').files[0];

        if (!benchmarkFile || !sastFile) {
            alert('Please select both files');
            return;
        }

        this.showLoadingOverlay();

        try {
            const result = await sessionManager.uploadFiles(benchmarkFile, sastFile, 'semgrep');
            console.log('Upload result:', result);

            document.getElementById('upload-status').textContent =
                `Session loaded: ${result.files_count} files, ${result.total_vulnerabilities.benchmark} benchmark, ${result.total_vulnerabilities.sast} SAST vulnerabilities`;

            this.closeUploadModal();
            await this.loadSessionData();

            document.getElementById('export-btn').disabled = false;
        } catch (error) {
            alert(`Upload failed: ${error.message}`);
            console.error('Upload error:', error);
        } finally {
            this.hideLoadingOverlay();
        }
    }

    async loadSessionData() {
        try {
            this.showLoadingOverlay();
            const data = await sessionManager.getSessionData();

            this.fileData = {};
            data.files.forEach(file => {
                this.fileData[file.file_path] = file;
            });

            this.renderFileList(data.files);
            this.updateProgressText();

            // Load first file
            if (data.files.length > 0) {
                this.selectFile(data.files[0].file_path);
            }
        } catch (error) {
            alert(`Failed to load session: ${error.message}`);
            console.error('Session load error:', error);
        } finally {
            this.hideLoadingOverlay();
        }
    }

    renderFileList(files) {
        const container = document.getElementById('file-list-container');

        if (files.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No files with vulnerabilities</p></div>';
            return;
        }

        container.innerHTML = files.map(file => {
            const benchCount = file.benchmark_vulns.length;
            const sastCount = file.sast_vulns.length;
            const totalCount = benchCount + sastCount;

            return `
                <div class="file-item" data-file-path="${this.escapeHtml(file.file_path)}" onclick="ui.selectFile('${this.escapeHtml(file.file_path)}')">
                    <div class="file-name">${this.escapeHtml(file.file_path.split('/').pop())}</div>
                    <div class="file-stats">
                        Benchmark: ${benchCount} | SAST: ${sastCount} | Total: ${totalCount}
                    </div>
                </div>
            `;
        }).join('');
    }

    selectFile(filePath) {
        // Update active state
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-file-path="${this.escapeHtml(filePath)}"]`)?.classList.add('active');

        this.currentFile = filePath;
        const fileData = this.fileData[filePath];

        if (!fileData) return;

        this.renderVulnerabilities(fileData);
    }

    renderVulnerabilities(fileData) {
        // Render benchmark vulnerabilities
        const benchmarkContainer = document.getElementById('benchmark-vulns');
        benchmarkContainer.innerHTML = fileData.benchmark_vulns.length > 0
            ? fileData.benchmark_vulns.map(vuln => this.renderVulnerabilityItem(vuln, 'benchmark')).join('')
            : '<div class="empty-state"><p>No benchmark vulnerabilities</p></div>';

        // Render SAST vulnerabilities
        const sastContainer = document.getElementById('sast-vulns');
        sastContainer.innerHTML = fileData.sast_vulns.length > 0
            ? fileData.sast_vulns.map(vuln => this.renderVulnerabilityItem(vuln, 'sast')).join('')
            : '<div class="empty-state"><p>No SAST vulnerabilities</p></div>';

        this.attachVulnerabilityListeners();
    }

    renderVulnerabilityItem(vuln, type) {
        const severityClass = (vuln.severity || 'unknown').toLowerCase();
        const typeAttr = type === 'benchmark' ? 'data-benchmark-id' : 'data-sast-id';

        return `
            <div class="vulnerability-item" ${typeAttr}="${this.escapeHtml(vuln.id)}">
                <div class="vulnerability-header">
                    <span class="vulnerability-type">${this.escapeHtml(vuln.vuln_type)}</span>
                    <span class="vulnerability-line">Line ${vuln.line_number}</span>
                </div>
                <div>
                    <span class="vulnerability-severity ${severityClass}">${this.escapeHtml(vuln.severity || 'UNKNOWN')}</span>
                </div>
                <div class="vulnerability-description">${this.escapeHtml(vuln.description || 'No description')}</div>
            </div>
        `;
    }

    attachVulnerabilityListeners() {
        document.querySelectorAll('.vulnerability-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const benchmarkId = item.getAttribute('data-benchmark-id');
                const sastId = item.getAttribute('data-sast-id');

                if (benchmarkId) {
                    document.querySelectorAll('[data-benchmark-id]').forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                } else if (sastId) {
                    document.querySelectorAll('[data-sast-id]').forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                }
            });
        });
    }

    onConfidenceChange(event) {
        const confidence = event.target.value;
        document.getElementById('confidence-value').textContent = confidence;
        this.loadSuggestions(confidence);
    }

    async loadSuggestions(confidenceThreshold) {
        try {
            const data = await sessionManager.getSuggestions(parseInt(confidenceThreshold));
            this.renderSuggestions(data.suggestions);
        } catch (error) {
            console.error('Failed to load suggestions:', error);
        }
    }

    renderSuggestions(suggestions) {
        const container = document.getElementById('suggestions-container');

        if (suggestions.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No suggestions matching confidence threshold</p></div>';
            return;
        }

        container.innerHTML = suggestions.map((suggestion, index) => `
            <div class="suggestion-item">
                <div class="suggestion-info">
                    <div class="suggestion-match">
                        ${this.escapeHtml(suggestion.benchmark_type || 'Unknown')}
                        <span style="color: #6c757d;">→</span>
                        ${this.escapeHtml(suggestion.sast_pattern || 'Unknown')}
                    </div>
                    <div class="suggestion-reasoning">${this.escapeHtml(suggestion.reasoning || 'Pattern match')}</div>
                </div>
                <span class="suggestion-confidence">${Math.round(suggestion.confidence)}%</span>
                <div class="suggestion-actions">
                    <button class="btn btn-success btn-sm" onclick="ui.acceptSuggestion('${index}')">Accept</button>
                    <button class="btn btn-danger btn-sm" onclick="ui.rejectSuggestion('${index}')">Reject</button>
                </div>
            </div>
        `).join('');
    }

    acceptSuggestion(index) {
        console.log('Accept suggestion:', index);
        // Implementation depends on backend response format
    }

    rejectSuggestion(index) {
        console.log('Reject suggestion:', index);
    }

    acceptAllVisible() {
        const benchmarkItems = document.querySelectorAll('#benchmark-vulns .vulnerability-item');
        const sastItems = document.querySelectorAll('#sast-vulns .vulnerability-item');

        if (benchmarkItems.length > 0 && sastItems.length > 0) {
            const benchId = benchmarkItems[0].getAttribute('data-benchmark-id');
            const sastId = sastItems[0].getAttribute('data-sast-id');

            if (benchId && sastId) {
                this.updateMapping(benchId, sastId, 'confirm');
            }
        }
    }

    rejectAllVisible() {
        const benchmarkItems = document.querySelectorAll('#benchmark-vulns .vulnerability-item');
        const sastItems = document.querySelectorAll('#sast-vulns .vulnerability-item');

        if (benchmarkItems.length > 0 && sastItems.length > 0) {
            const benchId = benchmarkItems[0].getAttribute('data-benchmark-id');
            const sastId = sastItems[0].getAttribute('data-sast-id');

            if (benchId && sastId) {
                this.updateMapping(benchId, sastId, 'deny');
            }
        }
    }

    async updateMapping(benchmarkId, sastId, action) {
        try {
            const result = await sessionManager.updateMapping(benchmarkId, sastId, action);
            console.log('Mapping updated:', result);

            // Update UI state
            const benchItem = document.querySelector(`[data-benchmark-id="${benchmarkId}"]`);
            const sastItem = document.querySelector(`[data-sast-id="${sastId}"]`);

            if (benchItem && sastItem) {
                const className = action === 'confirm' ? 'confirmed' : 'denied';
                benchItem.classList.add(className);
                sastItem.classList.add(className);
            }
        } catch (error) {
            alert(`Failed to update mapping: ${error.message}`);
            console.error('Mapping error:', error);
        }
    }

    async handleExport() {
        try {
            this.showLoadingOverlay();
            const data = await sessionManager.exportMapping();
            const sessionId = sessionManager.getSessionId();
            sessionManager.downloadExport(data, sessionId);
            alert('Mapping exported successfully');
        } catch (error) {
            alert(`Export failed: ${error.message}`);
            console.error('Export error:', error);
        } finally {
            this.hideLoadingOverlay();
        }
    }

    updateProgressText() {
        const sessionId = sessionManager.getSessionId();
        if (sessionId) {
            document.getElementById('progress-text').textContent = `Session: ${sessionId.substring(0, 8)}...`;
        }
    }

    showLoadingOverlay() {
        document.getElementById('loading-overlay').classList.add('show');
    }

    hideLoadingOverlay() {
        document.getElementById('loading-overlay').classList.remove('show');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize UI when DOM is ready
let ui;
document.addEventListener('DOMContentLoaded', () => {
    ui = new VulnerabilityUI();
});
