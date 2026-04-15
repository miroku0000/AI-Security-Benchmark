if field == "credits":
            if not isinstance(value, int) or isinstance(value, bool):
                return jsonify({"error": "credits must be an integer"}), 400
            if value < 0:
                return jsonify({"error": "credits must be non-negative"}), 400
        elif field == "verified_status":
            if not isinstance(value, bool):
                return jsonify({"error": "verified_status must be a boolean"}), 400
        else:
            if not isinstance(value, str):
                return jsonify({"error": f"{field} must be a string"}), 400
            value = value.strip()
            if field in {"email", "username", "account_type"} and not value:
                return jsonify({"error": f"{field} cannot be empty"}), 400
            data[field] = value