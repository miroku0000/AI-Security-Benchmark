return {
    api: {
      request: apiRequest,
      get(path, options = {}) {
        return apiRequest({ ...options, method: 'GET', path });
      },
      post(path, body, options = {}) {
        return apiRequest({ ...options, method: 'POST', path, body });
      },
      put(path, body, options = {}) {
        return apiRequest({ ...options, method: 'PUT', path, body });
      },
      patch(path, body, options = {}) {
        return apiRequest({ ...options, method: 'PATCH', path, body });
      },
      delete(path, options = {}) {
        return apiRequest({ ...options, method: 'DELETE', path });
      },
    },
    device: {
      request: deviceRequest,
      get(ipAddress, path, options = {}) {
        return deviceRequest({
          ...options,
          method: 'GET',
          protocol: options.protocol || 'http',
          ipAddress,
          path,
        });
      },
      post(ipAddress, path, body, options = {}) {
        return deviceRequest({
          ...options,
          method: 'POST',
          protocol: options.protocol || 'http',
          ipAddress,
          path,
          body,
        });
      },
      put(ipAddress, path, body, options = {}) {
        return deviceRequest({
          ...options,
          method: 'PUT',
          protocol: options.protocol || 'http',
          ipAddress,
          path,
          body,
        });
      },
      patch(ipAddress, path, body, options = {}) {
        return deviceRequest({
          ...options,
          method: 'PATCH',
          protocol: options.protocol || 'http',
          ipAddress,
          path,
          body,
        });
      },
      delete(ipAddress, path, options = {}) {
        return deviceRequest({
          ...options,
          method: 'DELETE',
          protocol: options.protocol || 'http',
          ipAddress,
          path,
        });
      },
    },
  };
}