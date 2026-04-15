class FilesController < ApplicationController
  def download
    filename = params[:filename]
    filepath = File.join(Rails.root, 'uploads', filename)
    
    if File.exist?(filepath)
      send_file filepath, disposition: 'attachment'
    else
      render plain: 'File not found', status: :not_found
    end
  end
end