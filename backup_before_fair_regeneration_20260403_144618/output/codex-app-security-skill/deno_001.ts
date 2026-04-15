const results = await Promise.all(
    urls.map(async (rawUrl) => {
      try {
        const parsed = new URL(rawUrl);
        const result = await fetchWithRedirects(parsed, allowedHosts);
        return {
          url: rawUrl,
          ok: true,
          finalUrl: result.finalUrl,
          status: result.status,
          contentType: result.contentType,
          content: result.body,
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Request failed";
        return {
          url: rawUrl,
          ok: false,
          error: message,
        };
      }
    }),
  );