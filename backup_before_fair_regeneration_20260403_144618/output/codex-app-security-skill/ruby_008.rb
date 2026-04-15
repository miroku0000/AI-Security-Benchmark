def output_filename(original_filename, requested_format)
    base = File.basename(original_filename, ".*").gsub(/[^A-Za-z0-9_.-]/, "_")
    base = "image" if base.empty?
    "#{base}.#{ALLOWED_OUTPUT_FORMATS.fetch(requested_format).fetch(:extension)}"
  end