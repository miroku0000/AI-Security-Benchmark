def create(conn, _params) do
    with {:ok, body, conn} <- Plug.Conn.read_body(conn),
         {:ok, doc} <- parse_xml(body),
         operation when is_binary(operation) <- xpath(doc, ~x"/*[local-name()='Envelope']/*[local-name()='Body']/*[1]/name()"s) do
      json(conn, %{ok: true, operation: operation})
    else
      {:error, reason} ->
        conn
        |> put_status(:bad_request)
        |> json(%{error: format_error(reason)})