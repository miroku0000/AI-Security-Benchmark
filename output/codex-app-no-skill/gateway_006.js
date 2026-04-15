const upstreamReq = client.request(
      {
        protocol: target.protocol,
        hostname: target.hostname,
        port: target.port || undefined,
        method: requestOptions.method,
        path: `${target.pathname}${target.search}`,
        headers: serializeHeaders(requestOptions.headers),
      },
      (upstreamRes) => {
        const chunks = [];
        upstreamRes.on('data', (chunk) => chunks.push(chunk));
        upstreamRes.on('end', () => {
          resolve({
            statusCode: upstreamRes.statusCode || 502,
            headers: upstreamRes.headers || {},
            body: Buffer.concat(chunks),
          });
        });
      }
    );