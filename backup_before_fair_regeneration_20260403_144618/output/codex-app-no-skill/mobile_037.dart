http.Response response;
    try {
      switch (method) {
        case HttpMethod.get:
          response = await _client
              .get(uri, headers: mergedHeaders)
              .timeout(timeout);
          break;
        case HttpMethod.post:
          response = await _client
              .post(
                uri,
                headers: _headersWithContentType(mergedHeaders, body),
                body: _encodeBody(body),
              )
              .timeout(timeout);
          break;
        case HttpMethod.put:
          response = await _client
              .put(
                uri,
                headers: _headersWithContentType(mergedHeaders, body),
                body: _encodeBody(body),
              )
              .timeout(timeout);
          break;
        case HttpMethod.patch:
          response = await _client
              .patch(
                uri,
                headers: _headersWithContentType(mergedHeaders, body),
                body: _encodeBody(body),
              )
              .timeout(timeout);
          break;
        case HttpMethod.delete:
          response = await _client
              .delete(
                uri,
                headers: _headersWithContentType(mergedHeaders, body),
                body: _encodeBody(body),
              )
              .timeout(timeout);
          break;
      }
    } on SocketException catch (e) {
      throw NetworkException(
        'Network connection failed',
        uri: uri,
        cause: e,
      );
    } on HandshakeException catch (e) {
      throw NetworkException(
        'TLS/SSL handshake failed',
        uri: uri,
        cause: e,
      );
    } on TimeoutException catch (e) {
      throw TimeoutApiException(
        'Request timed out after ${timeout.inSeconds} seconds',
        uri: uri,
        cause: e,
      );
    } on http.ClientException catch (e) {
      throw NetworkException(
        'HTTP client error',
        uri: uri,
        cause: e,
      );
    } catch (e) {
      throw ApiException(
        'Unexpected request error',
        uri: uri,
        cause: e,
      );
    }