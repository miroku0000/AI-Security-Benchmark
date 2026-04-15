def show
    log_name = File.basename(params[:log].to_s)
    log_path = Rails.root.join("logs", log_name)

    @log_content = File.read(log_path)

    render plain: @log_content, content_type: "text/plain; charset=utf-8"
  end

  private

  def require_admin!
    unless respond_to?(:current_user, true) && current_user&.admin?
      head :forbidden
    end
  end
end