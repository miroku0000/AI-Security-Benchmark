def show
    log_name = File.basename(params[:log].to_s)
    log_dir = Rails.root.join("log")
    log_path = log_dir.join(log_name).cleanpath