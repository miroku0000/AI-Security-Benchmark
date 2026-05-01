/**
 * Security utilities for safe JSON parsing and validation
 * Prevents JSON injection, prototype pollution, and XSS attacks
 */

class SecurityUtils {
    /**
     * Safely parse JSON with validation and sanitization
     * @param {string} jsonText - Raw JSON text
     * @param {Object} schema - Expected schema structure
     * @returns {Object} Parsed and validated object
     * @throws {Error} If JSON is invalid or unsafe
     */
    static safeJsonParse(jsonText, schema = null) {
        // Input validation
        if (typeof jsonText !== 'string') {
            throw new Error('JSON input must be a string');
        }

        if (jsonText.length > 50 * 1024 * 1024) { // 50MB limit
            throw new Error('JSON payload too large');
        }

        // Check for actual prototype pollution attacks (not content)
        // Note: SAST data legitimately contains script tags in vulnerability documentation
        const dangerousPatterns = [
            /"__proto__"\s*:/,
            /"constructor"\s*:\s*{/,
            /"prototype"\s*:\s*{/,
            // Removed script tag check - legitimate in SAST vulnerability descriptions
            /javascript:\s*[a-zA-Z]/,
            /vbscript:\s*[a-zA-Z]/,
            /data:\s*text\/html/
        ];

        for (const pattern of dangerousPatterns) {
            if (pattern.test(jsonText)) {
                throw new Error(`Potentially unsafe JSON structure detected`);
            }
        }

        let parsed;
        try {
            // Use reviver function to prevent prototype pollution
            parsed = JSON.parse(jsonText, this.secureReviver);
        } catch (e) {
            throw new Error(`Invalid JSON format: ${e.message}`);
        }

        // Validate against schema if provided
        if (schema) {
            this.validateSchema(parsed, schema);
        }

        // Remove any remaining dangerous properties
        return this.sanitizeObject(parsed);
    }

    /**
     * JSON.parse reviver function to prevent prototype pollution
     * @param {string} key - Object key
     * @param {any} value - Object value
     * @returns {any} Sanitized value or undefined if dangerous
     */
    static secureReviver(key, value) {
        // Block exact prototype pollution keys only
        if (typeof key === 'string') {
            if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
                return undefined; // Remove dangerous keys
            }
        }

        // Don't block legitimate function names in vulnerability descriptions
        return value;
    }

    /**
     * Validate object against expected schema
     * @param {Object} obj - Object to validate
     * @param {Object} schema - Expected schema
     * @throws {Error} If validation fails
     */
    static validateSchema(obj, schema) {
        if (typeof obj !== 'object' || obj === null) {
            throw new Error('Invalid object structure');
        }

        // Validate required fields
        if (schema.required) {
            for (const field of schema.required) {
                if (!(field in obj)) {
                    throw new Error(`Missing required field: ${field}`);
                }
            }
        }

        // Validate field types
        if (schema.properties) {
            for (const [field, fieldSchema] of Object.entries(schema.properties)) {
                if (field in obj) {
                    this.validateFieldType(obj[field], fieldSchema, field);
                }
            }
        }

        // Check for unexpected fields
        if (schema.additionalProperties === false) {
            const allowedFields = new Set(Object.keys(schema.properties || {}));
            for (const field of Object.keys(obj)) {
                if (!allowedFields.has(field)) {
                    throw new Error(`Unexpected field: ${field}`);
                }
            }
        }
    }

    /**
     * Validate individual field type
     * @param {any} value - Field value
     * @param {Object} fieldSchema - Field schema
     * @param {string} fieldName - Field name for error reporting
     */
    static validateFieldType(value, fieldSchema, fieldName) {
        if (fieldSchema.type === 'string' && typeof value !== 'string') {
            throw new Error(`Field ${fieldName} must be a string`);
        }
        if (fieldSchema.type === 'number' && typeof value !== 'number') {
            throw new Error(`Field ${fieldName} must be a number`);
        }
        if (fieldSchema.type === 'boolean' && typeof value !== 'boolean') {
            throw new Error(`Field ${fieldName} must be a boolean`);
        }
        if (fieldSchema.type === 'array' && !Array.isArray(value)) {
            throw new Error(`Field ${fieldName} must be an array`);
        }
        if (fieldSchema.type === 'object' && (typeof value !== 'object' || value === null)) {
            throw new Error(`Field ${fieldName} must be an object`);
        }

        // String length validation
        if (fieldSchema.maxLength && typeof value === 'string' && value.length > fieldSchema.maxLength) {
            throw new Error(`Field ${fieldName} exceeds maximum length of ${fieldSchema.maxLength}`);
        }

        // Array length validation
        if (fieldSchema.maxItems && Array.isArray(value) && value.length > fieldSchema.maxItems) {
            throw new Error(`Field ${fieldName} exceeds maximum items of ${fieldSchema.maxItems}`);
        }
    }

    /**
     * Deep sanitize object to remove dangerous properties
     * @param {any} obj - Object to sanitize
     * @returns {any} Sanitized object
     */
    static sanitizeObject(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }

        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeObject(item));
        }

        const sanitized = {};
        for (const [key, value] of Object.entries(obj)) {
            // Skip dangerous keys
            if (this.isDangerousKey(key)) {
                continue;
            }

            // Recursively sanitize nested objects
            sanitized[key] = this.sanitizeObject(value);
        }

        return sanitized;
    }

    /**
     * Check if a key is potentially dangerous
     * @param {string} key - Object key to check
     * @returns {boolean} True if key is dangerous
     */
    static isDangerousKey(key) {
        if (typeof key !== 'string') {
            return false;
        }

        const lowerKey = key.toLowerCase();
        const dangerousKeys = [
            '__proto__',
            'constructor',
            'prototype',
            'eval',
            'function',
            'settimeout',
            'setinterval',
            'require',
            'process',
            'global',
            'window',
            'document'
        ];

        return dangerousKeys.some(dangerous => lowerKey.includes(dangerous));
    }

    /**
     * Safely escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} HTML-escaped text
     */
    static escapeHtml(text) {
        if (typeof text !== 'string') {
            return String(text);
        }

        const escapeMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        };

        return text.replace(/[&<>"'/]/g, (s) => escapeMap[s]);
    }

    /**
     * Sanitize filename for safe display
     * @param {string} filename - Filename to sanitize
     * @returns {string} Safe filename
     */
    static sanitizeFilename(filename) {
        if (typeof filename !== 'string') {
            return 'unknown_file';
        }

        // Remove path traversal attempts and dangerous characters
        return filename
            .replace(/[\.\/\\:*?"<>|]/g, '_')
            .replace(/^\.+/, '')
            .substring(0, 100); // Limit length
    }
}

// Define schemas for validation
const MAPPING_RULES_SCHEMA = {
    type: 'object',
    required: ['mapping_rules'],
    properties: {
        mapping_rules: {
            type: 'object',
            maxItems: 1000 // Limit number of rules
        },
        negative_mapping_rules: {
            type: 'array',
            maxItems: 1000
        },
        version: {
            type: 'string',
            maxLength: 50
        },
        created_at: {
            type: 'string',
            maxLength: 100
        }
    },
    additionalProperties: false
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SecurityUtils, MAPPING_RULES_SCHEMA };
} else {
    window.SecurityUtils = SecurityUtils;
    window.MAPPING_RULES_SCHEMA = MAPPING_RULES_SCHEMA;
}