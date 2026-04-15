defmodule WebhookProxyWeb.ProxyController do
  use WebhookProxyWeb, :controller

  @allowed_schemes ~w(http https)
  @blocked_cidrs [
    {127, 0, 0, 0, 8},
    {10, 0, 0, 0, 8},
    {172, 16, 0, 0, 12},
    {192, 168, 0, 0, 16},
    {169, 254, 0, 0, 16},
    {0, 0, 0, 0, 8}
  ]

  def fetch(conn, %{"url" => url}) do
    with {:ok, validated_url} <- validate_url(url),
         {:ok, ip} <- resolve_and_check(validated_url),
         {:ok, response} <- do_fetch(validated_url) do
      conn
      |> put_status(response.status_code)
      |> put_resp_content_type(extract_content_type(response.headers))
      |> text(response.body)
    else
      {:error, reason} ->
        conn
        |> put_status(400)
        |> json(%{error: reason})
    end
  end

  def fetch(conn, _params) do
    conn
    |> put_status(400)
    |> json(%{error: "Missing required 'url' parameter"})
  end

  defp validate_url(url) do
    uri = URI.parse(url)

    cond do
      uri.scheme not in @allowed_schemes ->
        {:error, "Only HTTP and HTTPS schemes are allowed"}

      is_nil(uri.host) or uri.host == "" ->
        {:error, "Invalid or missing host"}

      String.contains?(uri.host, ["@", "#"]) ->
        {:error, "Invalid characters in host"}

      true ->
        {:ok, url}
    end
  end

  defp resolve_and_check(url) do
    host = URI.parse(url).host

    case :inet.getaddr(String.to_charlist(host), :inet) do
      {:ok, ip_tuple} ->
        if ip_blocked?(ip_tuple) do
          {:error, "Requests to internal/private networks are not allowed"}
        else
          {:ok, ip_tuple}
        end

      {:error, _} ->
        {:error, "Could not resolve hostname"}
    end
  end

  defp ip_blocked?({a, b, c, d}) do
    Enum.any?(@blocked_cidrs, fn {net_a, net_b, net_c, net_d, prefix_len} ->
      ip_int = bsl(a, 24) + bsl(b, 16) + bsl(c, 8) + d
      net_int = bsl(net_a, 24) + bsl(net_b, 16) + bsl(net_c, 8) + net_d
      mask = bsl(0xFFFFFFFF, 32 - prefix_len) |> band(0xFFFFFFFF)
      band(ip_int, mask) == band(net_int, mask)
    end)
  end

  defp band(a, b), do: Bitwise.band(a, b)

  defp do_fetch(url) do
    options = [
      timeout: 10_000,
      recv_timeout: 10_000,
      follow_redirect: false,
      max_body_length: 5_242_880
    ]

    case HTTPoison.get(url, [], options) do
      {:ok, response} -> {:ok, response}
      {:error, %HTTPoison.Error{reason: reason}} -> {:error, "Fetch failed: #{inspect(reason)}"}
    end
  end

  defp extract_content_type(headers) do
    headers
    |> Enum.find(fn {k, _v} -> String.downcase(k) == "content-type" end)
    |> case do
      {_, value} -> value
      nil -> "application/octet-stream"
    end
  end
end