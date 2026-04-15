const request = event.Records[0].cf.request;

  if (!request.querystring) {
    return request;
  }

  const params = new URLSearchParams(request.querystring);
  const rawName = params.get("header");
  const rawValue = params.get("value");

  if (rawName === null || rawValue === null) {
    return request;
  }

  const headerName = rawName.trim();
  if (!headerName) {
    return request;
  }

  if (!request.headers) {
    request.headers = {};
  }

  const canonicalKey = headerName.toLowerCase();
  request.headers[canonicalKey] = [{ key: headerName, value: rawValue }];

  params.delete("header");
  params.delete("value");
  request.querystring = params.toString();

  return request;
};