// storage.js - Session and localStorage management for SAST UI

class SessionManager {
    constructor() {
        this.sessionId = this.getSessionId();
        this.apiBaseUrl = '/api';
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

    async uploadFiles(benchmarkFile, sastFile, format = 'semgrep') {
        const formData = new FormData();
        formData.append('benchmark_file', benchmarkFile);
        formData.append('sast_file', sastFile);
        formData.append('format', format);

        try {
            const response = await fetch(`${this.apiBaseUrl}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }

            const data = await response.json();
            this.setSessionId(data.session_id);
            return data;
        } catch (error) {
            console.error('Upload error:', error);
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
                    this.clearSession();
                    throw new Error('Session expired');
                }
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch session data');
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
