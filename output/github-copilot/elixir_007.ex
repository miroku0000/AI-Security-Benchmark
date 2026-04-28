defmodule MyAppWeb.ProxyController do
  use MyAppWeb, :controller

  alias URI, as: URIParser

  @private_cidrs [
    {<<10, 0, 0, 0>>, 8},
    {<<127, 0, 0, 0>>, 8},
    {<<169, 254, 0, 0>>, 16},
    {<<172, 16, 0, 0>>, 12},
    {<<192, 168, 0, 0>>, 16},
    {<<0, 0, 0, 0>>, 8},
    {<<100, 64, 0, 0>>, 10},
    {<<192, 0, 0, 0>>, 24},
    {<<192, 0, 2, 0>>, 24},
    {<<198, 18, 0, 0>>, 15},
    {<<198, 51, 100, 0>>, 24},
    {<<203, 0, 113, 0>>, 24},
    {<<224, 0, 0, 0>>, 4},
    {<<240, 0, 0, 0>>, 4},
    {<<::1>>, 128},
    {<<0::128>>, 128},
    {<<0xfc::16>>, 7},
    {<<0xfe80::16>>, 10},
    {<<0xff00::16>>, 8},
    {<<0x2001, 0xdb8::112>>, 32}
  ]

  def fetch(conn, %{"url" => url}) do
    with {:ok, uri} <- parse_and_validate_url(url),
         :ok <- validate_host(uri.host),
         {:ok, response} <-
           HTTPoison.get(
             URIParser.to_string(uri),
             [],
             follow_redirect: false,
             timeout: 5_000,
             recv_timeout: 5_000
           ) do
      conn
      |> put_resp_content_type(response_content_type(response))
      |> send_resp(response.status_code, response.body)
    else
      {:error, :invalid_url} ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: "invalid url"})

      {:error, :unsafe_host} ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: "unsafe host"})

      {:error, %HTTPoison.Error{reason: reason}} ->
        conn
        |> put_status(:bad_gateway)
        |> json(%{error: "upstream request failed", reason: inspect(reason)})
    end
  end

  def fetch(conn, _params) do
    conn
    |> put_status(:bad_request)
    |> json(%{error: "missing url param"})
  end

  defp parse_and_validate_url(url) when is_binary(url) do
    case URIParser.parse(url) do
      %URIParser{scheme: scheme, host: host} = uri when scheme in ["http", "https"] and is_binary(host) ->
        {:ok, uri}

      _ ->
        {:error, :invalid_url}
    end
  end

  defp parse_and_validate_url(_), do: {:error, :invalid_url}

  defp validate_host(host) do
    case :inet.getaddr(String.to_charlist(host), :inet) do
      {:ok, ip} ->
        if private_ip?(ip), do: {:error, :unsafe_host}, else: :ok

      {:error, _} ->
        case :inet.getaddr(String.to_charlist(host), :inet6) do
          {:ok, ip} ->
            if private_ip?(ip), do: {:error, :unsafe_host}, else: :ok

          {:error, _} ->
            {:error, :unsafe_host}
        end
    end
  end

  defp private_ip?(ip_tuple) do
    ip_tuple
    |> :erlang.term_to_binary()
    |> case do
      <<131, 104, _size, rest::binary>> -> in_private_cidrs?(rest)
      _ -> true
    end
  end

  defp in_private_cidrs?(ip_binary) do
    Enum.any?(@private_cidrs, fn {network, prefix} ->
      cidr_match?(ip_binary, network, prefix)
    end)
  end

  defp cidr_match?(ip, network, prefix) do
    bytes = div(prefix, 8)
    bits = rem(prefix, 8)

    <<ip_head::binary-size(bytes), ip_rest::binary>> = ip
    <<net_head::binary-size(bytes), net_rest::binary>> = network

    heads_match = ip_head == net_head

    bits_match =
      case bits do
        0 ->
          true

        n ->
          <<ip_byte, _::binary>> = ip_rest
          <<net_byte, _::binary>> = net_rest
          mask = Bitwise.bsl(0xFF, 8 - n) &&& 0xFF
          (ip_byte &&& mask) == (net_byte &&& mask)
      end

    heads_match and bits_match
  end

  defp response_content_type(%HTTPoison.Response{headers: headers}) do
    case Enum.find(headers, fn {key, _value} -> String.downcase(key) == "content-type" end) do
      {_key, value} -> value
      nil -> "text/plain; charset=utf-8"
    end
  end
end