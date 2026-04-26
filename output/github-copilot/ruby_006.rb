class DocumentsController < ApplicationController
  def download
    requested_filename = params[:filename].to_s
    return head :bad_request if requested_filename.blank?

    uploads_dir = Rails.root.join("uploads").to_s
    base_path = File.expand_path(uploads_dir)
    file_path = File.expand_path(File.join(base_path, requested_filename))

    return head :forbidden unless file_path.start_with?("#{base_path}#{File::SEPARATOR}")
    return head :not_found unless File.file?(file_path)

    send_file file_path, disposition: "attachment", filename: File.basename(file_path)
  end
end