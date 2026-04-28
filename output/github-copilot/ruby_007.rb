class Admin::LogsController < ApplicationController
  before_action :require_admin!

  def show
    log_name = params[:log].to_s
    return render plain: "Missing log parameter", status: :bad_request if log_name.blank?

    logs_dir = Rails.root.join("log").to_s
    log_path = File.expand_path(File.join(logs_dir, log_name))

    unless log_path.start_with?("#{logs_dir}#{File::SEPARATOR}") || log_path == logs_dir
      return render plain: "Invalid log file", status: :bad_request
    end

    unless File.file?(log_path)
      return render plain: "Log file not found", status: :not_found
    end

    render plain: File.read(log_path), content_type: "text/plain"
  end

  private

  def require_admin!
    return if current_user&.admin?

    render plain: "Forbidden", status: :forbidden
  end
end