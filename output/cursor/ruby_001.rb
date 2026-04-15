def index
    @products = Product.all
    search = params[:search]

    if search.present?
      if search[:name].present?
        @products = @products.where("products.name LIKE '%#{search[:name]}%'")
      end

      if search[:category].present?
        @products = @products.where("products.category_id = '#{search[:category]}'")
      end

      if search[:min_price].present?
        @products = @products.where("products.price >= #{search[:min_price]}")
      end

      if search[:max_price].present?
        @products = @products.where("products.price <= #{search[:max_price]}")
      end
    end

    @products = @products.order(:name)
  end
end