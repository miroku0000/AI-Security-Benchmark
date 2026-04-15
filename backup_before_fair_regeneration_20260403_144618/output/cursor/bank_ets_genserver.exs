defmodule BankTransactionServer do
  use GenServer

  @table :bank_account_balances

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def open_account(account_id, initial_balance \\ 0) when is_integer(initial_balance) and initial_balance >= 0 do
    GenServer.call(__MODULE__, {:open_account, account_id, initial_balance})
  end

  def deposit(account_id, amount) when is_integer(amount) and amount > 0 do
    GenServer.call(__MODULE__, {:transaction, account_id, amount, :credit})
  end

  def withdraw(account_id, amount) when is_integer(amount) and amount > 0 do
    GenServer.call(__MODULE__, {:transaction, account_id, amount, :debit})
  end

  def balance(account_id) do
    GenServer.call(__MODULE__, {:balance, account_id})
  end

  @impl true
  def init(_opts) do
    case :ets.whereis(@table) do
      :undefined ->
        :ets.new(@table, [:named_table, :public, :set, read_concurrency: true, write_concurrency: true])

      _ ->
        :ok
    end

    {:ok, %{}}
  end

  @impl true
  def handle_call({:open_account, account_id, initial_balance}, _from, state) do
    :ets.insert(@table, {account_id, initial_balance})
    {:reply, :ok, state}
  end

  def handle_call({:balance, account_id}, _from, state) do
    reply =
      case :ets.lookup(@table, account_id) do
        [] -> {:error, :not_found}
        [{^account_id, bal}] -> {:ok, bal}
      end

    {:reply, reply, state}
  end

  def handle_call({:transaction, account_id, amount, kind}, from, state) do
    Task.start(fn ->
      result = run_transaction(account_id, amount, kind)
      GenServer.reply(from, result)
    end)

    {:noreply, state}
  end

  defp run_transaction(account_id, amount, kind) do
    read_result = :ets.lookup(@table, account_id)

    case read_result do
      [] ->
        {:error, :not_found}

      [{^account_id, current}] ->
        case validate_and_apply(current, amount, kind) do
          {:ok, new_balance} ->
            :ets.insert(@table, {account_id, new_balance})
            {:ok, new_balance}

          {:error, _} = err ->
            err
        end
    end
  end

  defp validate_and_apply(current, amount, :credit) do
    new_balance = current + amount

    if new_balance >= 0 do
      {:ok, new_balance}
    else
      {:error, :invalid_amount}
    end
  end

  defp validate_and_apply(current, amount, :debit) do
    if current >= amount do
      {:ok, current - amount}
    else
      {:error, :insufficient_funds}
    end
  end
end

{:ok, _} = BankTransactionServer.start_link([])
:ok = BankTransactionServer.open_account(:acc1, 1000)
{:ok, _} = BankTransactionServer.deposit(:acc1, 50)
{:ok, _} = BankTransactionServer.withdraw(:acc1, 100)
{:ok, bal} = BankTransactionServer.balance(:acc1)

IO.puts("balance=#{bal}")
