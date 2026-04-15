defmodule BankServer do
  use GenServer

  # Client API

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def create_account(account_id, initial_balance) when initial_balance >= 0 do
    GenServer.call(__MODULE__, {:create_account, account_id, initial_balance})
  end

  def get_balance(account_id) do
    GenServer.call(__MODULE__, {:get_balance, account_id})
  end

  def deposit(account_id, amount) when amount > 0 do
    GenServer.call(__MODULE__, {:deposit, account_id, amount})
  end

  def withdraw(account_id, amount) when amount > 0 do
    GenServer.call(__MODULE__, {:withdraw, account_id, amount})
  end

  def transfer(from_account, to_account, amount) when amount > 0 do
    GenServer.call(__MODULE__, {:transfer, from_account, to_account, amount})
  end

  # Server Callbacks

  @impl true
  def init(_opts) do
    table = :ets.new(:bank_accounts, [:set, :named_table, :protected])
    {:ok, %{table: table}}
  end

  @impl true
  def handle_call({:create_account, account_id, initial_balance}, _from, state) do
    case :ets.lookup(:bank_accounts, account_id) do
      [] ->
        :ets.insert(:bank_accounts, {account_id, initial_balance})
        {:reply, {:ok, initial_balance}, state}

      _ ->
        {:reply, {:error, :account_exists}, state}
    end
  end

  def handle_call({:get_balance, account_id}, _from, state) do
    case :ets.lookup(:bank_accounts, account_id) do
      [{^account_id, balance}] ->
        {:reply, {:ok, balance}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end

  def handle_call({:deposit, account_id, amount}, _from, state) do
    case :ets.lookup(:bank_accounts, account_id) do
      [{^account_id, balance}] ->
        new_balance = balance + amount
        :ets.insert(:bank_accounts, {account_id, new_balance})
        {:reply, {:ok, new_balance}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end

  def handle_call({:withdraw, account_id, amount}, _from, state) do
    case :ets.lookup(:bank_accounts, account_id) do
      [{^account_id, balance}] when balance >= amount ->
        new_balance = balance - amount
        :ets.insert(:bank_accounts, {account_id, new_balance})
        {:reply, {:ok, new_balance}, state}

      [{^account_id, _balance}] ->
        {:reply, {:error, :insufficient_funds}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end

  def handle_call({:transfer, from_account, to_account, amount}, _from, state) do
    with [{^from_account, from_balance}] when from_balance >= amount <-
           :ets.lookup(:bank_accounts, from_account),
         [{^to_account, to_balance}] <- :ets.lookup(:bank_accounts, to_account) do
      :ets.insert(:bank_accounts, {from_account, from_balance - amount})
      :ets.insert(:bank_accounts, {to_account, to_balance + amount})
      {:reply, {:ok, %{from: from_balance - amount, to: to_balance + amount}}, state}
    else
      [{_, _balance}] ->
        {:reply, {:error, :insufficient_funds}, state}

      [] ->
        {:reply, {:error, :account_not_found}, state}
    end
  end
end