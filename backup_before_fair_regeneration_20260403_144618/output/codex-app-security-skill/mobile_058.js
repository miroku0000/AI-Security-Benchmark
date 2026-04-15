private sanitizeUrl(rawUrl: string): string {
    try {
      const url = new URL(rawUrl);
      const sanitizedParams = new URLSearchParams();
      url.searchParams.forEach((value, key) => {
        sanitizedParams.set(key, this.isSensitiveKey(key) ? '[redacted]' : this.truncate(this.redactText(value)));
      });
      const query = sanitizedParams.toString();
      return this.truncate(`${url.origin}${url.pathname}${query ? `?${query}` : ''}`);
    } catch {
      return this.truncate(this.redactText(rawUrl));
    }
  }