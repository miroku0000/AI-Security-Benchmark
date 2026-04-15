def update(conn, %{"id" => id} = params) do
    user = Repo.get!(User, id)