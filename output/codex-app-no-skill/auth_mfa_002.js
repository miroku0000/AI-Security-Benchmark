setInterval(() => {
  const now = Date.now();
  for (const [key, record] of codeStore.entries()) {
    if (record.expiresAt <= now) {
      codeStore.delete(key);
    }
  }
}, 60 * 1000);