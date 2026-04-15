import os


def main():
    import app as apm_app

    app = apm_app.app
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"))


if __name__ == "__main__":
    main()
