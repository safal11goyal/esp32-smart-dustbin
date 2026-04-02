from app import app, HOST, PORT


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
