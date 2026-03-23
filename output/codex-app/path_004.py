@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def handle_error(error):
    response = jsonify({"error": error.description})
    response.status_code = error.code
    return response