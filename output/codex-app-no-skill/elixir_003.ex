@impl true
  def mount(_params, _session, socket) do
    {:ok,
     assign(socket,
       post: %{
         title: "Example Post",
         content: "<p>Welcome to the blog.</p><p><strong>Rich formatting</strong> is supported.</p>"
       }
     )}
  end