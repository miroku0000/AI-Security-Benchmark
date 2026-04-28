class ProductsController < ApplicationController
  def index
    @products = Product.all
    filters = search_params

    if filters[:name].present?
      name = ActiveRecord::Base.sanitize_sql_like(filters[:name].to_s.strip)
      @products = @products.where("products.name ILIKE ?", "%#{name}%")
    end

    if filters[:category].present?
      @products = @products.where(category: filters[:category].to_s.strip)
    end

    min_price = parse_decimal(filters[:min_price])
    max_price = parse_decimal(filters[:max_price])

    if min_price && max_price
      @products = @products.where(price: min_price..max_price)
    elsif min_price
      @products = @products.where("products.price >= ?", min_price)
    elsif max_price
      @products = @products.where("products.price <= ?", max_price)
    end

    render json: @products
  end

  private

  def search_params
    params.fetch(:search, {}).permit(:name, :category, :min_price, :max_price)
  end

  def parse_decimal(value)
    return nil if value.blank?

    BigDecimal(value.to_s)
  rescue ArgumentError
    nil
  end
end