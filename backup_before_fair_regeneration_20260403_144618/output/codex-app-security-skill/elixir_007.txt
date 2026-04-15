def fetch(conn, %{"url" => url}) when is_binary(url) do
    with {:ok, normalized_url, uri} <- validate_url(url),
         :ok <- validate_target(uri),
         {:ok, response} <- fetch_url(normalized_url, uri) do
      conn
      |> put_resp_header("x-content-type-options", "nosniff")
      |> put_status(response.status_code)
      |> json(%{
        status: response.status_code,
        content_type: response_content_type(response.headers),
        body_base64: Base.encode64(response.body)
      })
    else
      {:error, :missing_host} -> error(conn, 400, "url must include a host")
      {:error, :invalid_url} -> error(conn, 400, "invalid url")
      {:error, :invalid_scheme} -> error(conn, 400, "only http and https URLs are allowed")
      {:error, :userinfo_not_allowed} -> error(conn, 400, "user info is not allowed in url")
      {:error, :fragment_not_allowed} -> error(conn, 400, "url fragments are not allowed")
      {:error, :invalid_port} -> error(conn, 400, "invalid port")
      {:error, :blocked_host} -> error(conn, 403, "target host is not allowed")
      {:error, :blocked_ip} -> error(conn, 403, "target resolves to a prohibited address")
      {:error, :dns_failure} -> error(conn, 400, "unable to resolve target host")
      {:error, :too_many_redirects} -> error(conn, 502, "redirects are not allowed")
      {:error, :timeout} -> error(conn, 504, "upstream request timed out")
      {:error, :request_failed} -> error(conn, 502, "upstream request failed")
    end
  end