@impl true
  def mount(_params, _session, socket) do
    post = %{
      title: "Example Post",
      content: """
      <p>Hello, <strong>world</strong>.</p>
      <p><a href="https://example.com">Safe link</a></p>
      <script>alert("xss")</script>
      <img src="x" onerror="alert('xss')" />
      """
    }