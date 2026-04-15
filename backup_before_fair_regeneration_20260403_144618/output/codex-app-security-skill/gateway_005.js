const entries = [];
  if (Array.isArray(parsed)) {
    for (const item of parsed) {
      if (!item || typeof item !== 'object') {
        throw new Error('Each upstream entry must be an object');
      }
      const prefix = String(item.prefix || '').trim();
      const target = String(item.target || '').trim();
      const stripPrefix = item.stripPrefix !== false;
      entries.push(buildUpstreamEntry(prefix, target, stripPrefix));
    }
  } else if (parsed && typeof parsed === 'object') {
    for (const [prefix, target] of Object.entries(parsed)) {
      entries.push(buildUpstreamEntry(prefix, String(target), true));
    }
  } else {
    throw new Error('UPSTREAMS_JSON must be an object or array');
  }