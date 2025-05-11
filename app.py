from flask import Flask, send_from_directory
from flask_cors import CORS
from routes.ponto import ponto_bp
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='templates')
CORS(app)

# Rotas da API
app.register_blueprint(ponto_bp, url_prefix='/api')

# Rota principal → admin.html
@app.route('/')
def admin():
    return send_from_directory('templates', 'admin.html')

# Rota /funcionario → index.html
@app.route('/funcionario')
def funcionario():
    return send_from_directory('templates', 'index.html')

if __name__ == '__main__':
    porta = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)

