from flask import Flask
from flask_cors import CORS
from config.config import Config
import logging
import config.database as database
import sys

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=True)
sys.stdout.reconfigure(encoding='utf-8')

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

# ✅ Blueprint 라우트는 가장 마지막에 import (순환 참조 방지)
from routes import routes  # 🔥 여기서 import!
app.register_blueprint(routes)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)