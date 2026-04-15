def error_response(message, status_code):
    return jsonify({"error": message}), status_code