def create
    sql = params[:query].to_s

    result = ActiveRecord::Base.connection.execute(sql)

    render json: normalize_result(result)
  rescue ActiveRecord::StatementInvalid => e
    render json: { error: e.message }, status: :unprocessable_entity
  end

  private

  def normalize_result(result)
    if result.respond_to?(:to_a)
      result.to_a
    elsif result.respond_to?(:values) && result.respond_to?(:fields)
      result.values.map { |row| result.fields.zip(row).to_h }
    else
      Array(result)
    end
  end
end

Rails.application.routes.draw do
  namespace :webhooks do
    post 'sendgrid/events'
  end

  namespace :admin do
    resources :reports, only: [:create]
  end
  
  root "welcome#index"
end