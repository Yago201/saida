# backend/app.py
from flask import Flask
from flask_cors import CORS
from routes.ponto import ponto_bp
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Registrar blueprints
app.register_blueprint(ponto_bp, url_prefix='/api')

if __name__ == '__main__':
    porta = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
