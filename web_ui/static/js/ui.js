// ui.js - Main UI interaction logic for SAST mapping interface

class VulnerabilityUI {
    constructor() {
        this.currentFile = null;
        this.currentSession = null;
        this.fileData = {};
        this.mappedSastFindings = new Set(); // Track which SAST findings are mapped
        this.currentFilter = 'unmapped'; // Default to showing only unmapped
        this.loadedMappingRules = null; // Imported mapping rules
        this.negativeMappingRules = new Set(); // Track negative mappings (X != Y)
        this.csrfToken = null; // Security: CSRF protection
        this.initializeEventListeners();
        this.initializeCSRF(); // Security: Get CSRF token
        this.restoreSession(); // Now async but we don't wait for it
        this.loadSavedMappingRules();

        // Disable upload button until CSRF token is ready
        this.disableUploadUntilReady();
    }

    // Security: Initialize CSRF protection
    async initializeCSRF() {
        try {
            const response = await fetch('/api/csrf-token');
            if (response.ok) {
                const data = await response.json();
                this.csrfToken = data.csrf_token;
                console.log('🔒 CSRF token initialized');

                // Enable upload functionality once CSRF token is ready
                this.enableUpload();
            } else {
                console.error('Failed to get CSRF token');
            }
        } catch (error) {
            console.error('Error initializing CSRF token:', error);
        }
    }

    disableUploadUntilReady() {
        const uploadBtn = document.getElementById('upload-btn');
        const confirmBtn = document.getElementById('confirm-upload');

        if (uploadBtn) {
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Initializing Security...';
        }
        if (confirmBtn) {
            confirmBtn.disabled = true;
        }
    }

    enableUpload() {
        const uploadBtn = document.getElementById('upload-btn');
        const confirmBtn = document.getElementById('confirm-upload');

        if (uploadBtn) {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload Files';
        }
        // confirmBtn is re-enabled by updateUploadButton when files are selected
    }

    // Clear all session-related state
    clearSessionState() {
        this.currentSession = null;
        this.fileData = {};
        this.sastFindings = [];
        this.mappedSastFindings.clear();
        this.selectedSastFinding = null;

        // Clear UI elements
        const sastContainer = document.getElementById('sast-findings');
        if (sastContainer) {
            sastContainer.innerHTML = '<div class="empty-state"><p>Upload files to see SAST findings</p></div>';
        }

        const selectedFindingContainer = document.getElementById('selected-finding');
        if (selectedFindingContainer) {
            selectedFindingContainer.innerHTML = '<div class="empty-state"><p>Select a SAST finding to see details and potential matches</p></div>';
        }

        // Reset progress
        const progressText = document.getElementById('progress-text');
        if (progressText) {
            progressText.textContent = 'No session loaded';
        }

        // Disable export buttons
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) exportBtn.disabled = true;

        const exportMappingsBtn = document.getElementById('export-mappings-btn');
        if (exportMappingsBtn) exportMappingsBtn.disabled = true;

        console.log('🧹 Session state cleared');
    }

    // Security: Ensure we have a valid session before API calls
    ensureSession() {
        if (!this.currentSession) {
            const storedSession = sessionManager?.getSessionId();
            if (storedSession) {
                this.currentSession = storedSession;
                console.log('🔄 Session restored:', this.currentSession);
            } else {
                throw new Error('No active session. Please upload files first.');
            }
        }
    }

    // Security: Secure API request helper with CSRF protection
    async secureApiRequest(url, options = {}) {
        // Ensure we have a session before making API calls
        this.ensureSession();

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            },
            ...options
        };

        // Add CSRF token for state-changing requests
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(defaultOptions.method?.toUpperCase())) {
            if (!this.csrfToken) {
                console.log('🔄 CSRF token missing, fetching...');
                await this.initializeCSRF();
                if (!this.csrfToken) {
                    throw new Error('Failed to obtain CSRF token');
                }
            }

            if (this.csrfToken) {
                defaultOptions.headers['X-CSRF-Token'] = this.csrfToken;

                // Also add to JSON body if present
                if (defaultOptions.body && defaultOptions.headers['Content-Type']?.includes('application/json')) {
                    try {
                        const bodyData = JSON.parse(defaultOptions.body);
                        bodyData.csrf_token = this.csrfToken;
                        defaultOptions.body = JSON.stringify(bodyData);
                    } catch (e) {
                        // If body isn't JSON, just add header
                    }
                }
            }
        }

        const response = await fetch(url, defaultOptions);

        // Handle CSRF token expiration or session issues
        if (response.status === 403) {
            try {
                const errorData = await response.json();
                if (errorData.error?.includes('CSRF')) {
                    console.log('🔄 CSRF token expired, refreshing...');
                    this.csrfToken = null; // Clear old token
                    await this.initializeCSRF();
                    // Retry the request once with new token
                    if (this.csrfToken) {
                        defaultOptions.headers['X-CSRF-Token'] = this.csrfToken;

                        // Update JSON body if it exists
                        if (defaultOptions.body && defaultOptions.headers['Content-Type']?.includes('application/json')) {
                            const bodyData = JSON.parse(defaultOptions.body);
                            bodyData.csrf_token = this.csrfToken;
                            defaultOptions.body = JSON.stringify(bodyData);
                        }

                        return fetch(url, defaultOptions);
                    }
                }
            } catch (e) {
                // If response isn't JSON, just return the original response
                console.log('🔄 Non-JSON 403 response, not retrying');
            }
        }

        return response;
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
        document.getElementById('mapping-rules-upload').addEventListener('change', (e) => this.onMappingRulesUploadSelected(e));

        // Confidence slider
        document.getElementById('confidence-slider').addEventListener('input', (e) => this.onConfidenceChange(e));

        // Auto-mapping controls
        document.getElementById('auto-mapping-enabled').addEventListener('change', (e) => this.onAutoMappingToggle(e));
        document.getElementById('auto-mapping-threshold').addEventListener('change', (e) => this.onThresholdChange(e));

        // Export button
        document.getElementById('export-btn').addEventListener('click', () => this.handleExport());

        // Import/Export mappings
        document.getElementById('import-mappings-btn').addEventListener('click', () => this.handleImportMappings());
        document.getElementById('export-mappings-btn').addEventListener('click', () => this.handleExportMappings());
        document.getElementById('analyze-correlations-btn').addEventListener('click', () => this.analyzeCorrelations());
        document.getElementById('import-mappings-file').addEventListener('change', (e) => this.onMappingsFileSelected(e));

        // Mapping actions (check if elements exist first)
        const acceptAllBtn = document.getElementById('accept-all-btn');
        const rejectAllBtn = document.getElementById('reject-all-btn');
        if (acceptAllBtn) acceptAllBtn.addEventListener('click', () => this.acceptAllVisible());
        if (rejectAllBtn) rejectAllBtn.addEventListener('click', () => this.rejectAllVisible());

        // Panel controls removed - suggestions panel was eliminated

        // SAST filter controls
        document.getElementById('show-unmapped').addEventListener('click', () => this.setFilter('unmapped'));
        document.getElementById('show-mapped').addEventListener('click', () => this.setFilter('mapped'));
        document.getElementById('show-all').addEventListener('click', () => this.setFilter('all'));

        // Close modal on background click
        document.getElementById('upload-modal').addEventListener('click', (e) => {
            if (e.target.id === 'upload-modal') {
                this.closeUploadModal();
            }
        });
    }


    async restoreSession() {
        const sessionId = sessionManager.getSessionId();
        if (sessionId) {
            console.log('🔄 Restoring session:', sessionId);
            this.currentSession = sessionId;
            try {
                await this.loadSessionData();
            } catch (error) {
                console.log('🔄 Session restore failed:', error.message);
                if (error.message.includes('expired') || error.message.includes('404')) {
                    // Session expired, clear everything and reset
                    this.clearSessionState();
                    sessionManager.clearSession();
                    this.csrfToken = null;

                    // Re-initialize CSRF for fresh start
                    await this.initializeCSRF();
                    console.log('🔄 Session expired, cleared state, ready for new upload');
                }
            }
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

    onMappingRulesUploadSelected(event) {
        const file = event.target.files[0];
        if (file) {
            // Security: Validate file type and size
            if (!file.name.endsWith('.json')) {
                alert('Only JSON files are allowed for mapping rules');
                event.target.value = '';
                return;
            }

            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                alert('Mapping rules file too large (max 10MB)');
                event.target.value = '';
                return;
            }

            document.getElementById('mapping-rules-info').textContent = `Selected: ${file.name} (${this.formatFileSize(file.size)})`;
        } else {
            document.getElementById('mapping-rules-info').textContent = '';
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
        const mappingRulesFile = document.getElementById('mapping-rules-upload').files[0];

        if (!benchmarkFile || !sastFile) {
            alert('Please select both files');
            return;
        }

        this.showLoadingOverlay();

        try {
            console.log('Starting upload...', {
                benchmark: benchmarkFile?.name,
                sast: sastFile?.name,
                mappingRules: mappingRulesFile?.name || 'none'
            });

            const result = await sessionManager.uploadFiles(benchmarkFile, sastFile, 'semgrep', mappingRulesFile);
            console.log('Upload result:', result);

            if (!result || !result.session_id) {
                throw new Error('Invalid upload response - no session ID received');
            }

            // Store the session ID for API calls
            this.currentSession = result.session_id;
            console.log('✅ Session ID set:', this.currentSession);

            // Ensure sessionManager also has the session ID
            sessionManager.setSessionId(result.session_id);

            document.getElementById('upload-status').textContent =
                `Session loaded: ${result.files_count} files, ${result.total_vulnerabilities.benchmark} benchmark, ${result.total_vulnerabilities.sast} SAST vulnerabilities`;

            this.closeUploadModal();
            await this.loadSessionData();

            document.getElementById('export-btn').disabled = false;
        } catch (error) {
            console.error('Detailed upload error:', {
                message: error.message,
                stack: error.stack,
                benchmark: benchmarkFile?.name,
                sast: sastFile?.name
            });
            alert(`Upload failed: ${error.message}\n\nCheck browser console for details.`);
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

            await this.renderFileList(data.files);
            this.updateProgressText();

            // No need to select a specific file anymore - we show all SAST findings
            // Users will click on individual SAST findings to see matches
        } catch (error) {
            if (error.message.includes('expired') || error.message.includes('404')) {
                console.log('🔄 Session expired during load, will require new upload');
                // Don't show alert for expired sessions, just log it
                // The UI will show the upload button is available
            } else {
                alert(`Failed to load session: ${error.message}`);
            }
            console.error('Session load error:', error);
            throw error; // Re-throw so calling code can handle
        } finally {
            this.hideLoadingOverlay();
        }
    }

    async renderFileList(files) {
        // Validate input first
        if (!files || !Array.isArray(files)) {
            console.error('Invalid files data:', files);
            return;
        }

        if (files.length === 0) {
            console.log('No files to render');
            return;
        }

        // Collect all SAST findings from all files - DEFINE BEFORE USE
        let allSastFindings = [];
        files.forEach(file => {
            if (file && file.sast_vulns && Array.isArray(file.sast_vulns)) {
                file.sast_vulns.forEach(vuln => {
                    if (vuln) {
                        allSastFindings.push({
                            ...vuln,
                            sourceFile: file.file_path
                        });
                    }
                });
            }
        });

        console.log('All SAST findings collected:', allSastFindings.length, allSastFindings);

        // Store findings BEFORE using them
        this.sastFindings = allSastFindings;

        // Auto-apply any loaded mapping rules
        if (this.loadedMappingRules && this.currentSession) {
            await this.applyLoadedMappingRules();
        }

        // Check for 1:1 mapping opportunities - DEFINE BEFORE USE
        const oneToOneFiles = files.filter(file => {
            return file &&
                   file.benchmark_vulns && Array.isArray(file.benchmark_vulns) && file.benchmark_vulns.length === 1 &&
                   file.sast_vulns && Array.isArray(file.sast_vulns) && file.sast_vulns.length === 1;
        });

        // Check session completion status - DEFINE BEFORE USE
        const bulkMappingKey = this.currentSession ? 'bulk-mapping-completed-' + this.currentSession : null;
        const bulkMappingCompleted = bulkMappingKey ? localStorage.getItem(bulkMappingKey) : null;

        // Decision logic - ALL VARIABLES DEFINED ABOVE
        if (oneToOneFiles.length > 0 && !bulkMappingCompleted) {
            // Show bulk mapping interface first
            this.showBulkMappingWorkflow(oneToOneFiles, files, allSastFindings);
        } else {
            // Show normal detailed mapping interface
            this.showDetailedMappingInterface(files, allSastFindings);
        }
    }

    updateSessionSummary(files, allSastFindings) {
        const totalBenchmarkVulns = files.reduce((sum, f) => sum + f.benchmark_vulns.length, 0);
        const mappedCount = this.mappedSastFindings.size;
        const unmappedCount = allSastFindings.length - mappedCount;

        // Show the session summary header
        const sessionSummary = document.getElementById('session-summary');
        if (sessionSummary) {
            sessionSummary.style.display = 'block';
        }

        // Update the counts
        const filesCount = document.getElementById('files-count');
        const unmappedCountEl = document.getElementById('unmapped-count');
        const mappedCountEl = document.getElementById('mapped-count');

        if (filesCount) filesCount.textContent = `Files: ${files.length}`;
        if (unmappedCountEl) unmappedCountEl.textContent = `Unmapped: ${unmappedCount}`;
        if (mappedCountEl) mappedCountEl.textContent = `Mapped: ${mappedCount}`;

        // Enable/disable export mappings button based on mapped count
        const exportMappingsBtn = document.getElementById('export-mappings-btn');
        if (exportMappingsBtn) {
            exportMappingsBtn.disabled = mappedCount === 0;
            exportMappingsBtn.textContent = mappedCount > 0 ? `📤 Export ${mappedCount} Mappings` : '📤 Export Mappings';
        }

        // Enable/disable correlation analysis button based on available data
        const correlationBtn = document.getElementById('analyze-correlations-btn');
        if (correlationBtn) {
            correlationBtn.disabled = files.length < 5; // Need at least 5 files for meaningful correlation
            correlationBtn.textContent = files.length >= 5 ? `📊 Analyze ${files.length} Files` : '📊 Analyze Correlations';
        }
    }

    setFilter(filterType) {
        this.currentFilter = filterType;

        // Update active button
        document.querySelectorAll('.sast-filters .btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`show-${filterType}`).classList.add('active');

        // Re-render SAST findings with filter
        if (this.sastFindings) {
            this.renderSastFindings(this.sastFindings);
        }
    }

    shouldShowSastFinding(finding, index) {
        // Use backend-provided ID if available, otherwise generate
        const findingId = finding.id || `sast_${index}_${this.generateId(finding)}`;
        const isMapped = this.mappedSastFindings.has(findingId);

        // Debug output for first few findings to see ID matching
        if (index < 10) {
            console.log(`🔍 shouldShowSastFinding(${index}): using ID=${findingId} (backend-provided: ${!!finding.id}), isMapped=${isMapped}`);
            console.log(`  Finding: ${finding.file_path}:${finding.line_number} (rule: ${finding.rule_id})`);
        }

        switch (this.currentFilter) {
            case 'unmapped': return !isMapped;
            case 'mapped': return isMapped;
            case 'all': return true;
            default: return true;
        }
    }

    generateId(finding) {
        // Generate same ID format as backend: hash(file_path + line_number) & 0xFFFFFF as hex
        const hashInput = (finding.file_path || '') + String(finding.line_number || 0);
        let hash = 0;
        for (let i = 0; i < hashInput.length; i++) {
            const char = hashInput.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & 0xffffffff; // Convert to 32-bit integer
        }
        return (hash & 0xFFFFFF).toString(16).padStart(6, '0');
    }

    renderSastFindings(sastFindings) {
        const container = document.getElementById('sast-findings');
        const countBadge = document.getElementById('sast-count');

        if (!container) {
            console.error('sast-findings container not found');
            return;
        }

        if (!sastFindings || !Array.isArray(sastFindings)) {
            console.error('Invalid sastFindings data');
            container.innerHTML = '';
            const emptyDiv = this.createSecureElement('div', '', { class: 'empty-state' });
            const emptyP = this.createSecureElement('p', 'Invalid SAST findings data');
            emptyDiv.appendChild(emptyP);
            container.appendChild(emptyDiv);
            return;
        }

        // Create findings with indices for performance (avoid O(n²) lookups)
        const findingsWithIndex = sastFindings.map((finding, index) => ({
            finding,
            originalIndex: index,
            show: this.shouldShowSastFinding(finding, index)
        }));

        // Filter findings based on current filter
        const filteredFindings = findingsWithIndex.filter(item => item.show);

        if (countBadge) {
            countBadge.textContent = filteredFindings.length;
        }

        if (filteredFindings.length === 0) {
            let emptyMessage = 'No SAST findings found';
            if (this.currentFilter === 'unmapped') emptyMessage = '🎉 All SAST findings have been mapped!';
            else if (this.currentFilter === 'mapped') emptyMessage = 'No mapped SAST findings yet';

            container.innerHTML = '';
            const emptyDiv = this.createSecureElement('div', '', { class: 'empty-state' });
            const emptyP = this.createSecureElement('p', emptyMessage);
            emptyDiv.appendChild(emptyP);
            container.appendChild(emptyDiv);
            return;
        }

        container.innerHTML = filteredFindings.map(({finding, originalIndex}) => {
            // Use backend-provided ID if available, otherwise generate
            const findingId = finding.id || `sast_${originalIndex}_${this.generateId(finding)}`;
            const isMapped = this.mappedSastFindings.has(findingId);

            return `
            <div class="vulnerability-item sast-finding ${isMapped ? 'mapped' : ''}" data-finding-index="${originalIndex}">
                <div class="vulnerability-details">
                    <div class="vulnerability-main">
                        <div class="vulnerability-header">
                            <span class="vulnerability-type">${this.escapeHtml(finding.vuln_type || 'Unknown')}</span>
                            ${isMapped ? '<span class="mapping-indicator">✅</span>' : ''}
                        </div>
                        <div class="vulnerability-file" title="${this.escapeHtml(finding.file_path || 'Unknown')}">
                            📁 ${this.escapeHtml(this.truncateFilePath(finding.file_path))}
                        </div>
                        <div class="vulnerability-line-info">
                            <span class="line-number">Line ${finding.line_number || 'N/A'}</span>
                        </div>
                    </div>
                    <div class="vulnerability-meta">
                        <span class="vulnerability-severity ${(finding.severity || 'UNKNOWN').toUpperCase()}">
                            ${(finding.severity || 'UNKNOWN').toUpperCase()}
                        </span>
                    </div>
                </div>
                ${finding.description ? `<div class="vulnerability-description">${this.escapeHtml(finding.description)}</div>` : ''}
            </div>
            `;
        }).join('');

        // Add event listeners after creating the HTML
        setTimeout(() => {
            document.querySelectorAll('.sast-finding').forEach((item) => {
                if (!item || !item.getAttribute) {
                    console.warn('Invalid SAST finding element found');
                    return;
                }

                const indexAttr = item.getAttribute('data-finding-index');
                if (!indexAttr) {
                    console.warn('Missing data-finding-index attribute');
                    return;
                }

                const originalIndex = parseInt(indexAttr);
                if (isNaN(originalIndex)) {
                    console.warn('Invalid finding index:', indexAttr);
                    return;
                }

                item.addEventListener('click', () => this.selectSastFinding(originalIndex));
            });
        }, 0);

        this.sastFindings = sastFindings;
    }

    selectSastFinding(findingIndex) {
        try {
            if (typeof findingIndex !== 'number' || findingIndex < 0) {
                throw new Error('Invalid finding index');
            }

            if (!this.sastFindings || !Array.isArray(this.sastFindings)) {
                throw new Error('SAST findings not available');
            }

            if (findingIndex >= this.sastFindings.length) {
                throw new Error('Finding index out of range');
            }

            this.showLoadingOverlay('Loading potential matches...');

            // Update active state
            document.querySelectorAll('.sast-finding').forEach(item => {
                if (item && item.classList) {
                    item.classList.remove('selected');
                }
            });

            const selectedElement = document.querySelector(`[data-finding-index="${findingIndex}"]`);
            if (selectedElement && selectedElement.classList) {
                selectedElement.classList.add('selected');
            }

            this.currentFinding = this.sastFindings[findingIndex];
            if (this.currentFinding) {
                this.renderSelectedFinding(this.currentFinding, findingIndex);
            } else {
                throw new Error('Selected finding is null or undefined');
            }

        } catch (error) {
            console.error('Error selecting SAST finding:', error);
            const container = document.getElementById('selected-finding');
            if (container) {
                container.innerHTML = `<div class="error-state"><p>Failed to select finding: ${error.message}</p></div>`;
            }
        } finally {
            this.hideLoadingOverlay();
        }
    }

    renderSelectedFinding(finding, findingIndex) {
        const container = document.getElementById('selected-finding');

        container.innerHTML = `
            <div class="finding-header">
                <div class="finding-title">📍 Selected SAST Finding #${findingIndex + 1}</div>
                <div class="vulnerability-details">
                    <div class="vulnerability-main">
                        <div class="vulnerability-type">${this.escapeHtml(finding.vuln_type || 'Unknown')}</div>
                        <div class="vulnerability-file">📁 ${this.escapeHtml(finding.file_path || 'Unknown')}</div>
                        <div class="vulnerability-line-info">
                            <span class="line-number">Line ${finding.line_number || 'N/A'}</span>
                            <span class="vulnerability-severity ${(finding.severity || 'UNKNOWN').toUpperCase()}">
                                ${(finding.severity || 'UNKNOWN').toUpperCase()}
                            </span>
                        </div>
                    </div>
                </div>
                ${finding.description ? `<div class="vulnerability-description">${this.escapeHtml(finding.description)}</div>` : ''}
            </div>

            <div class="potential-matches">
                <h4>🎯 Potential Benchmark Matches</h4>
                <div id="match-suggestions" class="match-list">
                    <div class="loading-state">
                        <div class="spinner"></div>
                        <p>Analyzing potential matches...</p>
                    </div>
                </div>
            </div>
        `;

        // Load potential matches for this finding
        this.loadMatchesForFinding(finding, findingIndex);
    }

    async loadMatchesForFinding(finding, findingIndex) {
        try {
            console.log('DEBUG: loadMatchesForFinding called', finding, findingIndex);

            // Safety checks
            if (!finding) {
                throw new Error('Finding is null or undefined');
            }

            if (!this.fileData) {
                throw new Error('FileData not initialized');
            }

            if (!document.getElementById('match-suggestions')) {
                throw new Error('match-suggestions container not found');
            }

            console.log('DEBUG: fileData keys:', Object.keys(this.fileData));
            console.log('DEBUG: looking for file_path:', finding.file_path);

            // Get all benchmark vulnerabilities from the same file
            const sourceFileData = this.fileData[finding.file_path];
            console.log('DEBUG: sourceFileData:', sourceFileData);

            if (!sourceFileData || !sourceFileData.benchmark_vulns) {
                // If no benchmark data for this specific file, check all files for any matches
                const allBenchmarkVulns = [];
                Object.values(this.fileData).forEach(fileData => {
                    if (fileData.benchmark_vulns) {
                        console.log('DEBUG: adding benchmark vulns from file:', fileData.file_path, fileData.benchmark_vulns.length);
                        allBenchmarkVulns.push(...fileData.benchmark_vulns);
                    }
                });

                console.log('DEBUG: total benchmark vulns found:', allBenchmarkVulns.length);

                if (allBenchmarkVulns.length === 0) {
                    document.getElementById('match-suggestions').innerHTML =
                        '<div class="empty-state"><p>No benchmark vulnerabilities found</p></div>';
                    return;
                }

                const potentialMatches = this.findPotentialMatches(finding, allBenchmarkVulns);
                console.log('DEBUG: potential matches found:', potentialMatches.length);
                this.renderPotentialMatches(potentialMatches, findingIndex);
                return;
            }

            const potentialMatches = this.findPotentialMatches(finding, sourceFileData.benchmark_vulns);
            console.log('DEBUG: potential matches from same file:', potentialMatches.length);
            this.renderPotentialMatches(potentialMatches, findingIndex);

        } catch (error) {
            console.error('Error loading matches:', error);
            console.error('Error details:', error.stack);
            console.error('Finding data:', finding);
            console.error('FindingIndex:', findingIndex);
            console.error('FileData keys:', Object.keys(this.fileData || {}));

            const matchContainer = document.getElementById('match-suggestions');
            if (matchContainer) {
                matchContainer.innerHTML = `<div class="error-state">
                    <p>Failed to load potential matches</p>
                    <small>Error: ${error.message}</small>
                </div>`;
            } else {
                console.error('match-suggestions element not found!');
            }
        }
    }

    findPotentialMatches(sastFinding, benchmarkVulns) {
        return benchmarkVulns.map(benchVuln => {
            let score = 0;
            let reasons = [];

            // File path match (should always match since we're looking at same file)
            if (sastFinding.file_path === benchVuln.file_path) {
                score += 50;
                reasons.push('Same file');
            }

            // Line proximity
            const lineDiff = Math.abs((sastFinding.line_number || 0) - (benchVuln.line_number || 0));
            if (lineDiff <= 2) {
                score += 30;
                reasons.push('Adjacent lines');
            } else if (lineDiff <= 5) {
                score += 20;
                reasons.push('Nearby lines');
            } else if (lineDiff <= 10) {
                score += 10;
                reasons.push('Same general area');
            }

            // Vulnerability type similarity (fuzzy match)
            const sastType = (sastFinding.vuln_type || '').toLowerCase();
            const benchType = (benchVuln.vuln_type || '').toLowerCase();

            if (sastType === benchType) {
                score += 30;
                reasons.push('Exact type match');
            } else if (sastType.includes('sql') && benchType.includes('sql')) {
                score += 25;
                reasons.push('SQL-related');
            } else if (sastType.includes('xss') && benchType.includes('xss')) {
                score += 25;
                reasons.push('XSS-related');
            } else if (sastType.includes('injection') && benchType.includes('injection')) {
                score += 20;
                reasons.push('Injection-related');
            }

            // Severity similarity
            const sastSev = (sastFinding.severity || '').toLowerCase();
            const benchSev = (benchVuln.severity || '').toLowerCase();
            if (sastSev === benchSev) {
                score += 10;
                reasons.push('Same severity');
            }

            return {
                benchmarkVuln: benchVuln,
                confidence: Math.min(100, score),
                reasoning: reasons.join(', '),
                sastFinding: sastFinding
            };
        }).filter(match => {
            // Use the actual confidence slider value
            const confidenceThreshold = document.getElementById('confidence-slider')?.value || 0;
            return match.confidence >= confidenceThreshold;
        }).sort((a, b) => b.confidence - a.confidence) // Sort by confidence
          .slice(0, 10); // Show more matches (up to 10)
    }

    renderPotentialMatches(matches, findingIndex) {
        const container = document.getElementById('match-suggestions');

        if (!container) {
            console.error('match-suggestions container not found');
            return;
        }

        if (!matches || !Array.isArray(matches)) {
            console.error('Invalid matches data');
            container.innerHTML = '<div class="error-state"><p>Invalid matches data</p></div>';
            return;
        }

        if (typeof findingIndex !== 'number' || findingIndex < 0) {
            console.error('Invalid finding index for matches');
            container.innerHTML = '<div class="error-state"><p>Invalid finding index</p></div>';
            return;
        }

        // Force scrollable styling
        container.style.maxHeight = '400px';
        container.style.overflowY = 'auto';
        container.style.overflowX = 'hidden';

        if (matches.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No potential matches found</p>
                    <button class="btn btn-warning btn-sm" data-action="never-match" data-finding-index="${findingIndex}">
                        🚫 Mark as "Never Match"
                    </button>
                    <p style="font-size: 0.8rem; color: #6c757d; margin-top: 0.5rem;">
                        This will create a negative rule to filter out this SAST finding type in future bulk mappings
                    </p>
                </div>
            `;

            // Add event listener for never match button
            setTimeout(() => {
                const neverMatchBtn = document.querySelector('[data-action="never-match"]');
                if (neverMatchBtn) {
                    neverMatchBtn.addEventListener('click', (e) => {
                        const findingIndex = e.target.getAttribute('data-finding-index');
                        this.markAsNeverMatch(parseInt(findingIndex));
                    });
                }
            }, 0);
            return;
        }

        // Check for auto-mapping
        this.checkAutoMapping(matches, findingIndex);

        container.innerHTML = matches.map((match, matchIndex) => {
            const confidenceClass = match.confidence >= 80 ? 'high' : match.confidence >= 60 ? 'medium' : 'low';
            const sastFinding = this.sastFindings ? this.sastFindings[findingIndex] : null;

            return `
                <div class="match-item" data-match-index="${matchIndex}">
                    <div class="match-header">
                        <span class="match-confidence ${confidenceClass}">${match.confidence}%</span>
                        <div class="match-title">${this.escapeHtml(match.benchmarkVuln.vuln_type || 'Unknown')}</div>
                    </div>

                    <div class="code-comparison">
                        <div class="code-section sast-code">
                            <div class="code-label">🔍 SAST Finding - Line ${sastFinding?.line_number || 'N/A'}</div>
                            <div class="code-snippet">
                                <pre><code>${this.escapeHtml(sastFinding?.code || sastFinding?.description || 'No code available')}</code></pre>
                            </div>
                        </div>

                        <div class="code-section benchmark-code">
                            <div class="code-label">🎯 Benchmark - Line ${match.benchmarkVuln.line_number || 'N/A'}</div>
                            <div class="code-snippet">
                                <pre><code>${this.escapeHtml(match.benchmarkVuln.code || match.benchmarkVuln.description || 'No code available')}</code></pre>
                            </div>
                        </div>
                    </div>

                    <div class="match-details">
                        <div class="match-file">📁 ${this.escapeHtml(match.benchmarkVuln.file_path || 'Unknown file')}</div>
                        <div class="match-reasoning">🧠 ${this.escapeHtml(match.reasoning)}</div>
                        ${match.benchmarkVuln.description ? `<div class="match-description">${this.escapeHtml(match.benchmarkVuln.description)}</div>` : ''}
                    </div>
                    <div class="match-actions">
                        <button class="btn btn-success btn-sm" data-action="accept" data-finding-index="${findingIndex}" data-match-index="${matchIndex}">
                            ✅ Accept Match
                        </button>
                        <button class="btn btn-danger btn-sm" data-action="reject" data-finding-index="${findingIndex}" data-match-index="${matchIndex}">
                            ❌ Reject
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Add "Never Match" option at the end for when none of the matches are good
        container.innerHTML += `
            <div class="never-match-section">
                <div class="divider">
                    <span>None of the above matches are correct?</span>
                </div>
                <div class="never-match-action">
                    <button class="btn btn-warning btn-sm" data-action="never-match" data-finding-index="${findingIndex}">
                        🚫 Mark as "Never Match"
                    </button>
                    <p style="font-size: 0.8rem; color: #6c757d; margin-top: 0.5rem;">
                        This creates a negative rule to filter out this SAST finding type in future bulk mappings
                    </p>
                </div>
            </div>
        `;

        this.currentMatches = matches;

        // Add event listeners for match action buttons
        setTimeout(() => {
            document.querySelectorAll('[data-action="accept"]').forEach(button => {
                button.addEventListener('click', (e) => {
                    console.log('🔧 DEBUG: Accept button clicked!');
                    const findingIndex = e.target.getAttribute('data-finding-index');
                    const matchIndex = e.target.getAttribute('data-match-index');
                    console.log('🔧 DEBUG: Button data:', { findingIndex, matchIndex });
                    this.acceptMatch(parseInt(findingIndex), parseInt(matchIndex));
                });
            });
            document.querySelectorAll('[data-action="reject"]').forEach(button => {
                button.addEventListener('click', (e) => {
                    console.log('🔧 DEBUG: Reject button clicked!');
                    const findingIndex = e.target.getAttribute('data-finding-index');
                    const matchIndex = e.target.getAttribute('data-match-index');
                    this.rejectMatch(parseInt(findingIndex), parseInt(matchIndex));
                });
            });
            document.querySelectorAll('[data-action="never-match"]').forEach(button => {
                button.addEventListener('click', (e) => {
                    console.log('🔧 DEBUG: Never Match button clicked!');
                    const findingIndex = e.target.getAttribute('data-finding-index');
                    this.markAsNeverMatch(parseInt(findingIndex));
                });
            });
            console.log('🔧 DEBUG: Event listeners attached to', document.querySelectorAll('[data-action="accept"]').length, 'accept buttons');

            // Process auto-mapping after event listeners are attached
            this.processAutoMappingForCurrentMatches();
        }, 0);
    }

    async acceptMatch(findingIndex, matchIndex) {
        try {
            console.log('🔧 DEBUG: acceptMatch called', { findingIndex, matchIndex });

            // Validate parameters
            if (typeof findingIndex !== 'number' || findingIndex < 0) {
                throw new Error('Invalid finding index');
            }

            if (typeof matchIndex !== 'number' || matchIndex < 0) {
                throw new Error('Invalid match index');
            }

            if (!this.currentSession) {
                throw new Error('No active session');
            }

            if (!this.currentMatches || !Array.isArray(this.currentMatches)) {
                throw new Error('No current matches available');
            }

            if (!this.sastFindings || !Array.isArray(this.sastFindings)) {
                throw new Error('No SAST findings available');
            }

            console.log('🔧 DEBUG: currentMatches:', this.currentMatches);
            console.log('🔧 DEBUG: sastFindings:', this.sastFindings);
            console.log('🔧 DEBUG: currentSession:', this.currentSession);

            const match = this.currentMatches[matchIndex];
            const sastFinding = this.sastFindings[findingIndex];

            if (!match) {
                throw new Error(`No match found at index: ${matchIndex}`);
            }

            if (!sastFinding) {
                throw new Error(`No SAST finding at index: ${findingIndex}`);
            }

            console.log('✅ Accepting match:', {
                sastFinding: sastFinding,
                benchmarkVuln: match.benchmarkVuln,
                confidence: match.confidence
            });

            // Generate IDs if they don't exist (fallback)
            const sastId = sastFinding.id || `sast_${findingIndex}_${this.generateId(sastFinding)}`;
            const benchmarkId = match.benchmarkVuln.id || `bench_${matchIndex}_${this.generateId(match.benchmarkVuln)}`;

            console.log('Using IDs:', { sastId, benchmarkId });

            // Send mapping to backend
            const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mapping`, {
                method: 'POST',
                body: JSON.stringify({
                    action: 'confirm',
                    benchmark_id: benchmarkId,
                    sast_id: sastId
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Mapping saved to backend:', result);

                // Mark this SAST finding as mapped
                const findingId = sastFinding.id || `sast_${findingIndex}_${this.generateId(sastFinding)}`;
                this.mappedSastFindings.add(findingId);

                // Add visual feedback
                const matchElement = document.querySelector(`[data-match-index="${matchIndex}"]`);
                if (matchElement) {
                    matchElement.classList.add('accepted');
                    matchElement.innerHTML += '<div class="mapping-status">✅ Accepted - Learning pattern...</div>';
                } else {
                    console.warn('Could not find match element to update');
                }

                // Use backend auto-mapping results instead of frontend logic
                if (result.auto_mapped && result.auto_mapped.length > 0) {
                    console.log(`🧠 Backend auto-mapped ${result.auto_mapped.length} similar findings:`, result.auto_mapped);

                    // Mark auto-mapped findings as mapped
                    result.auto_mapped.forEach(autoMapping => {
                        this.mappedSastFindings.add(autoMapping.sast_id);
                        console.log(`  ✅ Auto-mapped: ${autoMapping.sast_id}`);
                    });

                    // Show user notification about auto-mapping
                    const notification = document.createElement('div');
                    notification.className = 'auto-mapping-notification';
                    notification.innerHTML = `🧠 Auto-mapped ${result.auto_mapped.length} similar findings!`;
                    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 5px; z-index: 1000; max-width: 400px;';
                    document.body.appendChild(notification);
                    setTimeout(() => notification.remove(), 5000);

                    console.log(`🎯 Auto-mapped ${result.auto_mapped.length} additional findings`);
                } else {
                    console.log('🔧 No auto-mappings returned from backend');
                }

                console.log('🔧 About to refresh UI...');

                // Refresh the display to hide newly mapped items
                console.log('🔄 Refreshing UI to reflect auto-mappings...');
                console.log(`🔧 Total mappedSastFindings: ${this.mappedSastFindings.size}`);
                console.log('🔧 Mapped IDs:', Array.from(this.mappedSastFindings));

                // Show loading for large datasets
                if (this.sastFindings.length > 500) {
                    this.showLoadingOverlay('Updating UI with auto-mappings...');
                }

                // Refresh immediately instead of using setTimeout
                try {
                    this.renderSastFindings(this.sastFindings);
                    this.updateSessionSummary(Object.values(this.fileData), this.sastFindings);
                    this.hideLoadingOverlay();

                    console.log('✅ UI refresh completed');
                } catch (error) {
                    console.error('Error refreshing UI:', error);
                    this.hideLoadingOverlay();
                }

                // If currently viewing unmapped, the auto-mapped findings should now be hidden
                if (this.currentFilter === 'unmapped') {
                    console.log(`🎯 Filtered view updated - ${this.mappedSastFindings.size} findings now marked as mapped`);
                }

                console.log('✅ Match accepted and pattern learned');

                // Recalculate batch opportunities after mapping changes
                if (this.fileData) {
                    this.detectBatchOpportunities(this.fileData);
                }
            } else {
                console.error('Failed to save mapping:', await response.text());
            }
        } catch (error) {
            console.error('Error accepting match:', error);
            this.hideLoadingOverlay();
            alert('Failed to accept match. Please check the console for details.');
        }
    }

    async rejectMatch(findingIndex, matchIndex) {
        try {
            const match = this.currentMatches[matchIndex];
            const sastFinding = this.sastFindings[findingIndex];

            console.log('Rejecting match:', {
                sastFinding: sastFinding,
                benchmarkVuln: match.benchmarkVuln
            });

            // Generate IDs if they don't exist (fallback)
            const sastId = sastFinding.id || `sast_${findingIndex}_${this.generateId(sastFinding)}`;
            const benchmarkId = match.benchmarkVuln.id || `bench_${matchIndex}_${this.generateId(match.benchmarkVuln)}`;

            // Send rejection to backend
            const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mapping`, {
                method: 'POST',
                body: JSON.stringify({
                    action: 'deny',
                    benchmark_id: benchmarkId,
                    sast_id: sastId
                })
            });

            if (response.ok) {
                // Add visual feedback
                const matchElement = document.querySelector(`[data-match-index="${matchIndex}"]`);
                matchElement.classList.add('rejected');
                matchElement.innerHTML += '<div class="mapping-status">❌ Rejected</div>';

                // Save negative mapping rule
                this.saveNegativeMapping(sastFinding, match.benchmarkVuln);

                console.log('❌ Match rejected and negative mapping saved');

                // Recalculate batch opportunities after rejection
                if (this.fileData) {
                    this.detectBatchOpportunities(this.fileData);
                }
            } else {
                console.error('Failed to save rejection:', await response.text());
            }
        } catch (error) {
            console.error('Error rejecting match:', error);
        }
    }

    checkAutoMapping(matches, findingIndex) {
        const autoMappingEnabledEl = document.getElementById('auto-mapping-enabled');
        const thresholdEl = document.getElementById('auto-mapping-threshold');

        // Check if auto-mapping controls exist
        if (!autoMappingEnabledEl || !thresholdEl) {
            console.log('Auto-mapping controls not found, skipping auto-mapping check');
            return;
        }

        const autoMappingEnabled = autoMappingEnabledEl.checked;
        const threshold = parseInt(thresholdEl.value);

        if (!autoMappingEnabled || matches.length === 0) {
            return;
        }

        // Find highest confidence match
        const bestMatch = matches[0]; // Already sorted by confidence

        if (bestMatch.confidence >= threshold) {
            console.log(`🤖 Auto-mapping enabled: Found match with ${bestMatch.confidence}% confidence (threshold: ${threshold}%)`);

            // Show notification
            const notification = document.createElement('div');
            notification.className = 'auto-mapping-notification';
            notification.innerHTML = `🤖 Auto-accepting match with ${bestMatch.confidence}% confidence!`;
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 10px; border-radius: 5px; z-index: 1000; max-width: 400px;';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);

            // Auto-accept the best match after a short delay
            setTimeout(() => {
                this.acceptMatch(findingIndex, 0); // 0 is the index of the best match
            }, 500);
        }
    }

    detectBatchOpportunities(files) {
        // Filter out already mapped vulnerabilities to find true 1:1 candidates
        const unmappedOneToOneFiles = this.findUnmappedOneToOneMatches(files);

        const batchBtn = document.getElementById('batch-review-btn');

        // Check if button exists (might not be available during initial load)
        if (!batchBtn) {
            console.log('Batch review button not found, skipping batch detection');
            return;
        }

        if (unmappedOneToOneFiles.length > 0) {
            batchBtn.disabled = false;
            batchBtn.textContent = `Batch Review ${unmappedOneToOneFiles.length} 1:1 Matches`;
            batchBtn.onclick = () => this.showBatchReview(unmappedOneToOneFiles);

            console.log(`📊 Found ${unmappedOneToOneFiles.length} unmapped files with 1:1 vulnerability matches`);
        } else {
            batchBtn.disabled = true;
            batchBtn.textContent = 'Batch Review 1:1 Matches';
            console.log('📊 No unmapped 1:1 matches available for batch review');
        }
    }

    findUnmappedOneToOneMatches(files) {
        if (!files || !Array.isArray(files)) {
            return [];
        }

        return files.filter(file => {
            // Must have exactly 1 benchmark vuln and at least 1 SAST vuln
            if (!file.benchmark_vulns || file.benchmark_vulns.length !== 1) {
                return false;
            }

            if (!file.sast_vulns || file.sast_vulns.length === 0) {
                return false;
            }

            const benchmarkVuln = file.benchmark_vulns[0];

            // Check if this benchmark vulnerability is already mapped
            const benchmarkId = benchmarkVuln.id || `bench_${this.generateId(benchmarkVuln)}`;
            if (this.mappedSastFindings && this.mappedSastFindings.has(benchmarkId)) {
                console.log(`📍 Skipping already mapped benchmark: ${benchmarkVuln.vuln_type} in ${file.file_name}`);
                return false;
            }

            // Count unmapped SAST vulnerabilities in this file
            const unmappedSastVulns = file.sast_vulns.filter(sastVuln => {
                const sastId = sastVuln.id || `sast_${this.generateId(sastVuln)}`;
                return !this.mappedSastFindings || !this.mappedSastFindings.has(sastId);
            });

            // For true 1:1 mapping, we need exactly 1 unmapped SAST vuln
            if (unmappedSastVulns.length === 1) {
                console.log(`✅ Found 1:1 candidate: ${benchmarkVuln.vuln_type} <-> ${unmappedSastVulns[0].vuln_type} in ${file.file_name}`);
                return true;
            } else if (unmappedSastVulns.length > 1) {
                console.log(`⚠️  Multiple SAST vulns (${unmappedSastVulns.length}) vs 1 benchmark in ${file.file_name} - not 1:1`);
            }

            return false;
        });
    }

    showBatchReview(oneToOneFiles) {
        const modal = document.getElementById('batch-review-modal');
        const container = document.getElementById('batch-matches-container');

        if (!modal) {
            console.error('batch-review-modal not found');
            return;
        }

        if (!container) {
            console.error('batch-matches-container not found');
            return;
        }

        if (!oneToOneFiles || !Array.isArray(oneToOneFiles)) {
            console.error('Invalid oneToOneFiles data');
            return;
        }

        // Generate batch matches with confidence scores
        const batchMatches = oneToOneFiles.map(file => {
            const benchmarkVuln = file.benchmark_vulns[0];
            const sastVuln = file.sast_vulns[0];

            // Calculate confidence based on similarity
            let confidence = 50; // Base confidence

            // Boost confidence for exact matches
            if (benchmarkVuln.vuln_type && sastVuln.vuln_type) {
                if (benchmarkVuln.vuln_type.toLowerCase().includes(sastVuln.vuln_type.toLowerCase()) ||
                    sastVuln.vuln_type.toLowerCase().includes(benchmarkVuln.vuln_type.toLowerCase())) {
                    confidence += 30;
                }
            }

            // Line proximity bonus
            if (Math.abs((benchmarkVuln.line_number || 0) - (sastVuln.line_number || 0)) <= 5) {
                confidence += 20;
            }

            confidence = Math.min(confidence, 95); // Cap at 95%

            return {
                file_path: file.file_path,
                benchmarkVuln,
                sastVuln,
                confidence,
                selected: confidence >= 70 // Auto-select high confidence matches
            };
        }).sort((a, b) => b.confidence - a.confidence); // Sort by confidence

        // Render batch matches
        container.innerHTML = batchMatches.map((match, index) => `
            <div class="batch-match-item" data-index="${index}">
                <div class="batch-match-header">
                    <label class="batch-match-checkbox">
                        <input type="checkbox" ${match.selected ? 'checked' : ''}
                               onchange="window.ui.updateBatchSelection()">
                        <span class="confidence-badge ${match.confidence >= 80 ? 'high' : match.confidence >= 60 ? 'medium' : 'low'}">
                            ${match.confidence}%
                        </span>
                        <span class="file-path">${this.truncateFilePath(match.file_path)}</span>
                    </label>
                </div>
                <div class="batch-match-content">
                    <div class="benchmark-side">
                        <h5>🎯 Benchmark Vulnerability</h5>
                        <div class="vuln-type">${this.escapeHtml(match.benchmarkVuln.vuln_type || 'Unknown')}</div>
                        <div class="vuln-line">Line ${match.benchmarkVuln.line_number || 'N/A'}</div>
                        <div class="vuln-desc">${this.escapeHtml(match.benchmarkVuln.description || '')}</div>
                    </div>
                    <div class="arrow">→</div>
                    <div class="sast-side">
                        <h5>🔍 SAST Finding</h5>
                        <div class="vuln-type">${this.escapeHtml(match.sastVuln.vuln_type || 'Unknown')}</div>
                        <div class="vuln-line">Line ${match.sastVuln.line_number || 'N/A'}</div>
                        <div class="vuln-desc">${this.escapeHtml(match.sastVuln.description || '')}</div>
                    </div>
                </div>
            </div>
        `).join('');

        // Store batch matches for approval
        this.batchMatches = batchMatches;
        this.updateBatchSelection();

        // Setup event listeners
        this.setupBatchEventListeners();

        modal.style.display = 'flex';
    }

    setupBatchEventListeners() {
        const closeBtn = document.getElementById('close-batch-review');
        if (closeBtn) {
            closeBtn.onclick = () => {
                const modal = document.getElementById('batch-review-modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            };
        }

        const selectAllBtn = document.getElementById('select-all-matches');
        if (selectAllBtn) {
            selectAllBtn.onclick = () => {
                const checkboxes = document.querySelectorAll('#batch-matches-container input[type="checkbox"]');
                checkboxes.forEach(cb => {
                    if (cb) cb.checked = true;
                });
                this.updateBatchSelection();
            };
        }

        const deselectAllBtn = document.getElementById('deselect-all-matches');
        if (deselectAllBtn) {
            deselectAllBtn.onclick = () => {
                const checkboxes = document.querySelectorAll('#batch-matches-container input[type="checkbox"]');
                checkboxes.forEach(cb => {
                    if (cb) cb.checked = false;
                });
                this.updateBatchSelection();
            };
        }

        const approveBtn = document.getElementById('approve-selected');
        if (approveBtn) {
            approveBtn.onclick = () => {
                this.approveSelectedBatchMatches();
            };
        }
    }

    updateBatchSelection() {
        const checkboxes = document.querySelectorAll('#batch-matches-container input[type="checkbox"]');
        const selectedCount = Array.from(checkboxes).filter(cb => cb && cb.checked).length;

        const selectedCountEl = document.getElementById('selected-count');
        if (selectedCountEl) {
            selectedCountEl.textContent = `${selectedCount} selected`;
        }

        const approveBtn = document.getElementById('approve-selected');
        if (approveBtn) {
            approveBtn.disabled = selectedCount === 0;
            approveBtn.textContent = `Approve ${selectedCount} Selected Matches`;
        }
    }

    async approveSelectedBatchMatches() {
        const checkboxes = document.querySelectorAll('#batch-matches-container input[type="checkbox"]');
        const selectedMatches = [];

        checkboxes.forEach((checkbox, index) => {
            if (checkbox.checked && this.batchMatches[index]) {
                selectedMatches.push(this.batchMatches[index]);
            }
        });

        if (selectedMatches.length === 0) return;

        // Show loading
        this.showLoadingOverlay(`Approving ${selectedMatches.length} batch matches...`);

        let successCount = 0;
        const ruleTypes = new Set();

        for (const match of selectedMatches) {
            try {
                // Create mapping request
                const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mapping`, {
                    method: 'POST',
                    body: JSON.stringify({
                        action: 'confirm',
                        benchmark_id: match.benchmarkVuln.id || `bench_${this.generateId(match.benchmarkVuln)}`,
                        sast_id: match.sastVuln.id || `sast_${this.generateId(match.sastVuln)}`
                    })
                });

                if (response.ok) {
                    const result = await response.json();

                    // Mark as mapped
                    this.mappedSastFindings.add(match.sastVuln.id);

                    // Track rule types for auto-application
                    if (match.sastVuln.rule_id) {
                        ruleTypes.add(match.sastVuln.rule_id);
                    }

                    // Handle auto-mapped results from backend
                    if (result.auto_mapped) {
                        result.auto_mapped.forEach(autoMapping => {
                            this.mappedSastFindings.add(autoMapping.sast_id);
                        });
                    }

                    successCount++;
                } else {
                    const errorText = await response.text();
                    console.error('Failed to approve match for', match.file_path);
                    console.error('Response status:', response.status);
                    console.error('Response body:', errorText);
                    console.error('Match data:', match);
                }
            } catch (error) {
                console.error('Error approving batch match:', error);
                console.error('Match data:', match);
                console.error('Generated IDs:', {
                    benchmark_id: match.benchmarkVuln.id || `bench_${this.generateId(match.benchmarkVuln)}`,
                    sast_id: match.sastVuln.id || `sast_${this.generateId(match.sastVuln)}`
                });
            }
        }

        this.hideLoadingOverlay();

        // Show results
        const notification = document.createElement('div');
        notification.className = 'batch-approval-notification';
        notification.innerHTML = `✅ Approved ${successCount}/${selectedMatches.length} batch matches!<br>
                                 🧠 Auto-applied ${ruleTypes.size} rule types to similar findings`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);

        // Close modal and refresh UI
        document.getElementById('batch-review-modal').style.display = 'none';
        this.renderSastFindings(this.sastFindings);
        this.updateSessionSummary(Object.values(this.fileData), this.sastFindings);
        this.detectBatchOpportunities(Object.values(this.fileData));

        console.log(`✅ Batch approval completed: ${successCount}/${selectedMatches.length} matches approved`);
    }

    showBulkMappingWorkflow(oneToOneFiles, allFiles, allSastFindings) {
        // Validate inputs first
        if (!oneToOneFiles || !Array.isArray(oneToOneFiles)) {
            console.error('Invalid oneToOneFiles data');
            return;
        }

        if (!allFiles || !Array.isArray(allFiles)) {
            console.error('Invalid allFiles data');
            return;
        }

        if (!allSastFindings || !Array.isArray(allSastFindings)) {
            console.error('Invalid allSastFindings data');
            return;
        }

        // Remove any existing bulk mapping container to prevent duplication
        const existingBulkContainer = document.getElementById('bulk-mapping-container');
        if (existingBulkContainer) {
            existingBulkContainer.remove();
            console.log('🗑️ Removed existing bulk mapping container');
        }

        // Hide the normal interface
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.style.display = 'none';
        }

        // Calculate confidence scores and group by SAST rule ID - ALL DATA PROCESSING FIRST
        const bulkMatches = oneToOneFiles.map((file, index) => {
            if (!file || !file.benchmark_vulns || !file.sast_vulns) {
                console.warn('Invalid file data:', file);
                return null;
            }

            const benchmarkVuln = file.benchmark_vulns[0];
            const sastVuln = file.sast_vulns[0];

            if (!benchmarkVuln || !sastVuln) {
                console.warn('Missing vulnerabilities in file:', file.file_path);
                return null;
            }

            // Calculate confidence
            let confidence = 60; // Base confidence for 1:1 matches

            // Type similarity
            if (benchmarkVuln.vuln_type && sastVuln.vuln_type) {
                const benchType = benchmarkVuln.vuln_type.toLowerCase();
                const sastType = sastVuln.vuln_type.toLowerCase();
                if (benchType.includes(sastType) || sastType.includes(benchType)) {
                    confidence += 25;
                }
            }

            // Line proximity
            const lineDiff = Math.abs((benchmarkVuln.line_number || 0) - (sastVuln.line_number || 0));
            if (lineDiff <= 3) confidence += 15;
            else if (lineDiff <= 10) confidence += 5;

            confidence = Math.min(confidence, 95);

            // Find the best identifier for grouping
            const fullRuleId = sastVuln.rule_id || sastVuln.rule || sastVuln.check_id || sastVuln.test_name || sastVuln.vuln_type || 'unknown';
            const shortRuleId = fullRuleId.split('.').pop() || fullRuleId;

            // Check negative mappings - filter out explicitly rejected combinations
            const sastRuleId = fullRuleId;
            const benchmarkType = benchmarkVuln.vuln_type || 'unknown';
            const negativeRule = `${sastRuleId}!==${benchmarkType}`;

            if (this.negativeMappingRules && this.negativeMappingRules.has(negativeRule)) {
                console.log(`🚫 Filtered out negative mapping: ${sastRuleId} != ${benchmarkType} in ${file.file_path}`);
                return null; // Filter out this match
            }

            return {
                file_path: file.file_path,
                benchmarkVuln,
                sastVuln,
                confidence,
                selected: confidence >= 75, // Auto-select high confidence
                index,
                ruleId: fullRuleId,
                shortRuleId: shortRuleId
            };
        }).filter(match => match !== null); // Remove invalid entries

        // Group by rule ID
        const groupedMatches = bulkMatches.reduce((groups, match) => {
            const ruleId = match.ruleId;
            if (!groups[ruleId]) {
                groups[ruleId] = [];
            }
            groups[ruleId].push(match);
            return groups;
        }, {});

        // Sort groups by count (largest first) and within groups by confidence
        const sortedGroups = Object.entries(groupedMatches)
            .sort((a, b) => b[1].length - a[1].length) // Sort by group size
            .map(([ruleId, matches]) => ({
                ruleId,
                shortRuleId: matches[0] ? matches[0].shortRuleId : 'unknown',
                matches: matches.sort((a, b) => b.confidence - a.confidence), // Sort by confidence within group
                avgConfidence: Math.round(matches.reduce((sum, m) => sum + m.confidence, 0) / matches.length),
                allSelected: matches.every(m => m.selected)
            }));

        // Flatten grouped matches back to array for processing
        const flattenedMatches = sortedGroups.flatMap(group => group.matches);

        // Create bulk mapping interface AFTER all data is processed
        const bulkContainer = document.createElement('div');
        if (!bulkContainer) {
            console.error('Failed to create bulk container');
            return;
        }

        bulkContainer.id = 'bulk-mapping-container';
        bulkContainer.className = 'bulk-mapping-workflow';

        bulkContainer.innerHTML = `
            <div class="bulk-controls">
                <div class="bulk-controls-header">
                    <h3>Review ${oneToOneFiles.length} vulnerability rule groups with 1:1 matches</h3>
                    <p>Select rules to auto-map, then proceed to detailed mapping for complex cases.</p>
                </div>

                <div class="bulk-search-section">
                    <input type="text" id="bulk-search-input" class="search-input" placeholder="🔍 Search vulnerability types, rule IDs, or descriptions...">
                    <button id="bulk-clear-search" class="btn btn-sm btn-outline-secondary" style="margin-left: 0.5rem;">Clear</button>
                </div>

                <div class="bulk-controls-actions">
                    <div class="bulk-action-buttons">
                        <button id="bulk-select-all" class="btn btn-primary">✓ Select All Groups</button>
                        <button id="bulk-select-visible" class="btn btn-info">✓ Select All Visible</button>
                        <button id="bulk-select-high-confidence" class="btn btn-success">✓ Select High Confidence (75%+)</button>
                        <button id="bulk-deselect-all" class="btn btn-secondary">✗ Deselect All</button>
                        <div class="bulk-stats">
                            <span id="bulk-selected-count">0 selected</span> •
                            <span id="bulk-high-confidence-count">0 high confidence</span> •
                            <span id="bulk-visible-count">${sortedGroups.length} visible</span>
                        </div>
                        <div class="bulk-actions">
                            <button id="bulk-approve" class="btn btn-success" disabled>Apply Selected & Remove</button>
                            <button id="bulk-proceed" class="btn btn-primary">Proceed to Detailed Mapping</button>
                            <button id="bulk-skip" class="btn btn-outline-secondary">Skip All Bulk Mapping</button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bulk-vulnerability-groups">
                ${sortedGroups.map((group, groupIdx) => {
                    const firstMatch = group.matches[0];
                    const sastDesc = firstMatch.sastVuln.description || 'No description available';

                    // Use benchmark description as-is
                    const benchDesc = firstMatch.benchmarkVuln.description || 'No description available';

                    return `
                    <div class="vulnerability-group-card" data-rule-id="${this.escapeHtml(group.ruleId)}">
                        <div class="group-header">
                            <div class="group-selection">
                                <input type="checkbox"
                                       class="group-checkbox"
                                       data-rule-id="${this.escapeHtml(group.ruleId)}"
                                       ${group.allSelected ? 'checked' : ''}
                                       title="Select/Deselect all ${group.matches.length} instances">
                                <span class="group-confidence ${group.avgConfidence >= 80 ? 'high' : group.avgConfidence >= 60 ? 'medium' : 'low'}">
                                    ${group.avgConfidence}%
                                </span>
                            </div>
                            <div class="group-info">
                                <div class="group-title">
                                    <h4>${this.escapeHtml(group.shortRuleId)}</h4>
                                    <span class="instance-count">${group.matches.length} instances</span>
                                    <button class="btn btn-success btn-sm bulk-match-btn"
                                            data-rule-id="${this.escapeHtml(group.ruleId)}"
                                            data-sast-rule="${this.escapeHtml(firstMatch.sastVuln.rule_id || firstMatch.sastVuln.vuln_type || 'unknown')}"
                                            data-benchmark-type="${this.escapeHtml(firstMatch.benchmarkVuln.vuln_type || 'unknown')}"
                                            title="Accept and apply this mapping to all ${group.matches.length} instances">
                                        ✅ Match All
                                    </button>
                                    <button class="btn btn-warning btn-sm bulk-never-match-btn"
                                            data-sast-rule="${this.escapeHtml(firstMatch.sastVuln.rule_id || firstMatch.sastVuln.vuln_type || 'unknown')}"
                                            data-benchmark-type="${this.escapeHtml(firstMatch.benchmarkVuln.vuln_type || 'unknown')}"
                                            title="Mark this combination as never matching">
                                        🚫 Never Match
                                    </button>
                                    <button class="toggle-files-btn" onclick="window.ui.toggleFileList('${this.escapeHtml(group.ruleId)}')">
                                        <span class="toggle-icon">▼</span> Show Files
                                    </button>
                                </div>
                                <div class="full-rule-id">${this.escapeHtml(group.ruleId)}</div>
                            </div>
                            <div class="group-actions">
                                <!-- Buttons moved to group-title for better UX -->
                            </div>
                        </div>

                        <div class="vulnerability-descriptions">
                            <div class="sast-description">
                                <div class="desc-header">🔍 SAST Finding</div>
                                <div class="desc-type">${this.escapeHtml(firstMatch.sastVuln.vuln_type || 'Unknown Type')}</div>
                                <div class="desc-text">${this.escapeHtml(sastDesc)}</div>
                            </div>
                            <div class="mapping-arrow">→</div>
                            <div class="benchmark-description">
                                <div class="desc-header">🎯 Benchmark Vulnerability</div>
                                <div class="desc-type">${this.escapeHtml(firstMatch.benchmarkVuln.vuln_type || 'Unknown Type')}</div>
                                <div class="desc-text">${this.escapeHtml(benchDesc)}</div>
                            </div>
                        </div>

                        <div class="files-list" id="files-list-${this.escapeHtml(group.ruleId)}" style="display: none;">
                            <div class="files-header">
                                <span>Select individual files to exclude:</span>
                            </div>
                            <div class="files-grid">
                                ${group.matches.map((match, idx) => {
                                    const globalIndex = flattenedMatches.findIndex(m => m === match);
                                    return `
                                    <div class="file-item">
                                        <label class="file-checkbox">
                                            <input type="checkbox"
                                                   ${match.selected ? 'checked' : ''}
                                                   data-index="${globalIndex}"
                                                   data-rule-id="${this.escapeHtml(group.ruleId)}"
                                                   onchange="window.ui.updateBulkStats()">
                                            <div class="file-info">
                                                <div class="file-path" title="${this.escapeHtml(match.file_path)}">
                                                    ${this.truncateFilePath(match.file_path, 50)}
                                                </div>
                                                <div class="file-details">
                                                    <span class="confidence-mini ${match.confidence >= 80 ? 'high' : match.confidence >= 60 ? 'medium' : 'low'}">
                                                        ${match.confidence}%
                                                    </span>
                                                    <span class="line-info">
                                                        SAST: L${match.sastVuln.line_number || '?'} →
                                                        Benchmark: L${match.benchmarkVuln.line_number || '?'}
                                                    </span>
                                                </div>
                                            </div>
                                        </label>
                                    </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                    `;
                }).join('')}
            </div>
        `;

        // Insert before main content
        if (mainContent && mainContent.parentNode) {
            mainContent.parentNode.insertBefore(bulkContainer, mainContent);
        }

        // Store data for later use
        this.bulkMatches = flattenedMatches;
        this.bulkGroups = sortedGroups;
        this.allFiles = allFiles;
        this.allSastFindings = allSastFindings;

        // Setup event listeners after DOM is ready
        setTimeout(() => {
            this.setupBulkMappingEventListeners();
            this.updateBulkStats();
        }, 100);
    }

    showDetailedMappingInterface(files, allSastFindings) {
        console.log('🔄 Switching to detailed mapping interface...');
        console.log('📊 Session check:', this.currentSession);

        // Validate session before showing interface
        if (!this.currentSession) {
            console.error('❌ No session available for detailed mapping');

            // Try to restore session
            const storedSessionId = sessionManager?.getSessionId();
            if (storedSessionId) {
                console.log('🔄 Restoring session:', storedSessionId);
                this.currentSession = storedSessionId;
            } else {
                console.error('❌ Cannot restore session - user needs to upload files again');
                // Show error message to user
                const mainContent = document.querySelector('.main-content');
                if (mainContent) {
                    mainContent.innerHTML = `
                        <div style="text-align: center; padding: 2rem; color: #dc3545;">
                            <h3>Session Lost</h3>
                            <p>Your session has been lost. Please refresh the page and upload your files again.</p>
                            <button onclick="window.location.reload()" class="btn btn-primary">Refresh Page</button>
                        </div>
                    `;
                }
                return;
            }
        }

        // Show the normal detailed mapping interface
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.style.display = 'flex';
        }

        // Remove bulk interface if it exists
        const bulkContainer = document.getElementById('bulk-mapping-container');
        if (bulkContainer) {
            bulkContainer.remove();
        }

        this.renderSastFindings(allSastFindings);
        this.updateSessionSummary(files, allSastFindings);
        this.detectBatchOpportunities(files);
    }

    setupBulkMappingEventListeners() {
        console.log('🔧 Setting up bulk mapping event listeners...');

        const selectAllBtn = document.getElementById('bulk-select-all');
        if (selectAllBtn) {
            console.log('✅ Found select-all button');
            selectAllBtn.addEventListener('click', () => {
                console.log('🔧 Select All clicked');
                document.querySelectorAll('.file-checkbox input[type="checkbox"], .group-checkbox').forEach(cb => {
                    if (cb) cb.checked = true;
                });
                this.updateBulkStats();
            });
        } else {
            console.error('❌ bulk-select-all button not found');
        }

        const selectVisibleBtn = document.getElementById('bulk-select-visible');
        if (selectVisibleBtn) {
            console.log('✅ Found select-visible button');
            selectVisibleBtn.addEventListener('click', () => {
                console.log('🔧 Select All Visible clicked');
                this.selectAllVisibleGroups();
            });
        } else {
            console.error('❌ bulk-select-visible button not found');
        }

        const selectHighConfBtn = document.getElementById('bulk-select-high-confidence');
        if (selectHighConfBtn) {
            console.log('✅ Found select-high-confidence button');
            selectHighConfBtn.addEventListener('click', () => {
                console.log('🔧 Select High Confidence clicked');
                document.querySelectorAll('.bulk-match-row').forEach((row, idx) => {
                    const checkbox = row.querySelector('input[type="checkbox"]');
                    if (checkbox && this.bulkMatches[idx]) {
                        checkbox.checked = this.bulkMatches[idx].confidence >= 75;
                    }
                });
                this.updateBulkStats();
            });
        } else {
            console.error('❌ bulk-select-high-confidence button not found');
        }

        const deselectAllBtn = document.getElementById('bulk-deselect-all');
        if (deselectAllBtn) {
            console.log('✅ Found deselect-all button');
            deselectAllBtn.addEventListener('click', () => {
                console.log('🔧 Deselect All clicked');
                document.querySelectorAll('.file-checkbox input[type="checkbox"], .group-checkbox').forEach(cb => {
                    if (cb) cb.checked = false;
                });
                this.updateBulkStats();
            });
        } else {
            console.error('❌ bulk-deselect-all button not found');
        }

        const approveBtn = document.getElementById('bulk-approve');
        if (approveBtn) {
            console.log('✅ Found approve button');
            approveBtn.addEventListener('click', () => {
                console.log('🔧 Approve clicked');
                this.processBulkMappings();
            });
        } else {
            console.error('❌ bulk-approve button not found');
        }

        const proceedBtn = document.getElementById('bulk-proceed');
        if (proceedBtn) {
            console.log('✅ Found proceed button');
            proceedBtn.addEventListener('click', () => {
                console.log('🔧 Proceed clicked');
                this.proceedToDetailedMapping();
            });
        } else {
            console.error('❌ bulk-proceed button not found');
        }

        const skipBtn = document.getElementById('bulk-skip');
        if (skipBtn) {
            console.log('✅ Found skip button');
            skipBtn.addEventListener('click', () => {
                console.log('🔧 Skip clicked');
                this.skipBulkMapping();
            });
        } else {
            console.error('❌ bulk-skip button not found');
        }

        // Search functionality
        const searchInput = document.getElementById('bulk-search-input');
        if (searchInput) {
            console.log('✅ Found search input');
            searchInput.addEventListener('input', (e) => {
                this.filterBulkGroups(e.target.value);
            });
        } else {
            console.error('❌ bulk-search-input not found');
        }

        const clearSearchBtn = document.getElementById('bulk-clear-search');
        if (clearSearchBtn) {
            console.log('✅ Found clear search button');
            clearSearchBtn.addEventListener('click', () => {
                const searchInput = document.getElementById('bulk-search-input');
                if (searchInput) {
                    searchInput.value = '';
                    this.filterBulkGroups('');
                }
            });
        } else {
            console.error('❌ bulk-clear-search button not found');
        }

        // Header checkbox for select/deselect all
        const headerCheckbox = document.getElementById('bulk-header-checkbox');
        if (headerCheckbox) {
            headerCheckbox.addEventListener('change', () => {
                const checked = headerCheckbox.checked;
                document.querySelectorAll('.bulk-match-row input[type="checkbox"]').forEach(cb => {
                    if (cb) cb.checked = checked;
                });
                this.updateBulkStats();
            });
        }

        // Group checkbox listeners
        document.querySelectorAll('.group-checkbox').forEach(cb => {
            if (cb) {
                cb.addEventListener('change', (e) => {
                    const ruleId = e.target.getAttribute('data-rule-id');
                    const checked = e.target.checked;

                    // Select/deselect all matches in this group
                    document.querySelectorAll(`.file-checkbox input[data-rule-id="${ruleId}"]`).forEach(matchCb => {
                        if (matchCb) matchCb.checked = checked;
                    });

                    this.updateBulkStats();
                });
            }
        });

        // Also add change listeners to file checkboxes for live stats updates
        document.querySelectorAll('.file-checkbox input[type="checkbox"]').forEach(cb => {
            if (cb) {
                cb.addEventListener('change', () => this.updateBulkStats());
            }
        });

        // Bulk "Match All" button listeners
        document.querySelectorAll('.bulk-match-btn').forEach(btn => {
            if (btn) {
                btn.addEventListener('click', (e) => {
                    const ruleId = e.target.getAttribute('data-rule-id');
                    const sastRule = e.target.getAttribute('data-sast-rule');
                    const benchmarkType = e.target.getAttribute('data-benchmark-type');
                    this.bulkMatchAll(ruleId, sastRule, benchmarkType, e.target);
                });
            }
        });

        // Bulk "Never Match" button listeners
        document.querySelectorAll('.bulk-never-match-btn').forEach(btn => {
            if (btn) {
                btn.addEventListener('click', (e) => {
                    const sastRule = e.target.getAttribute('data-sast-rule');
                    const benchmarkType = e.target.getAttribute('data-benchmark-type');
                    this.bulkMarkAsNeverMatch(sastRule, benchmarkType, e.target);
                });
            }
        });

        console.log('🔧 Bulk mapping event listeners setup complete');
    }

    toggleFileList(ruleId) {
        const filesList = document.getElementById(`files-list-${ruleId}`);
        const toggleBtn = document.querySelector(`[onclick="window.ui.toggleFileList('${ruleId}')"]`);

        if (!filesList || !toggleBtn) {
            console.error('Toggle elements not found for rule:', ruleId);
            return;
        }

        const isVisible = filesList.style.display !== 'none';
        const toggleIcon = toggleBtn.querySelector('.toggle-icon');

        if (isVisible) {
            filesList.style.display = 'none';
            if (toggleIcon) toggleIcon.textContent = '▼';
            toggleBtn.innerHTML = '<span class="toggle-icon">▼</span> Show Files';
        } else {
            filesList.style.display = 'block';
            if (toggleIcon) toggleIcon.textContent = '▲';
            toggleBtn.innerHTML = '<span class="toggle-icon">▲</span> Hide Files';
        }
    }

    bulkMarkAsNeverMatch(sastRule, benchmarkType, buttonElement) {
        if (!sastRule || !benchmarkType) {
            console.error('Missing sastRule or benchmarkType for negative mapping');
            return;
        }

        // Create negative mapping rule
        const negativeRule = `${sastRule}!==${benchmarkType}`;
        this.negativeMappingRules.add(negativeRule);

        // Save to localStorage for persistence
        const savedNegativeRules = Array.from(this.negativeMappingRules);
        localStorage.setItem('negative-mapping-rules', JSON.stringify(savedNegativeRules));

        // Remove the group card from display
        const groupCard = buttonElement.closest('.vulnerability-group-card');
        if (groupCard) {
            groupCard.style.opacity = '0.5';
            groupCard.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                groupCard.remove();
            }, 300);
        }

        // Update counts
        const remainingGroups = document.querySelectorAll('.vulnerability-group-card');
        const visibleCountSpan = document.getElementById('bulk-visible-count');
        if (visibleCountSpan) {
            visibleCountSpan.textContent = `${remainingGroups.length - 1} visible`;
        }

        // Update header count
        const headerElement = document.querySelector('.bulk-controls-header h3');
        if (headerElement) {
            headerElement.textContent = `Review ${remainingGroups.length - 1} vulnerability rule groups with 1:1 matches`;
        }

        // Update bulk stats
        this.updateBulkStats();

        // Show confirmation notification
        const notification = document.createElement('div');
        notification.innerHTML = `🚫 Marked "${sastRule}" ≠ "${benchmarkType}" as never matching<br>This combination will be filtered from future bulk mappings.`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);

        console.log(`🚫 Bulk negative mapping created: ${sastRule} != ${benchmarkType}`);
    }

    async bulkMatchAll(ruleId, sastRule, benchmarkType, buttonElement) {
        if (!ruleId || !sastRule || !benchmarkType) {
            console.error('Missing parameters for bulk match all');
            return;
        }

        // Find the group card and get all matches for this rule
        const groupCard = buttonElement.closest('.vulnerability-group-card');
        if (!groupCard) {
            console.error('Could not find group card for bulk match');
            return;
        }

        try {
            this.showLoadingOverlay('Applying bulk matches...');

            // Find all files with this rule ID from the current bulk data
            const matchesToApply = [];
            if (this.oneToOneFiles) {
                for (const fileGroup of this.oneToOneFiles) {
                    const firstSastVuln = fileGroup.sast_vulns[0];
                    const firstBenchmarkVuln = fileGroup.benchmark_vulns[0];

                    if ((firstSastVuln.rule_id === sastRule || firstSastVuln.vuln_type === sastRule)) {
                        matchesToApply.push({
                            sastVuln: firstSastVuln,
                            benchmarkVuln: firstBenchmarkVuln,
                            file_path: fileGroup.file_path
                        });
                    }
                }
            }

            console.log(`🔄 Applying bulk match for ${matchesToApply.length} instances of rule: ${sastRule}`);

            let successCount = 0;
            const errors = [];

            // Apply each mapping
            for (const match of matchesToApply) {
                try {
                    const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mapping`, {
                        method: 'POST',
                        body: JSON.stringify({
                            action: 'confirm',
                            benchmark_id: match.benchmarkVuln.id || `bench_${this.generateId(match.benchmarkVuln)}`,
                            sast_id: match.sastVuln.id || `sast_${this.generateId(match.sastVuln)}`,
                            bulk_applied: true
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        this.mappedSastFindings.add(match.sastVuln.id);
                        successCount++;

                        // Handle auto-mapped results
                        if (result.auto_mapped) {
                            result.auto_mapped.forEach(autoMapping => {
                                this.mappedSastFindings.add(autoMapping.sast_id);
                            });
                        }
                    } else {
                        const errorText = await response.text();
                        errors.push(`${match.file_path}: ${errorText}`);
                    }
                } catch (error) {
                    errors.push(`${match.file_path}: ${error.message}`);
                }
            }

            this.hideLoadingOverlay();

            // Remove the group card from display with animation
            groupCard.style.opacity = '0.5';
            groupCard.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                groupCard.remove();

                // Update counts after removal
                const remainingGroups = document.querySelectorAll('.vulnerability-group-card');
                const visibleCountSpan = document.getElementById('bulk-visible-count');
                if (visibleCountSpan) {
                    visibleCountSpan.textContent = `${remainingGroups.length} visible`;
                }

                // Update header count
                const headerElement = document.querySelector('.bulk-controls-header h3');
                if (headerElement) {
                    headerElement.textContent = `Review ${remainingGroups.length} vulnerability rule groups with 1:1 matches`;
                }
            }, 300);

            // Update bulk stats
            this.updateBulkStats();

            // Show result notification
            const notification = document.createElement('div');
            if (errors.length === 0) {
                notification.innerHTML = `✅ Successfully matched all ${successCount} instances of "${sastRule}"<br>Rule learned for future automatic application.`;
                notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
            } else {
                notification.innerHTML = `⚠️ Applied ${successCount}/${matchesToApply.length} matches for "${sastRule}"<br>Some mappings failed. Check console for details.`;
                notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
                console.warn('Bulk match errors:', errors);
            }

            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 5000);

            console.log(`✅ Bulk match completed: ${successCount}/${matchesToApply.length} successful for rule ${sastRule}`);

        } catch (error) {
            this.hideLoadingOverlay();
            console.error('Bulk match error:', error);

            const notification = document.createElement('div');
            notification.innerHTML = `❌ Failed to apply bulk matches: ${error.message}`;
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 5000);
        }
    }

    filterBulkGroups(searchTerm) {
        const searchLower = searchTerm.toLowerCase().trim();
        const groups = document.querySelectorAll('.vulnerability-group-card');
        let visibleCount = 0;

        groups.forEach(group => {
            const ruleId = group.querySelector('.full-rule-id')?.textContent || '';
            const shortRuleId = group.querySelector('.group-title h4')?.textContent || '';
            const sastType = group.querySelector('.sast-description .desc-type')?.textContent || '';
            const sastDesc = group.querySelector('.sast-description .desc-text')?.textContent || '';
            const benchType = group.querySelector('.benchmark-description .desc-type')?.textContent || '';
            const benchDesc = group.querySelector('.benchmark-description .desc-text')?.textContent || '';

            // Search across all relevant fields
            const searchableContent = [
                ruleId,
                shortRuleId,
                sastType,
                sastDesc,
                benchType,
                benchDesc
            ].join(' ').toLowerCase();

            const shouldShow = searchTerm === '' || searchableContent.includes(searchLower);

            if (shouldShow) {
                group.style.display = 'block';
                visibleCount++;

                // Highlight matching text if there's a search term
                if (searchTerm !== '') {
                    this.highlightSearchTerm(group, searchTerm);
                } else {
                    this.removeSearchHighlights(group);
                }
            } else {
                group.style.display = 'none';
            }
        });

        // Update visible count
        const visibleCountSpan = document.getElementById('bulk-visible-count');
        if (visibleCountSpan) {
            visibleCountSpan.textContent = `${visibleCount} visible`;
        }

        // Update selection stats after filtering
        this.updateBulkStats();

        console.log(`🔍 Filtered bulk groups: ${visibleCount}/${groups.length} visible for search: "${searchTerm}"`);
    }

    highlightSearchTerm(element, searchTerm) {
        // Remove existing highlights
        this.removeSearchHighlights(element);

        if (!searchTerm) return;

        const searchLower = searchTerm.toLowerCase();
        const textElements = element.querySelectorAll('.desc-type, .desc-text, .group-title h4, .full-rule-id');

        textElements.forEach(textEl => {
            const originalText = textEl.textContent;
            if (originalText.toLowerCase().includes(searchLower)) {
                const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                const highlightedText = originalText.replace(regex, '<mark>$1</mark>');
                textEl.innerHTML = highlightedText;
            }
        });
    }

    removeSearchHighlights(element) {
        const highlights = element.querySelectorAll('mark');
        highlights.forEach(mark => {
            mark.replaceWith(mark.textContent);
        });
    }

    selectAllVisibleGroups() {
        // Find all visible vulnerability group cards
        const visibleGroups = document.querySelectorAll('.vulnerability-group-card:not([style*="display: none"])');
        let selectedCount = 0;
        let totalVisible = visibleGroups.length;

        visibleGroups.forEach(group => {
            // Select the group checkbox
            const groupCheckbox = group.querySelector('.group-checkbox');
            if (groupCheckbox) {
                const wasChecked = groupCheckbox.checked;
                groupCheckbox.checked = true;

                if (!wasChecked) {
                    selectedCount++;

                    // Trigger the same logic as the existing group checkbox event
                    const ruleId = groupCheckbox.getAttribute('data-rule-id');
                    document.querySelectorAll(`.file-checkbox input[data-rule-id="${ruleId}"]`).forEach(matchCb => {
                        if (matchCb) matchCb.checked = true;
                    });
                }
            }
        });

        // Update stats
        this.updateBulkStats();

        console.log(`✅ Selected ${selectedCount} out of ${totalVisible} visible groups`);

        // Show feedback
        const notification = document.createElement('div');
        if (selectedCount > 0) {
            notification.innerHTML = `✅ Selected ${selectedCount} visible groups`;
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 10px; border-radius: 5px; z-index: 1000; max-width: 300px;';
        } else {
            notification.innerHTML = `ℹ️ All ${totalVisible} visible groups were already selected`;
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 10px; border-radius: 5px; z-index: 1000; max-width: 300px;';
        }
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 2000);
    }

    updateBulkStats() {
        const checkboxes = document.querySelectorAll('.file-checkbox input[type="checkbox"]');
        const selectedCount = Array.from(checkboxes).filter(cb => cb && cb.checked).length;
        const highConfidenceCount = this.bulkMatches ? this.bulkMatches.filter(m => m.confidence >= 75).length : 0;

        const selectedEl = document.getElementById('bulk-selected-count');
        const highConfEl = document.getElementById('bulk-high-confidence-count');
        const approveBtn = document.getElementById('bulk-approve');

        if (selectedEl) selectedEl.textContent = `${selectedCount} selected`;
        if (highConfEl) highConfEl.textContent = `${highConfidenceCount} high confidence`;
        if (approveBtn) {
            approveBtn.disabled = selectedCount === 0;
            approveBtn.textContent = selectedCount === 0 ? `Apply Selected & Remove` : `Apply ${selectedCount} Selected & Remove`;
        }

        // Update group checkbox states based on their individual file selections
        if (this.bulkGroups) {
            this.bulkGroups.forEach(group => {
                const groupCheckbox = document.querySelector(`.group-checkbox[data-rule-id="${group.ruleId}"]`);
                const groupFileCheckboxes = document.querySelectorAll(`.file-checkbox input[data-rule-id="${group.ruleId}"]`);

                if (groupCheckbox && groupFileCheckboxes.length > 0) {
                    const allChecked = Array.from(groupFileCheckboxes).every(cb => cb && cb.checked);
                    const someChecked = Array.from(groupFileCheckboxes).some(cb => cb && cb.checked);

                    groupCheckbox.checked = allChecked;
                    groupCheckbox.indeterminate = someChecked && !allChecked;
                }
            });
        }
    }

    async processBulkMappings() {
        // Get selected groups (not individual files)
        const selectedGroupRuleIds = [];
        const groupCheckboxes = document.querySelectorAll('.group-checkbox:checked');

        groupCheckboxes.forEach(checkbox => {
            const ruleId = checkbox.getAttribute('data-rule-id');
            if (ruleId) {
                selectedGroupRuleIds.push(ruleId);
            }
        });

        // Also check individual file checkboxes for any manually selected files
        const fileCheckboxes = document.querySelectorAll('.file-checkbox input[type="checkbox"]:checked');
        const selectedMatches = [];

        // Collect matches from selected groups
        selectedGroupRuleIds.forEach(ruleId => {
            const group = this.bulkGroups[ruleId];
            if (group && group.matches) {
                selectedMatches.push(...group.matches);
            }
        });

        // Add individually selected files
        fileCheckboxes.forEach((checkbox) => {
            const index = parseInt(checkbox.getAttribute('data-index'));
            if (!isNaN(index) && this.bulkMatches[index]) {
                const match = this.bulkMatches[index];
                // Only add if not already included from group selection
                if (!selectedMatches.some(m => m.index === match.index)) {
                    selectedMatches.push(match);
                }
            }
        });

        if (selectedMatches.length === 0) return;

        this.showLoadingOverlay(`Applying ${selectedMatches.length} bulk mappings...`);

        let successCount = 0;
        const appliedRuleIds = new Set();
        const appliedMatchIndices = new Set();

        for (const match of selectedMatches) {
            try {
                const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mapping`, {
                    method: 'POST',
                    body: JSON.stringify({
                        action: 'confirm',
                        benchmark_id: match.benchmarkVuln.id || `bench_${this.generateId(match.benchmarkVuln)}`,
                        sast_id: match.sastVuln.id || `sast_${this.generateId(match.sastVuln)}`
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    this.mappedSastFindings.add(match.sastVuln.id);

                    // Handle auto-mapped results
                    if (result.auto_mapped) {
                        result.auto_mapped.forEach(autoMapping => {
                            this.mappedSastFindings.add(autoMapping.sast_id);
                        });
                    }

                    appliedRuleIds.add(match.ruleId);
                    appliedMatchIndices.add(match.index);
                    successCount++;
                } else {
                    const errorText = await response.text();
                    console.error('Failed to apply mapping:', match.file_path, errorText);
                }
            } catch (error) {
                console.error('Error processing bulk mapping:', error);
            }
        }

        this.hideLoadingOverlay();

        // Remove successfully applied groups from display
        this.removeAppliedBulkGroups(appliedRuleIds);

        // Show results but stay on bulk mapping page
        const notification = document.createElement('div');
        notification.innerHTML = `✅ Applied ${successCount}/${selectedMatches.length} bulk mappings!<br>📋 Removed applied groups from the list.`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);

        // Update counts and stats
        this.updateBulkStats();

        // Check if there are any groups left
        const remainingGroups = document.querySelectorAll('.vulnerability-group-card:not([style*="display: none"])');
        if (remainingGroups.length === 0) {
            // All groups processed, offer to proceed
            const proceedNotification = document.createElement('div');
            proceedNotification.innerHTML = `🎉 All vulnerability groups processed!<br><button onclick="window.ui.proceedToDetailedMapping()" class="btn btn-primary" style="margin-top: 0.5rem;">Proceed to Detailed Mapping</button>`;
            proceedNotification.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #cce5ff; border: 1px solid #b3d9ff; color: #004085; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
            document.body.appendChild(proceedNotification);
            setTimeout(() => proceedNotification.remove(), 8000);
        }

        console.log(`✅ Applied ${successCount} bulk mappings, removed ${appliedRuleIds.size} groups from display`);
    }

    removeAppliedBulkGroups(appliedRuleIds) {
        appliedRuleIds.forEach(ruleId => {
            const groupCard = document.querySelector(`[data-rule-id="${ruleId}"]`);
            if (groupCard) {
                groupCard.remove();
                console.log(`🗑️  Removed group: ${ruleId}`);
            }
        });

        // Update visible count
        const remainingGroups = document.querySelectorAll('.vulnerability-group-card');
        const visibleCountSpan = document.getElementById('bulk-visible-count');
        if (visibleCountSpan) {
            visibleCountSpan.textContent = `${remainingGroups.length} visible`;
        }

        // Update header count
        const headerElement = document.querySelector('.bulk-controls-header h3');
        if (headerElement) {
            headerElement.textContent = `Review ${remainingGroups.length} vulnerability rule groups with 1:1 matches`;
        }
    }

    proceedToDetailedMapping() {
        console.log('🔄 Proceeding to detailed mapping...');
        console.log('📊 Current session:', this.currentSession);
        console.log('📊 Files available:', this.allFiles?.length || 0);
        console.log('📊 SAST findings available:', this.allSastFindings?.length || 0);

        // Validate session before proceeding
        if (!this.currentSession) {
            console.error('❌ No current session available for detailed mapping');

            // Try to restore session from sessionManager
            const storedSessionId = sessionManager?.getSessionId();
            if (storedSessionId) {
                console.log('🔄 Restoring session from sessionManager:', storedSessionId);
                this.currentSession = storedSessionId;
            } else {
                alert('Session lost. Please refresh the page and upload your files again.');
                return;
            }
        }

        // Mark bulk mapping as completed
        localStorage.setItem('bulk-mapping-completed-' + this.currentSession, 'true');

        // Switch to detailed mapping interface
        this.showDetailedMappingInterface(this.allFiles, this.allSastFindings);
    }

    skipBulkMapping() {
        // Mark as completed to skip this phase in future
        localStorage.setItem('bulk-mapping-completed-' + this.currentSession, 'true');

        // Switch to detailed mapping
        this.showDetailedMappingInterface(this.allFiles, this.allSastFindings);
    }

    async applyLearnedRules() {
        // Auto-apply learned mapping rules to other similar vulnerabilities
        console.log('🧠 Applying learned mapping rules...');

        // This will be triggered after each accept to automatically map similar findings
        // The backend will return new auto-suggestions based on the learned patterns
        // Suggestions API removed - auto-mapping now happens server-side only
    }

    // Old renderVulnerabilities function removed - replaced with SAST-first approach

    renderVulnerabilityItem(vuln, type) {
        // Handle missing vulnerability data gracefully
        if (!vuln) {
            return '<div class="vulnerability-item error">Invalid vulnerability data</div>';
        }

        const severityClass = (vuln.severity || 'UNKNOWN').toUpperCase();
        const typeAttr = type === 'benchmark' ? 'data-benchmark-id' : 'data-sast-id';
        const vulnId = vuln.id || 'unknown';
        const vulnType = vuln.vuln_type || 'UNKNOWN';
        const filePath = vuln.file_path || 'Unknown file';
        const lineNumber = vuln.line_number || 'N/A';
        const description = vuln.description || '';

        return `
            <div class="vulnerability-item" ${typeAttr}="${this.escapeHtml(vulnId)}">
                <div class="vulnerability-details">
                    <div class="vulnerability-main">
                        <div class="vulnerability-header">
                            <span class="vulnerability-type">${this.escapeHtml(vulnType)}</span>
                        </div>
                        <div class="vulnerability-file" title="${this.escapeHtml(filePath)}">
                            📁 ${this.escapeHtml(this.truncateFilePath(filePath))}
                        </div>
                        <div class="vulnerability-line-info">
                            <span class="line-number">Line ${lineNumber}</span>
                        </div>
                    </div>
                    <div class="vulnerability-meta">
                        <span class="vulnerability-severity ${severityClass}">${severityClass}</span>
                    </div>
                </div>
                ${description ? `<div class="vulnerability-description">${this.escapeHtml(description)}</div>` : ''}
            </div>
        `;
    }

    truncateFilePath(path, maxLength = 40) {
        if (!path || typeof path !== 'string') {
            return 'Unknown file';
        }

        if (path.length <= maxLength) return path;

        const parts = path.split('/');
        if (parts.length > 2) {
            return `.../${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
        }

        return path.substring(path.length - maxLength);
    }

    // Old attachVulnerabilityListeners function removed - using onclick handlers now

    onConfidenceChange(event) {
        const confidence = event.target.value;
        document.getElementById('confidence-value').textContent = confidence;
        // Suggestions panel removed - confidence only affects filtering now
    }

    onAutoMappingToggle(event) {
        const isEnabled = event.target.checked;
        const threshold = document.getElementById('auto-mapping-threshold').value;
        console.log(`Auto-mapping ${isEnabled ? 'enabled' : 'disabled'} with threshold ${threshold}%`);

        if (isEnabled && this.currentSession) {
            // Check if there are any high-confidence matches to auto-accept
            this.processAutoMappingForCurrentMatches();
        }
    }

    onThresholdChange(event) {
        const threshold = event.target.value;
        const isEnabled = document.getElementById('auto-mapping-enabled').checked;
        console.log(`Auto-mapping threshold changed to ${threshold}%`);

        if (isEnabled && this.currentSession) {
            // Reprocess matches with new threshold
            this.processAutoMappingForCurrentMatches();
        }
    }

    async processAutoMappingForCurrentMatches() {
        const isEnabled = document.getElementById('auto-mapping-enabled').checked;
        const threshold = parseInt(document.getElementById('auto-mapping-threshold').value);

        if (!isEnabled || !this.currentSession) {
            return;
        }

        // Find all visible accept buttons with high confidence matches
        const acceptButtons = document.querySelectorAll('.btn-accept:not([disabled])');
        let autoAcceptedCount = 0;

        for (const button of acceptButtons) {
            const matchContainer = button.closest('.match-item');
            if (!matchContainer) continue;

            // Look for confidence badge in the match
            const confidenceBadge = matchContainer.querySelector('.confidence-badge');
            if (!confidenceBadge) continue;

            // Extract confidence percentage from badge text
            const confidenceText = confidenceBadge.textContent;
            const confidenceMatch = confidenceText.match(/(\d+)%/);
            if (!confidenceMatch) continue;

            const confidence = parseInt(confidenceMatch[1]);

            // Auto-accept if confidence meets threshold
            if (confidence >= threshold) {
                console.log(`🤖 Auto-accepting match with ${confidence}% confidence (threshold: ${threshold}%)`);
                button.click(); // Trigger the existing accept logic
                autoAcceptedCount++;

                // Small delay to avoid overwhelming the server
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }

        if (autoAcceptedCount > 0) {
            console.log(`🎯 Auto-accepted ${autoAcceptedCount} matches above ${threshold}% confidence`);
        }
    }

    // Suggestions panel methods removed - using two-phase workflow instead

    getConfidenceClass(confidence) {
        if (confidence >= 80) return 'high';
        if (confidence >= 60) return 'medium';
        return 'low';
    }

    getMatchIcon(confidence) {
        if (confidence >= 90) return '🎯';
        if (confidence >= 80) return '✅';
        if (confidence >= 60) return '⚡';
        return '❓';
    }

    // acceptSuggestion and rejectSuggestion removed - using two-phase workflow instead

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

    async handleExportMappings() {
        try {
            console.log('🔍 Export mappings starting, currentSession:', this.currentSession);
            console.log('🔍 SessionManager sessionId:', sessionManager?.getSessionId());

            if (!this.currentSession) {
                // Try to get from sessionManager
                const storedSession = sessionManager?.getSessionId();
                if (storedSession) {
                    this.currentSession = storedSession;
                    console.log('🔄 Retrieved session from sessionManager:', storedSession);
                } else {
                    alert('No active session to export mappings from');
                    return;
                }
            }

            this.showLoadingOverlay('Exporting learned mappings...');

            // Get current mappings from the session using secure API request
            const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mappings`, {
                method: 'GET'
            });

            console.log('🔍 Mappings response status:', response.status, response.statusText);
            console.log('🔍 Session ID being used:', this.currentSession);

            if (!response.ok) {
                let errorDetails;
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.error || 'Unknown error';
                    console.log('🔍 Server error response:', errorData);
                } catch (e) {
                    errorDetails = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(`Failed to fetch current mappings: ${errorDetails}`);
            }

            const mappingsData = await response.json();

            // Create a simplified mapping rules file
            const mappingRules = {};

            // Extract SAST rule ID to benchmark vulnerability type mappings
            if (mappingsData.mappings) {
                mappingsData.mappings.forEach(mapping => {
                    if (mapping.sast && mapping.benchmark) {
                        const sastRuleId = mapping.sast.rule_id || mapping.sast.vuln_type;
                        const benchmarkType = mapping.benchmark.vuln_type;
                        const benchmarkDescription = mapping.benchmark.description;

                        if (sastRuleId && benchmarkType) {
                            mappingRules[sastRuleId] = {
                                benchmark_type: benchmarkType,
                                benchmark_description: benchmarkDescription,
                                confidence: 95, // High confidence for learned mappings
                                source: 'manual_mapping',
                                created_at: new Date().toISOString()
                            };
                        }
                    }
                });
            }

            const exportData = {
                version: '1.0',
                created_at: new Date().toISOString(),
                total_rules: Object.keys(mappingRules).length,
                total_negative_rules: this.negativeMappingRules.size,
                mapping_rules: mappingRules,
                negative_mapping_rules: Array.from(this.negativeMappingRules),
                metadata: {
                    session_id: this.currentSession,
                    exported_by: 'SAST Vulnerability Mapping Tool'
                }
            };

            // Download the file
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `sast-mapping-rules-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            // Update export button to show it's enabled
            const exportBtn = document.getElementById('export-mappings-btn');
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.textContent = `📤 Export ${Object.keys(mappingRules).length} Rules`;
            }

            alert(`Exported ${Object.keys(mappingRules).length} mapping rules successfully!`);
        } catch (error) {
            alert(`Export mappings failed: ${error.message}`);
            console.error('Export mappings error:', error);
        } finally {
            this.hideLoadingOverlay();
        }
    }

    handleImportMappings() {
        // Trigger file input dialog
        document.getElementById('import-mappings-file').click();
    }

    async onMappingsFileSelected(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            this.showLoadingOverlay('Loading mapping rules...');

            // Security: Validate file size (max 10MB)
            if (file.size > 10 * 1024 * 1024) {
                throw new Error('Mapping file too large (max 10MB)');
            }

            // Security: Validate file type
            if (!file.name.endsWith('.json')) {
                throw new Error('Only JSON files are allowed');
            }

            const text = await file.text();

            // Security: Use safe JSON parsing with validation
            const mappingData = SecurityUtils.safeJsonParse(text, MAPPING_RULES_SCHEMA);

            // Additional validation for mapping rules structure
            if (!mappingData.mapping_rules || typeof mappingData.mapping_rules !== 'object') {
                throw new Error('Invalid mapping file: mapping_rules must be an object');
            }

            // Validate individual mapping rules
            const validatedRules = {};
            let ruleCount = 0;

            for (const [ruleId, ruleData] of Object.entries(mappingData.mapping_rules)) {
                if (ruleCount >= 1000) {
                    console.warn('Truncating mapping rules at 1000 entries for security');
                    break;
                }

                // Validate rule structure
                if (typeof ruleData !== 'object' || ruleData === null) {
                    console.warn(`Skipping invalid rule: ${ruleId}`);
                    continue;
                }

                // Sanitize rule ID and data
                const sanitizedRuleId = SecurityUtils.escapeHtml(String(ruleId)).substring(0, 200);
                validatedRules[sanitizedRuleId] = SecurityUtils.sanitizeObject(ruleData);
                ruleCount++;
            }

            // Store the validated mapping rules
            this.loadedMappingRules = validatedRules;

            // Securely store in localStorage
            try {
                const serialized = JSON.stringify(this.loadedMappingRules);
                if (serialized.length > 5 * 1024 * 1024) { // 5MB limit for localStorage
                    throw new Error('Mapping rules too large for storage');
                }
                localStorage.setItem('imported-mapping-rules', serialized);
            } catch (e) {
                console.warn('Could not store mapping rules in localStorage:', e.message);
                // Continue without localStorage - rules still work for this session
            }

            // Load and validate negative mapping rules if present
            let negativeCount = 0;
            if (mappingData.negative_mapping_rules && Array.isArray(mappingData.negative_mapping_rules)) {
                const validatedNegativeRules = [];

                for (const negativeRule of mappingData.negative_mapping_rules) {
                    if (negativeCount >= 1000) {
                        console.warn('Truncating negative mapping rules at 1000 entries for security');
                        break;
                    }

                    if (typeof negativeRule === 'string') {
                        const sanitized = SecurityUtils.escapeHtml(negativeRule).substring(0, 500);
                        validatedNegativeRules.push(sanitized);
                        negativeCount++;
                    }
                }

                this.negativeMappingRules = new Set(validatedNegativeRules);

                try {
                    localStorage.setItem('negative-mapping-rules', JSON.stringify(validatedNegativeRules));
                } catch (e) {
                    console.warn('Could not store negative mapping rules in localStorage:', e.message);
                }

                console.log(`🚫 Loaded ${negativeCount} negative mapping rules`);
            } else {
                negativeCount = this.negativeMappingRules.size;
            }

            // Show secure confirmation notification
            const notification = document.createElement('div');
            const safeFileName = SecurityUtils.sanitizeFilename(file.name);
            notification.textContent = `📥 Loaded ${ruleCount} positive & ${negativeCount} negative mapping rules from ${safeFileName}. Positive rules auto-apply, negative rules filter out bad matches.`;
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px; word-break: break-word;';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 5000);

            // Update import button text (securely)
            const importBtn = document.getElementById('import-mappings-btn');
            if (importBtn) {
                // Security: Use textContent instead of innerHTML to prevent XSS
                importBtn.textContent = `📥 ${Math.min(ruleCount, 999)} Rules Loaded`;
                importBtn.classList.remove('btn-info');
                importBtn.classList.add('btn-success');
            }

            // If we have an active session, apply the rules immediately
            if (this.currentSession && this.sastFindings) {
                await this.applyLoadedMappingRules();
            }

            console.log(`✅ Loaded ${ruleCount} mapping rules from ${file.name}`);
        } catch (error) {
            alert(`Failed to import mappings: ${error.message}`);
            console.error('Import mappings error:', error);
        } finally {
            this.hideLoadingOverlay();
            // Clear the file input
            event.target.value = '';
        }
    }

    async applyLoadedMappingRules() {
        if (!this.loadedMappingRules || !this.sastFindings) {
            return;
        }

        let appliedCount = 0;
        const appliedRules = [];

        for (const finding of this.sastFindings) {
            const ruleId = finding.rule_id || finding.vuln_type;
            if (ruleId && this.loadedMappingRules[ruleId]) {
                const mappingRule = this.loadedMappingRules[ruleId];

                // Check if this finding is already mapped
                const findingId = finding.id || `sast_${this.generateId(finding)}`;
                if (!this.mappedSastFindings.has(findingId)) {
                    try {
                        // Apply the mapping automatically
                        const response = await this.secureApiRequest(`/api/session/${this.currentSession}/mapping`, {
                            method: 'POST',
                            body: JSON.stringify({
                                action: 'confirm',
                                sast_id: findingId,
                                benchmark_id: `auto_${this.generateId(mappingRule)}`,
                                auto_applied: true,
                                mapping_rule: mappingRule
                            })
                        });

                        if (response.ok) {
                            this.mappedSastFindings.add(findingId);
                            appliedCount++;
                            appliedRules.push(ruleId);
                        }
                    } catch (error) {
                        console.error('Error auto-applying mapping rule:', error);
                    }
                }
            }
        }

        if (appliedCount > 0) {
            // Refresh the UI to show newly mapped items
            this.renderSastFindings(this.sastFindings);
            this.updateSessionSummary(Object.values(this.fileData || {}), this.sastFindings);

            // Show notification
            const notification = document.createElement('div');
            notification.innerHTML = `🎯 Auto-applied ${appliedCount} mappings using loaded rules!<br>Rules used: ${appliedRules.slice(0, 3).join(', ')}${appliedRules.length > 3 ? '...' : ''}`;
            notification.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 6000);

            console.log(`🎯 Auto-applied ${appliedCount} mappings using loaded rules`);
        }
    }

    saveNegativeMapping(sastFinding, benchmarkVuln) {
        // Create a negative mapping rule: SAST rule X should NOT map to benchmark type Y
        const sastRuleId = sastFinding.rule_id || sastFinding.vuln_type || 'unknown';
        const benchmarkType = benchmarkVuln.vuln_type || 'unknown';

        const negativeRule = `${sastRuleId}!==${benchmarkType}`;
        this.negativeMappingRules.add(negativeRule);

        // Save to localStorage for persistence
        const savedNegativeRules = Array.from(this.negativeMappingRules);
        localStorage.setItem('negative-mapping-rules', JSON.stringify(savedNegativeRules));

        console.log(`🚫 Saved negative mapping: ${sastRuleId} != ${benchmarkType}`);
    }

    markAsNeverMatch(findingIndex) {
        const sastFinding = this.sastFindings[findingIndex];
        if (!sastFinding) {
            console.error('SAST finding not found for index:', findingIndex);
            return;
        }

        // For "Never Match", we create a general negative rule against all possible benchmark types
        // We'll use a special marker to indicate this SAST type should never be suggested
        const sastRuleId = sastFinding.rule_id || sastFinding.vuln_type || 'unknown';
        const neverMatchRule = `${sastRuleId}!==*`;
        this.negativeMappingRules.add(neverMatchRule);

        // Save to localStorage for persistence
        const savedNegativeRules = Array.from(this.negativeMappingRules);
        localStorage.setItem('negative-mapping-rules', JSON.stringify(savedNegativeRules));

        // Mark this finding as handled (mapped) so it doesn't show up in unmapped filter
        const findingId = sastFinding.id || `sast_${findingIndex}_${this.generateId(sastFinding)}`;
        this.mappedSastFindings.add(findingId);

        console.log(`🚫 DEBUG: Added findingId "${findingId}" to mappedSastFindings. Total mapped: ${this.mappedSastFindings.size}`);

        // Refresh UI to hide this finding
        this.renderSastFindings(this.sastFindings);
        this.updateSessionSummary(Object.values(this.fileData || {}), this.sastFindings);

        // Show confirmation
        const notification = document.createElement('div');
        notification.innerHTML = `🚫 Marked "${sastRuleId}" as "Never Match"<br>This will be filtered from future bulk mappings.`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);

        console.log(`🚫 Marked as never match: ${sastRuleId}`);
    }

    analyzeCorrelations() {
        if (!this.fileData || Object.keys(this.fileData).length === 0) {
            alert('No data loaded for correlation analysis');
            return;
        }

        this.showLoadingOverlay('Analyzing rule correlations...');

        try {
            // Build correlation matrix
            const correlations = this.calculateRuleCorrelations();

            // Show results in a modal or new interface
            this.displayCorrelationResults(correlations);

        } catch (error) {
            console.error('Correlation analysis error:', error);
            alert(`Correlation analysis failed: ${error.message}`);
        } finally {
            this.hideLoadingOverlay();
        }
    }

    calculateRuleCorrelations() {
        const files = Object.values(this.fileData);
        const cooccurrenceMatrix = new Map();
        const sastRuleCounts = new Map();
        const benchmarkRuleCounts = new Map();

        // Count occurrences and co-occurrences
        files.forEach(file => {
            const sastRules = new Set();
            const benchmarkRules = new Set();

            // Collect unique SAST rules in this file
            if (file.sast_vulns) {
                file.sast_vulns.forEach(sast => {
                    const ruleId = sast.rule_id || sast.vuln_type || 'unknown';
                    sastRules.add(ruleId);
                    sastRuleCounts.set(ruleId, (sastRuleCounts.get(ruleId) || 0) + 1);
                });
            }

            // Collect unique benchmark rules in this file
            if (file.benchmark_vulns) {
                file.benchmark_vulns.forEach(bench => {
                    const ruleId = bench.vuln_type || 'unknown';
                    benchmarkRules.add(ruleId);
                    benchmarkRuleCounts.set(ruleId, (benchmarkRuleCounts.get(ruleId) || 0) + 1);
                });
            }

            // Calculate co-occurrences for all pairs in this file
            sastRules.forEach(sastRule => {
                benchmarkRules.forEach(benchRule => {
                    const key = `${sastRule}|||${benchRule}`;
                    cooccurrenceMatrix.set(key, (cooccurrenceMatrix.get(key) || 0) + 1);
                });
            });
        });

        // Calculate correlation scores
        const correlations = [];
        cooccurrenceMatrix.forEach((cooccurCount, key) => {
            const [sastRule, benchRule] = key.split('|||');
            const sastCount = sastRuleCounts.get(sastRule) || 0;
            const benchCount = benchmarkRuleCounts.get(benchRule) || 0;

            // Correlation score = co-occurrence / max(sast_count, bench_count)
            // This gives us the percentage of overlap
            const correlationScore = cooccurCount / Math.max(sastCount, benchCount);

            // Only include correlations above a threshold and with sufficient data
            if (correlationScore >= 0.5 && cooccurCount >= 2) {
                correlations.push({
                    sastRule,
                    benchRule,
                    cooccurCount,
                    sastCount,
                    benchCount,
                    correlationScore,
                    confidence: Math.round(correlationScore * 100)
                });
            }
        });

        // Sort by correlation score descending
        correlations.sort((a, b) => b.correlationScore - a.correlationScore);

        console.log(`📊 Found ${correlations.length} rule correlations`, correlations);
        return correlations;
    }

    displayCorrelationResults(correlations) {
        // Create a modal to display correlation results
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';

        modal.innerHTML = `
            <div class="modal-content" style="max-width: 90%; max-height: 90%;">
                <div class="modal-header">
                    <h3>📊 Rule Correlation Analysis</h3>
                    <button id="close-correlation-modal" class="btn btn-secondary">✕</button>
                </div>
                <div style="padding: 1rem; overflow-y: auto;">
                    <p>Found <strong>${correlations.length}</strong> statistically significant correlations where SAST rules frequently appear with specific benchmark vulnerabilities:</p>

                    ${correlations.length === 0 ? '<p>No significant correlations found. Try analyzing more data.</p>' : `
                        <div class="correlation-controls" style="margin-bottom: 1rem;">
                            <button id="apply-high-confidence-correlations" class="btn btn-success">
                                ✅ Auto-Apply High Confidence (80%+) Mappings
                            </button>
                            <button id="export-correlations" class="btn btn-info">
                                📤 Export as Mapping Rules
                            </button>
                        </div>

                        <table class="correlation-table" style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                                    <th style="padding: 0.75rem; text-align: left;">SAST Rule</th>
                                    <th style="padding: 0.75rem; text-align: left;">Benchmark Type</th>
                                    <th style="padding: 0.75rem; text-align: center;">Co-occur</th>
                                    <th style="padding: 0.75rem; text-align: center;">Confidence</th>
                                    <th style="padding: 0.75rem; text-align: center;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${correlations.map((corr, idx) => `
                                    <tr style="border-bottom: 1px solid #dee2e6;">
                                        <td style="padding: 0.75rem; font-family: monospace; font-size: 0.85rem;">${corr.sastRule}</td>
                                        <td style="padding: 0.75rem; font-weight: 500;">${corr.benchRule}</td>
                                        <td style="padding: 0.75rem; text-align: center;">${corr.cooccurCount}/${Math.max(corr.sastCount, corr.benchCount)}</td>
                                        <td style="padding: 0.75rem; text-align: center;">
                                            <span class="confidence-badge ${corr.confidence >= 80 ? 'confidence-high' : corr.confidence >= 60 ? 'confidence-medium' : 'confidence-low'}">
                                                ${corr.confidence}%
                                            </span>
                                        </td>
                                        <td style="padding: 0.75rem; text-align: center;">
                                            <button class="btn btn-sm btn-success apply-correlation-btn" data-index="${idx}">Apply</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Event listeners for the modal
        document.getElementById('close-correlation-modal').addEventListener('click', () => {
            modal.remove();
        });

        if (correlations.length > 0) {
            // Apply individual correlations
            document.querySelectorAll('.apply-correlation-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const index = parseInt(e.target.getAttribute('data-index'));
                    this.applyCorrelationAsMapping(correlations[index]);
                    e.target.textContent = 'Applied';
                    e.target.disabled = true;
                });
            });

            // Apply high confidence correlations
            document.getElementById('apply-high-confidence-correlations').addEventListener('click', () => {
                const highConfCorrelations = correlations.filter(c => c.confidence >= 80);
                this.applyMultipleCorrelations(highConfCorrelations);
                modal.remove();
            });

            // Export correlations as mapping rules
            document.getElementById('export-correlations').addEventListener('click', () => {
                this.exportCorrelationsAsMappings(correlations);
            });
        }
    }

    applyCorrelationAsMapping(correlation) {
        // Convert correlation to a mapping rule
        if (!this.loadedMappingRules) {
            this.loadedMappingRules = {};
        }

        this.loadedMappingRules[correlation.sastRule] = {
            benchmark_type: correlation.benchRule,
            benchmark_description: `Auto-discovered via correlation analysis (${correlation.confidence}% confidence)`,
            confidence: correlation.confidence,
            source: 'correlation_analysis',
            created_at: new Date().toISOString(),
            correlation_data: {
                cooccur_count: correlation.cooccurCount,
                sast_count: correlation.sastCount,
                bench_count: correlation.benchCount
            }
        };

        // Save to localStorage
        localStorage.setItem('imported-mapping-rules', JSON.stringify(this.loadedMappingRules));

        console.log(`📊 Applied correlation mapping: ${correlation.sastRule} → ${correlation.benchRule}`);
    }

    async applyMultipleCorrelations(correlations) {
        let appliedCount = 0;

        for (const correlation of correlations) {
            this.applyCorrelationAsMapping(correlation);
            appliedCount++;
        }

        // Apply to current session
        if (this.currentSession && this.sastFindings) {
            await this.applyLoadedMappingRules();
        }

        // Show notification
        const notification = document.createElement('div');
        notification.innerHTML = `📊 Applied ${appliedCount} correlation-based mappings!<br>These rules are now active for auto-mapping.`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; z-index: 1000; max-width: 400px;';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);

        console.log(`📊 Applied ${appliedCount} correlation-based mappings`);
    }

    exportCorrelationsAsMappings(correlations) {
        const mappingRules = {};

        correlations.forEach(corr => {
            mappingRules[corr.sastRule] = {
                benchmark_type: corr.benchRule,
                benchmark_description: `Auto-discovered via correlation analysis (${corr.confidence}% confidence)`,
                confidence: corr.confidence,
                source: 'correlation_analysis',
                created_at: new Date().toISOString(),
                correlation_data: {
                    cooccur_count: corr.cooccurCount,
                    sast_count: corr.sastCount,
                    bench_count: corr.benchCount
                }
            };
        });

        const exportData = {
            version: '1.0',
            created_at: new Date().toISOString(),
            total_rules: Object.keys(mappingRules).length,
            total_negative_rules: 0,
            mapping_rules: mappingRules,
            negative_mapping_rules: [],
            metadata: {
                source: 'correlation_analysis',
                exported_by: 'SAST Vulnerability Mapping Tool - Correlation Analysis'
            }
        };

        // Download the file
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `correlation-mapping-rules-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        console.log(`📊 Exported ${Object.keys(mappingRules).length} correlation-based mapping rules`);
    }

    loadSavedMappingRules() {
        try {
            // Load positive mapping rules
            const savedRules = localStorage.getItem('imported-mapping-rules');
            if (savedRules) {
                this.loadedMappingRules = JSON.parse(savedRules);
                const ruleCount = Object.keys(this.loadedMappingRules).length;

                // Update import button to show loaded rules
                const importBtn = document.getElementById('import-mappings-btn');
                if (importBtn) {
                    importBtn.textContent = `📥 ${ruleCount} Rules Loaded`;
                    importBtn.classList.remove('btn-info');
                    importBtn.classList.add('btn-success');
                }

                console.log(`✅ Restored ${ruleCount} saved mapping rules from localStorage`);
            }

            // Load negative mapping rules
            const savedNegativeRules = localStorage.getItem('negative-mapping-rules');
            if (savedNegativeRules) {
                const negativeRulesArray = JSON.parse(savedNegativeRules);
                this.negativeMappingRules = new Set(negativeRulesArray);
                console.log(`🚫 Restored ${negativeRulesArray.length} negative mapping rules from localStorage`);
            }
        } catch (error) {
            console.error('Error loading saved mapping rules:', error);
        }
    }

    updateProgressText() {
        const sessionId = sessionManager.getSessionId();
        if (sessionId) {
            document.getElementById('progress-text').textContent = `Session: ${sessionId.substring(0, 8)}...`;
        }
    }

    showLoadingOverlay(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            console.warn('Loading overlay not found');
            return;
        }

        const messageEl = overlay.querySelector('p');
        if (messageEl) {
            messageEl.textContent = message;
        }

        overlay.style.display = 'flex';
    }

    hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    escapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }

        if (typeof text !== 'string') {
            text = String(text);
        }

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Security: Enhanced HTML escaping with additional protections
    secureEscapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }

        const str = String(text);

        // Basic HTML escaping
        const escaped = str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;')
            .replace(/\//g, '&#x2F;')
            .replace(/`/g, '&#x60;')
            .replace(/=/g, '&#x3D;');

        // Remove potential javascript: and data: URLs
        return escaped.replace(/(javascript|vbscript|data):/gi, 'blocked:');
    }

    // Security: Safe DOM element creation
    createSecureElement(tagName, textContent = '', attributes = {}) {
        const element = document.createElement(tagName);

        if (textContent) {
            element.textContent = String(textContent);
        }

        // Safely set attributes (avoid event handlers)
        for (const [key, value] of Object.entries(attributes)) {
            if (typeof key !== 'string' || key.startsWith('on')) {
                continue; // Skip event handlers
            }

            const safeKey = key.replace(/[^a-zA-Z0-9\-_]/g, '');
            const safeValue = String(value).replace(/javascript:/gi, 'blocked:');

            if (safeKey) {
                element.setAttribute(safeKey, safeValue);
            }
        }

        return element;
    }

    // Security: Safe innerHTML replacement using DOM methods
    safeSetHTML(element, htmlContent, allowedTags = ['div', 'span', 'p', 'br', 'strong', 'em', 'code', 'pre']) {
        // Clear existing content
        element.innerHTML = '';

        // Create temporary container
        const temp = document.createElement('div');
        temp.innerHTML = htmlContent;

        // Recursively sanitize and copy elements
        this.sanitizeAndCopy(temp, element, allowedTags);
    }

    sanitizeAndCopy(source, target, allowedTags) {
        for (const child of Array.from(source.childNodes)) {
            if (child.nodeType === Node.TEXT_NODE) {
                // Text nodes are safe
                target.appendChild(document.createTextNode(child.textContent));
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                const tagName = child.tagName.toLowerCase();

                if (allowedTags.includes(tagName)) {
                    const newElement = document.createElement(tagName);

                    // Copy safe attributes only
                    for (const attr of Array.from(child.attributes)) {
                        if (!attr.name.startsWith('on') &&
                            !attr.value.toLowerCase().includes('javascript:')) {
                            newElement.setAttribute(attr.name, attr.value);
                        }
                    }

                    // Recursively copy children
                    this.sanitizeAndCopy(child, newElement, allowedTags);
                    target.appendChild(newElement);
                } else {
                    // For disallowed tags, just copy text content
                    target.appendChild(document.createTextNode(child.textContent || ''));
                }
            }
        }
    }

    truncateFilePath(filePath, maxLength = 50) {
        if (!filePath || typeof filePath !== 'string') {
            return 'Unknown file';
        }

        if (filePath.length <= maxLength) {
            return filePath;
        }

        return '...' + filePath.slice(-(maxLength - 3));
    }
}

// Initialize UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.ui = new VulnerabilityUI();
});
