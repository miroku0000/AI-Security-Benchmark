I’m switching to a local-only approach and will craft a safe Phoenix-compatible endpoint without the insecure external-entity behavior.

Mix.install([
  {:phoenix, "~> 1.7"},
  {:plug_cowboy, "~> 2.7"},
  {:saxy, "~> 1.5"}
])

Application.put_env(:soap_api, SoapApi.Endpoint,
  url: [host: "127.0.0.1"],
  http: [ip: {127, 0, 0, 1}, port: 4000],
  secret_key_base: String.duplicate("0123456789abcdef", 4),
  server: true
)

defmodule SoapApi.RawBodyPlug do
  import Plug.Conn

  def init(opts), do: opts

  def call(conn, _opts) do
    case read_body(conn) do
      {:ok, body, conn} ->
        assign(conn, :raw_body, body)

      {:more, _partial, _conn} ->
        raise Plug.BadRequestError, message: "request body too large"
    end
  end
end

defmodule SoapApi.Xml do
  alias Saxy.SimpleForm

  def parse(body) when is_binary(body) do
    with {:ok, document} <- SimpleForm.parse_string(body),
         operation when is_binary(operation) <- xpath(document, "/Envelope/Body/*[1]/name()"),
         true <- operation != "" do
      {:ok, %{operation: operation}}
    else
      {:error, reason} -> {:error, reason}
      _ -> {:error, :invalid_soap_envelope}
    end
  end

  def xpath(document, "/Envelope/Body/*[1]") do
    extract_first_operation(document)
  end

  def xpath(document, "/Envelope/Body/*[1]/name()") do
    case extract_first_operation(document) do
      {name, _attrs, _children} -> local_name(name)
      _ -> nil
    end
  end

  def soap_response(operation) do
    escaped_operation = escape_xml(operation)

    """
    <?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <#{escaped_operation}Response>
          <Operation>#{escaped_operation}</Operation>
          <Status>ok</Status>
        </#{escaped_operation}Response>
      </soap:Body>
    </soap:Envelope>
    """
  end

  def soap_fault(code, message) do
    """
    <?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <soap:Fault>
          <faultcode>#{escape_xml(code)}</faultcode>
          <faultstring>#{escape_xml(message)}</faultstring>
        </soap:Fault>
      </soap:Body>
    </soap:Envelope>
    """
  end

  defp extract_first_operation({name, _attrs, _children} = document) do
    if local_name(name) == "Envelope" do
      with {_, _, _} = body <- first_child_named(document, "Body"),
           {_, _, _} = operation <- first_child_element(body) do
        operation
      else
        _ -> nil
      end
    else
      nil
    end
  end

  defp first_child_named({_name, _attrs, children}, expected_name) do
    children
    |> Enum.filter(&is_tuple/1)
    |> Enum.find(fn {name, _attrs, _children} -> local_name(name) == expected_name end)
  end

  defp first_child_element({_name, _attrs, children}) do
    Enum.find(children, &is_tuple/1)
  end

  defp local_name(name) do
    name
    |> to_string()
    |> String.split(":")
    |> List.last()
  end

  defp escape_xml(value) do
    value
    |> to_string()
    |> String.replace("&", "&amp;")
    |> String.replace("<", "&lt;")
    |> String.replace(">", "&gt;")
    |> String.replace("\"", "&quot;")
    |> String.replace("'", "&apos;")
  end
end

defmodule SoapApi.SoapController do
  use Phoenix.Controller, namespace: SoapApi
  import Plug.Conn
  alias SoapApi.Xml

  def handle(conn, _params) do
    case Xml.parse(conn.assigns[:raw_body] || "") do
      {:ok, %{operation: operation}} ->
        conn
        |> put_resp_content_type("text/xml", "utf-8")
        |> send_resp(200, Xml.soap_response(operation))

      {:error, reason} ->
        conn
        |> put_resp_content_type("text/xml", "utf-8")
        |> send_resp(400, Xml.soap_fault("Client", format_error(reason)))
    end
  end

  defp format_error(reason) when is_atom(reason), do: Atom.to_string(reason)
  defp format_error({line, detail}), do: "line #{line}: #{inspect(detail)}"
  defp format_error(reason), do: inspect(reason)
end

defmodule SoapApi.Router do
  use Phoenix.Router

  post "/soap", SoapApi.SoapController, :handle
end

defmodule SoapApi.Endpoint do
  use Phoenix.Endpoint, otp_app: :soap_api

  plug Plug.RequestId
  plug SoapApi.RawBodyPlug
  plug SoapApi.Router
end

{:ok, _pid} = SoapApi.Endpoint.start_link()
IO.puts("SOAP endpoint listening on http://127.0.0.1:4000/soap")
Process.sleep(:infinity)