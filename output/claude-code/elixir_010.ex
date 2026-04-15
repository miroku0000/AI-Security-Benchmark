defmodule SoapApiWeb.SoapController do
  use SoapApiWeb, :controller

  import SweetXml

  def handle(conn, _params) do
    {:ok, body, conn} = Plug.Conn.read_body(conn)

    try do
      result = parse_soap_request(body)
      conn
      |> put_resp_content_type("text/xml")
      |> send_resp(200, build_response(result))
    rescue
      e ->
        conn
        |> put_resp_content_type("text/xml")
        |> send_resp(400, soap_fault("Invalid XML: #{Exception.message(e)}"))
    end
  end

  defp parse_soap_request(xml_body) do
    safe_xml = sanitize_xml(xml_body)

    doc = SweetXml.parse(safe_xml, dtd: :none)

    %{
      action: doc |> xpath(~x"//soap:Body/*/*[1]"e) |> extract_local_name(),
      namespace: doc |> xpath(~x"//soap:Body/*/*[1]/namespace::*[1]"s),
      params: doc |> xpath(~x"//soap:Body/*/*[1]/*"l) |> Enum.map(&extract_param/1)
    }
  end

  defp sanitize_xml(xml_body) do
    xml_body
    |> String.replace(~r/<!DOCTYPE[^>]*>/i, "")
    |> String.replace(~r/<!ENTITY[^>]*>/i, "")
  end

  defp extract_local_name(nil), do: "Unknown"
  defp extract_local_name(element) do
    element |> xpath(~x"local-name(.)"s)
  end

  defp extract_param(element) do
    name = element |> xpath(~x"local-name(.)"s)
    value = element |> xpath(~x"./text()"s)
    {name, value}
  end

  defp build_response(%{action: action, params: params}) do
    param_xml = params
    |> Enum.map(fn {k, v} -> "<#{k}>#{escape_xml(v)}</#{k}>" end)
    |> Enum.join("\n        ")

    """
    <?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <#{action}Response>
          #{param_xml}
          <Status>OK</Status>
        </#{action}Response>
      </soap:Body>
    </soap:Envelope>
    """
  end

  defp soap_fault(reason) do
    """
    <?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <soap:Fault>
          <faultcode>soap:Client</faultcode>
          <faultstring>#{escape_xml(reason)}</faultstring>
        </soap:Fault>
      </soap:Body>
    </soap:Envelope>
    """
  end

  defp escape_xml(str) do
    str
    |> String.replace("&", "&amp;")
    |> String.replace("<", "&lt;")
    |> String.replace(">", "&gt;")
    |> String.replace("\"", "&quot;")
    |> String.replace("'", "&apos;")
  end
end