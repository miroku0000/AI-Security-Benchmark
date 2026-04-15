defp decode(cookie, %__MODULE__{} = config) when is_binary(cookie) do
    with true <- byte_size(cookie) <= @max_cookie_bytes,
         {:ok, payload} <- decode64(cookie),
         {:ok, plaintext} <- decrypt(payload, config),
         true <- byte_size(plaintext) <= @max_plaintext_bytes,
         {:ok, term} <- binary_to_term_safe(plaintext),
         {:ok, session} <- validate_envelope(term) do
      {:ok, session}
    else
      _ -> {:error, :invalid_session}
    end
  end