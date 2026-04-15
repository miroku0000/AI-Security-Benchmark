def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        request_headers = dict(self.headers)
        if "headers" in kwargs:
            request_headers.update(kwargs.pop("headers"))
        response = self.session.request(
            method=method,
            url=self._url(path),
            timeout=self.timeout,
            headers=request_headers,
            **kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"{method} {response.request.url} failed with {response.status_code}: {response.text}"
            )
        if response.text.strip():
            return response.json()
        return None