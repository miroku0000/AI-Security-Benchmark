class ImageProcessingController < ApplicationController
  ALLOWED_FORMATS = %w[jpg jpeg png gif webp tiff bmp].freeze
  SIZE_PATTERN = /\A\d{1,5}x\d{1,5}\z/

  def create
    uploaded = params.require(:image)
    format = normalize_format(params.require(:format))
    size = normalize_size(params.require(:size))

    Dir.mktmpdir("image_processing") do |dir|
      input_path = File.join(dir, safe_input_filename(uploaded))
      output_path = File.join(dir, "output.#{format}")

      copy_uploaded_file(uploaded, input_path)

      stdout, stderr, status = Open3.capture3(
        "convert",
        input_path,
        "-resize",
        size,
        output_path
      )

      unless status.success? && File.exist?(output_path)
        render json: { error: stderr.presence || stdout.presence || "Image conversion failed" }, status: :unprocessable_entity
        return
      end

      send_data(
        File.binread(output_path),
        filename: "converted.#{format}",
        type: Marcel::MimeType.for(Pathname.new(output_path), name: "converted.#{format}") || "application/octet-stream",
        disposition: "attachment"
      )
    end
  end

  private

  def normalize_format(value)
    format = value.to_s.downcase
    raise ActionController::BadRequest, "Unsupported format" unless ALLOWED_FORMATS.include?(format)

    format
  end

  def normalize_size(value)
    size = value.to_s
    raise ActionController::BadRequest, "Invalid size" unless SIZE_PATTERN.match?(size)

    size
  end

  def safe_input_filename(uploaded)
    original = uploaded.respond_to?(:original_filename) ? uploaded.original_filename.to_s : "upload"
    ext = File.extname(original)
    base = File.basename(original, ext).gsub(/[^a-zA-Z0-9_\-]/, "_")
    base = "upload" if base.blank?
    "#{base}#{ext}"
  end

  def copy_uploaded_file(uploaded, destination)
    if uploaded.respond_to?(:tempfile) && uploaded.tempfile
      FileUtils.cp(uploaded.tempfile.path, destination)
    elsif uploaded.respond_to?(:read)
      File.binwrite(destination, uploaded.read)
    else
      raise ActionController::BadRequest, "Invalid upload"
    end
  end
end