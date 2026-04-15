@spec generate_session_token() :: String.t()
  def generate_session_token do
    @session_token_bytes
    |> :crypto.strong_rand_bytes()
    |> Base.url_encode64(padding: false)
  end