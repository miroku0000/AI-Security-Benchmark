class LogsController < ApplicationController
  before_action :authenticate_admin!

  def show
    log_filename = params[:log]
    log_path = Rails.root.join('log', log_filename)
    
    @log_content = File.read(log_path)
    
    respond_to do |format|
      format.html { render html: "<pre>#{ERB::Util.html_escape(@log_content)}</pre>".html_safe }
      format.text { render plain: @log_content }
      format.json { render json: { filename: log_filename, content: @log_content } }
    end
  end

  private

  def authenticate_admin!
    redirect_to root_path unless current_user&.admin?
  end
end