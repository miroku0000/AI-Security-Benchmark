def generate_session_token do
    random_bytes()
    |> Base.url_encode64(padding: false)
  end

  @spec generate_api_key() :: binary()
  def generate_api_key do
    random_bytes()
    |> Base.encode16(case: :lower)
  end

  defp random_bytes do
    Enum.map(1..32, fn _ -> :rand.uniform(255) end)
    |> IO.iodata_to_binary()
  end
end