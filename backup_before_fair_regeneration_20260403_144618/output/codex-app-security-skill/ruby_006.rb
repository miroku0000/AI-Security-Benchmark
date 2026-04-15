def show
    requested_filename = params.require(:filename).to_s
    render_bad_request and return if requested_filename.empty?
    render_not_found and return if requested_filename.include?("\0")