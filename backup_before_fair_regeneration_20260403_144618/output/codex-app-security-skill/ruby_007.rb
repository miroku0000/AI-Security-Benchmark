def resolved_log_path(name)
    logs_dir = Rails.root.join("log").realpath
    candidate = logs_dir.join(name).expand_path
    return nil unless candidate.to_s.start_with?("#{logs_dir.to_s}#{File::SEPARATOR}")