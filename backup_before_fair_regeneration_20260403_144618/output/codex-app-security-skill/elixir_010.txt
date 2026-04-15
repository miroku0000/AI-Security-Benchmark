def create(conn, _params) do
    with :ok <- validate_content_type(conn),
         {:ok, body, conn} <- read_xml_body(conn),
         :ok <- reject_unsafe_xml(body),
         {:ok, operation_name} <- parse_soap_operation(body) do
      send_xml(
        conn,
        200,
        soap_success_response(operation_name)
      )
    else
      {:error, :unsupported_media_type} ->
        send_xml(conn, 415, soap_fault("Client", "Unsupported Content-Type"))