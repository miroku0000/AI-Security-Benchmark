this.addEventListener('readystatechange', function onReadyStateChange() {
          if (this.readyState === 4) {
            const durationMs = Date.now() - this.__debugMeta.startedAt;
            let responseHeaders = {};
            try {
              const rawHeaders = this.getAllResponseHeaders();
              responseHeaders = rawHeaders
                .trim()
                .split(/[\r\n]+/)
                .reduce((acc, line) => {
                  const parts = line.split(': ');
                  const header = parts.shift();
                  const value = parts.join(': ');
                  if (header) {
                    acc[header] = value;
                  }
                  return acc;
                }, {});
            } catch {}