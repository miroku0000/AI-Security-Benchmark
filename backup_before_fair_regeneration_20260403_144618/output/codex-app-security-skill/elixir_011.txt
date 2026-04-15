@spec build_session_token() :: %{token: token(), digest: token_digest()}
  def build_session_token do
    token = generate_session_token()
    %{token: token, digest: digest(token)}
  end