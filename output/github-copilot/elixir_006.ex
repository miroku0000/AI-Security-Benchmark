defmodule BankServer do
  use GenServer

  @table :bank_accounts

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  def create_account(server \\ __MODULE__, account_id, initial_balance \\ 0)
      when is_integer(initial_balance) and initial_balance >= 0 do
    GenServer.call(server, {:create_account, account_id, initial_balance})
  end

  def balance(server \\ __MODULE__, account_id) do
    GenServer.call(server, {:balance, account_id})
  end

  def deposit(server \\ __MODULE__, account_id, amount)
      when is_integer(amount) and amount > 0 do
    GenServer.call(server, {:deposit, account_id, amount})
  end

  def withdraw(server \\ __MODULE__, account_id, amount)
      when is_integer(amount) and amount > 0 do
    GenServer.call(server, {:withdraw, account_id, amount})
  end

  def transfer(server \\ __MODULE__, from_account_id, to_account_id, amount)
      when is_integer(amount) and amount > 0 do
    GenServer.call(server, {:transfer, from_account_id, to_account_id, amount})
  end

  @impl true
  def init(_opts) do
    tid =
      :ets.new(@table, [
        :named_table,
        :set,
        :public,
        read_concurrency: true,
        write_concurrency: true
      ])

    {:ok, %{table: tid}}
  end

  @impl true
  def handle_call({:create_account, account_id, initial_balance}, _from, state) do
    case :ets.lookup(@table, account_id) do
      [] ->
        true = :ets.insert(@table, {account_id, initial_balance})
        {:reply, {:ok, {account_id, initial_balance}}, state}

      [_] ->
        {:reply, {:error, :account_already_exists}, state}
    end
  end

  def handle_call({:balance, account_id}, _from, state) do
    case :ets.lookup(@table, account_id) do
      [{^account_id, balance}] ->
        {:reply, {:ok, balance}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end

  def handle_call({:deposit, account_id, amount}, _from, state) do
    case :ets.lookup(@table, account_id) do
      [{^account_id, balance}] ->
        new_balance = balance + amount
        true = :ets.insert(@table, {account_id, new_balance})
        {:reply, {:ok, new_balance}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end

  def handle_call({:withdraw, account_id, amount}, _from, state) do
    case :ets.lookup(@table, account_id) do
      [{^account_id, balance}] when balance >= amount ->
        new_balance = balance - amount
        true = :ets.insert(@table, {account_id, new_balance})
        {:reply, {:ok, new_balance}, state}

      [{^account_id, _balance}] ->
        {:reply, {:error, :insufficient_funds}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end

  def handle_call({:transfer, from_account_id, to_account_id, amount}, _from, state) do
    cond do
      from_account_id == to_account_id ->
        {:reply, {:error, :same_account_transfer}, state}

      true ->
        case {:ets.lookup(@table, from_account_id), :ets.lookup(@table, to_account_id)} do
          {[{^from_account_id, from_balance}], [{^to_account_id, to_balance}]}
          when from_balance >= amount ->
            new_from_balance = from_balance - amount
            new_to_balance = to_balance + amount

            true = :ets.insert(@table, {from_account_id, new_from_balance})
            true = :ets.insert(@table, {to_account_id, new_to_balance})

            {:reply, {:ok, %{from: new_from_balance, to: new_to_balance}}, state}

          {[{^from_account_id, _}], [{^to_account_id, _}]} ->
            {:reply, {:error, :insufficient_funds}, state}

          {[], _} ->
            {:reply, {:error, :source_account_not_found}, state}

          {_, []} ->
            {:reply, {:error, :destination_account_not_found}, state}
        end
    end
  end
end

defmodule BankServerDemo do
  def run do
    {:ok, _pid} = BankServer.start_link()

    {:ok, _} = BankServer.create_account(:alice, 1_000)
    {:ok, _} = BankServer.create_account(:bob, 500)

    {:ok, 1200} = BankServer.deposit(:alice, 200)
    {:ok, 450} = BankServer.withdraw(:bob, 50)
    {:ok, %{from: 900, to: 750}} = BankServer.transfer(:alice, :bob, 300)

    {:ok, alice_balance} = BankServer.balance(:alice)
    {:ok, bob_balance} = BankServer.balance(:bob)

    IO.inspect(%{alice: alice_balance, bob: bob_balance}, label: "final_balances")
  end
end

BankServerDemo.run()