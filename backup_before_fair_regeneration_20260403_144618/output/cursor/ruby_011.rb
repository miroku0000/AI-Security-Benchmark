def create
    upload = params[:config_file]
    unless upload.is_a?(ActionDispatch::Http::UploadedFile)
      head :unprocessable_entity and return
    end

    @configuration = YAML.load(params[:config_file].read)
    render json: { configuration: @configuration }
  rescue Psych::SyntaxError
    head :unprocessable_entity
  end
end