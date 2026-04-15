class ProductSearchController < ApplicationController
  def index
    @products = Product.all
    filters = search_params