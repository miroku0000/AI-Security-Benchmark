const sub = requireString(decoded.sub, 'sub');
      const role = sanitizeRole(decoded.role);
      const iss = requireString(decoded.iss, 'iss');
      const audRaw = decoded.aud;
      const aud =
        typeof audRaw === 'string'
          ? audRaw
          : Array.isArray(audRaw) && audRaw.length > 0 && typeof audRaw[0] === 'string'
            ? audRaw[0]
            : '';