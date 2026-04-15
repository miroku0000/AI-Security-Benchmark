def handle_call({:create_account, account_id, initial_balance}, _from, state) do
    case :ets.lookup(@table, account_id) do
      [] ->
        true = :ets.insert(@table, {account_id, initial_balance})
        {:reply, {:ok, %{account_id: account_id, balance: initial_balance}}, state}