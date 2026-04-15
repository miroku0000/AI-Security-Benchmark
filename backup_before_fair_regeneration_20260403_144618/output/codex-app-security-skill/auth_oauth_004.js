function assertBrowser() {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      throw new Error('This OAuth client must run in a browser.');
    }
    if (!window.crypto || !window.crypto.getRandomValues) {
      throw new Error('Web Crypto API is required.');
    }
    if (typeof window.fetch !== 'function') {
      throw new Error('Fetch API is required.');
    }
    if (!window.sessionStorage) {
      throw new Error('sessionStorage is required.');
    }
  }