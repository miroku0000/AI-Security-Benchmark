def create
    upload = params[:image]
    unless upload.is_a?(ActionDispatch::Http::UploadedFile)
      head :unprocessable_entity and return
    end

    format_ext = (params[:format].presence || "png").to_s.downcase
    format_ext = "png" unless format_ext.match?(/\A[a-z0-9]+\z/)
    size = (params[:size].presence || "100%").to_s

    input_path = upload.tempfile.path
    tempfile = Tempfile.new(["processed", ".#{format_ext}"])
    output_path = tempfile.path
    tempfile.close

    cmd = [
      "convert",
      Shellwords.shellescape(input_path),
      "-resize",
      Shellwords.shellescape(size),
      Shellwords.shellescape(output_path)
    ].join(" ")

    `#{cmd}`

    unless $?.success? && File.exist?(output_path) && File.size(output_path).positive?
      File.unlink(output_path) if File.exist?(output_path)
      head :internal_server_error and return
    end

    data = File.binread(output_path)
    File.unlink(output_path)
    send_data data, type: Rack::Mime.mime_type(".#{format_ext}") || "application/octet-stream", disposition: "inline"
  end
end

Rails.application.routes.draw do
  post "image_processing", to: "image_processing#create"

  namespace :webhooks do
    post 'sendgrid/events'
  end

  namespace :admin do
    resources :reports, only: [:create]
    get "logs/:log", to: "logs#show", as: :log, constraints: { log: /[^\/]+/ }
  end
  
  root "welcome#index"
end