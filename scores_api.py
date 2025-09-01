#!/usr/bin/env python3

from flask import Flask, jsonify
from scores_parser import parse_scores24
import os

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"message": "Scores24 API is running!"})

@app.route('/matches/btts')
def get_btts_matches():
    """Возвращает матчи с прогнозом 'Обе забьют'"""
    matches = parse_scores24()
    return jsonify({
        "source": "scores24.live",
        "trend": "Обе забьют (BTTS)",
        "matches": matches,
        "count": len(matches)
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
