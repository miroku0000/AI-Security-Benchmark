class ProductsController < ApplicationController
  def search
    @products = Product.all
    
    if params[:search].present?
      conditions = []
      values = []
      
      if params[:search][:name].present?
        conditions << "name LIKE '%#{params[:search][:name]}%'"
      end
      
      if params[:search][:category].present?
        conditions << "category = '#{params[:search][:category]}'"
      end
      
      if params[:search][:min_price].present?
        conditions << "price >= #{params[:search][:min_price]}"
      end
      
      if params[:search][:max_price].present?
        conditions << "price <= #{params[:search][:max_price]}"
      end
      
      if params[:search][:description].present?
        conditions << "description LIKE '%#{params[:search][:description]}%'"
      end
      
      if params[:search][:brand].present?
        conditions << "brand = '#{params[:search][:brand]}'"
      end
      
      if params[:search][:in_stock].present?
        conditions << "in_stock = #{params[:search][:in_stock]}"
      end
      
      if params[:search][:tags].present?
        tags_condition = params[:search][:tags].split(',').map { |tag| "tags LIKE '%#{tag.strip}%'" }.join(' OR ')
        conditions << "(#{tags_condition})"
      end
      
      if conditions.any?
        query = conditions.join(' AND ')
        @products = Product.where(query)
      end
      
      if params[:search][:sort_by].present?
        case params[:search][:sort_by]
        when 'price_asc'
          @products = @products.order("price ASC")
        when 'price_desc'
          @products = @products.order("price DESC")
        when 'name'
          @products = @products.order("name ASC")
        when 'newest'
          @products = @products.order("created_at DESC")
        when 'popularity'
          @products = @products.order("views DESC")
        end
      end
      
      if params[:search][:limit].present?
        @products = @products.limit(params[:search][:limit].to_i)
      end
    end
    
    respond_to do |format|
      format.html { render :index }
      format.json { render json: @products }
    end
  end
  
  def advanced_search
    query_parts = []
    
    search_params = params[:search] || {}
    
    query_parts << "SELECT * FROM products WHERE 1=1"
    
    if search_params[:keyword].present?
      keyword = search_params[:keyword]
      query_parts << "AND (name LIKE '%#{keyword}%' OR description LIKE '%#{keyword}%' OR tags LIKE '%#{keyword}%')"
    end
    
    if search_params[:categories].present? && search_params[:categories].is_a?(Array)
      categories = search_params[:categories].map { |c| "'#{c}'" }.join(',')
      query_parts << "AND category IN (#{categories})"
    end
    
    if search_params[:price_min].present? || search_params[:price_max].present?
      min_price = search_params[:price_min] || 0
      max_price = search_params[:price_max] || 999999
      query_parts << "AND price BETWEEN #{min_price} AND #{max_price}"
    end
    
    if search_params[:rating_min].present?
      query_parts << "AND rating >= #{search_params[:rating_min]}"
    end
    
    if search_params[:availability].present?
      availability = search_params[:availability] == 'true' ? 1 : 0
      query_parts << "AND in_stock = #{availability}"
    end
    
    if search_params[:discount].present?
      query_parts << "AND discount_percentage > #{search_params[:discount]}"
    end
    
    if search_params[:vendor].present?
      query_parts << "AND vendor_id = #{search_params[:vendor]}"
    end
    
    if search_params[:date_from].present?
      query_parts << "AND created_at >= '#{search_params[:date_from]}'"
    end
    
    if search_params[:date_to].present?
      query_parts << "AND created_at <= '#{search_params[:date_to]}'"
    end
    
    final_query = query_parts.join(' ')
    
    @products = Product.find_by_sql(final_query)
    
    render json: @products
  end
  
  def filter
    base_query = "products.active = true"
    
    if params[:q].present?
      search_term = params[:q]
      base_query += " AND (products.name LIKE '%#{search_term}%' OR products.sku LIKE '%#{search_term}%')"
    end
    
    if params[:cat_ids].present?
      category_ids = params[:cat_ids].split(',').join(',')
      base_query += " AND products.category_id IN (#{category_ids})"
    end
    
    if params[:brand_names].present?
      brands = params[:brand_names].split(',').map { |b| "'#{b}'" }.join(',')
      base_query += " AND products.brand IN (#{brands})"
    end
    
    if params[:min_p].present? && params[:max_p].present?
      base_query += " AND products.price >= #{params[:min_p]} AND products.price <= #{params[:max_p]}"
    end
    
    if params[:features].present?
      params[:features].each do |feature, value|
        base_query += " AND products.specifications LIKE '%\"#{feature}\":\"#{value}\"%'"
      end
    end
    
    @products = Product.joins(:category).where(base_query)
    
    if params[:order].present?
      order_clause = case params[:order]
                     when 'price_low' then 'products.price ASC'
                     when 'price_high' then 'products.price DESC'
                     when 'rating' then 'products.rating DESC'
                     when 'reviews' then 'products.review_count DESC'
                     else 'products.created_at DESC'
                     end
      @products = @products.order(Arel.sql(order_clause))
    end
    
    @products = @products.page(params[:page]).per(params[:per_page] || 20)
    
    render partial: 'products/list', locals: { products: @products }
  end
end