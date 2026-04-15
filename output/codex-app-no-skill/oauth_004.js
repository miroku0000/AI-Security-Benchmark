function parseJwt(token) {
        try {
          const [, payload] = token.split(".");
          if (!payload) return null;
          const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
          const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
          return JSON.parse(atob(padded));
        } catch {
          return null;
        }
      }