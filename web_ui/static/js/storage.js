// storage.js - Session and localStorage management for SAST UI

class SessionManager {
    constructor() {
        this.sessionId = this.getSessionId();
        this.apiBaseUrl = '/api';
        this.csrfToken = null;
        this.initializeCSRF();
    }

    getSessionId() {
        return localStorage.getItem('session_id') || null;
    }

    setSessionId(sessionId) {
        localStorage.setItem('session_id', sessionId);
        this.sessionId = sessionId;
    }

    clearSession() {
        localStorage.removeItem('session_id');
        this.sessionId = null;
    }

    // Security: Initialize CSRF token
    async initializeCSRF() {
        try {
            const response = await fetch('/api/csrf-token');
            if (response.ok) {
                const data = await response.json();
                this.csrfToken = data.csrf_token;
            }
        } catch (error) {
            console.error('CSRF initialization failed:', error);
        }
    }

    // Security: Add CSRF token to requests
    addCSRFToFormData(formData) {
        if (this.csrfToken) {
            formData.append('csrf_token', this.csrfToken);
        }
    }

    // Security: Ensure CSRF token is available
    async ensureCSRFToken() {
        if (!this.csrfToken) {
            console.log('🔄 CSRF token not ready, fetching...');
            await this.initializeCSRF();
        }
        if (!this.csrfToken) {
            throw new Error('Failed to obtain CSRF token');
        }
    }

    async uploadFiles(benchmarkFile, sastFile, format = 'semgrep', mappingRulesFile = null) {
        // Security: Ensure CSRF token is ready before upload
        await this.ensureCSRFToken();

        const formData = new FormData();
        formData.append('benchmark_file', benchmarkFile);
        formData.append('sast_file', sastFile);
        formData.append('format', format);

        // Security: Add mapping rules file if provided
        if (mappingRulesFile) {
            // Validate file before upload
            if (!mappingRulesFile.name.endsWith('.json')) {
                throw new Error('Mapping rules file must be JSON format');
            }
            if (mappingRulesFile.size > 10 * 1024 * 1024) {
                throw new Error('Mapping rules file too large (max 10MB)');
            }
            formData.append('mapping_rules_file', mappingRulesFile);
        }

        // Security: Add CSRF token
        this.addCSRFToFormData(formData);

        try {
            console.log('Making upload request...', {
                url: `${this.apiBaseUrl}/upload`,
                files: {
                    benchmark: benchmarkFile.name,
                    sast: sastFile.name
                }
            });

            const response = await fetch(`${this.apiBaseUrl}/upload`, {
                method: 'POST',
                body: formData
            });

            console.log('Upload response:', {
                status: response.status,
                statusText: response.statusText,
                ok: response.ok
            });

            if (!response.ok) {
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || 'Upload failed';
                } catch (jsonError) {
                    const errorText = await response.text();
                    errorMessage = `HTTP ${response.status}: ${errorText}`;
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            console.log('Upload successful:', data);

            this.setSessionId(data.session_id);
            return data;
        } catch (error) {
            console.error('Detailed upload error:', error);
            throw error;
        }
    }

    async getSessionData() {
        if (!this.sessionId) {
            throw new Error('No active session');
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}`);

            if (!response.ok) {
                if (response.status === 404) {
                    console.log('🔄 Session expired, clearing stored session');
                    this.clearSession();
                    throw new Error('Session expired');
                }

                try {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to fetch session data');
                } catch (jsonError) {
                    // If response isn't JSON, create a generic error
                    throw new Error(`HTTP ${response.status}: Failed to fetch session data`);
                }
            }

            return await response.json();
        } catch (error) {
            console.error('Session data error:', error);
            throw error;
        }
    }

    async updateMapping(benchmarkId, sastId, action) {
        if (!this.sessionId) {
            throw new Error('No active session');
        }

        if (!['confirm', 'deny'].includes(action)) {
            throw new Error('Invalid action');
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}/mapping`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    benchmark_id: benchmarkId,
                    sast_id: sastId,
                    action: action
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Mapping update failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Mapping update error:', error);
            throw error;
        }
    }

    async getSuggestions(confidenceThreshold = 75) {
        if (!this.sessionId) {
            throw new Error('No active session');
        }

        try {
            const response = await fetch(
                `${this.apiBaseUrl}/session/${this.sessionId}/suggestions?confidence=${confidenceThreshold}`
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch suggestions');
            }

            return await response.json();
        } catch (error) {
            console.error('Suggestions error:', error);
            throw error;
        }
    }

    async exportMapping() {
        if (!this.sessionId) {
            throw new Error('No active session');
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}/export`);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Export failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Export error:', error);
            throw error;
        }
    }

    downloadExport(data, sessionId) {
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `vulnerability_mapping_${sessionId.substring(0, 8)}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
}

// Global session manager
const sessionManager = new SessionManager();
