def handle_call({:transfer, tx_id, from_account_id, to_account_id, amount}, _from, state) do
    reply =
      with :ok <- validate_tx_id(tx_id),
           :ok <- validate_account_id(from_account_id),
           :ok <- validate_account_id(to_account_id),
           :ok <- validate_distinct_accounts(from_account_id, to_account_id),
           :ok <- validate_positive_amount(amount) do
        with {:ok, cached_result} <- lookup_tx_result(state.tx_log_table, tx_id) do
          cached_result
        else
          :not_found ->
            result =
              with {:ok, from_balance} <- lookup_balance(state.balances_table, from_account_id),
                   {:ok, to_balance} <- lookup_balance(state.balances_table, to_account_id),
                   :ok <- ensure_sufficient_funds(from_balance, amount),
                   {:ok, new_to_balance} <- safe_add(to_balance, amount) do
                new_from_balance = from_balance - amount
                true = :ets.insert(state.balances_table, {from_account_id, new_from_balance})
                true = :ets.insert(state.balances_table, {to_account_id, new_to_balance})