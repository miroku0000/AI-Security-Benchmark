defp normalize_where_filters(filters) do
    filters
    |> Enum.reject(fn {key, _value} -> key in ["order_by", "order_dir", "limit"] end)
    |> Enum.reduce_while({:ok, []}, fn {key, value}, {:ok, acc} ->
      case normalize_single_filter(key, value) do
        {:ok, nil} -> {:cont, {:ok, acc}}
        {:ok, normalized} -> {:cont, {:ok, [normalized | acc]}}
        {:error, reason} -> {:halt, {:error, reason}}
      end
    end)
    |> case do
      {:ok, filters_list} -> {:ok, Enum.reverse(filters_list)}
      error -> error
    end
  end