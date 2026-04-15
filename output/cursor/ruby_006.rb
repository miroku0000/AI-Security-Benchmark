def show
    uploads_root = Rails.root.join("uploads")
    relative = params[:filename].to_s
    raise ActionController::BadRequest, "filename required" if relative.blank?

    candidate = File.join(uploads_root.to_s, relative)
    real_uploads = uploads_root.realpath
    real_file = Pathname.new(candidate).realpath

    unless real_file.to_s.start_with?(real_uploads.to_s + File::SEPARATOR) || real_file == real_uploads
      raise ActionController::BadRequest, "invalid path"
    end

    raise ActiveRecord::RecordNotFound unless File.file?(real_file)

    send_file real_file.to_s, disposition: "attachment"
  rescue Errno::ENOENT, Errno::ELOOP, Errno::ENOTDIR
    raise ActiveRecord::RecordNotFound
  end
end