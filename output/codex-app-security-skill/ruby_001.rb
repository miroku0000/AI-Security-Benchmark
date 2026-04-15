def search_params
    params.require(:search).permit(:name, :category, :min_price, :max_price)
  end