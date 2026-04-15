"""
投资辩论竞技场 - Flask Web 应用
分步 API 设计，每步独立调用，前端实时展示进度
"""

import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from debate_engine import DebateEngine
from roles_config import INVESTORS, DEBATE_TOPICS, FACTION_COLORS

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

engine = DebateEngine()

# 内存中缓存分析会话（简单实现）
_sessions = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/investors")
def get_investors():
    """获取所有投资者角色信息"""
    return jsonify({
        "investors": [
            {
                "id": inv["id"],
                "name": inv["name"],
                "name_en": inv["name_en"],
                "emoji": inv["emoji"],
                "faction": inv["faction"],
                "faction_color": inv["faction_color"],
                "tagline": inv["tagline"],
                "philosophy": inv["philosophy"],
                "style": inv["style"],
            }
            for inv in INVESTORS
        ],
        "factions": FACTION_COLORS,
        "debate_topics": DEBATE_TOPICS,
    })


@app.route("/api/step1-stock-data", methods=["POST"])
def step1_stock_data():
    """第1步：获取股票数据"""
    data = request.get_json()
    symbol = data.get("symbol", "").strip().upper()
    if not symbol:
        return jsonify({"error": "请输入股票代码"}), 400

    stock_data = engine.fetch_stock_data(symbol)
    session_id = symbol
    _sessions[session_id] = {"stock_data": stock_data}
    return jsonify({"symbol": symbol, "stock_data": stock_data})


@app.route("/api/step2-analyses", methods=["POST"])
def step2_analyses():
    """第2步：7位大师独立分析"""
    data = request.get_json()
    symbol = data.get("symbol", "").strip().upper()

    if symbol not in _sessions:
        return jsonify({"error": "请先获取股票数据"}), 400

    stock_data = _sessions[symbol]["stock_data"]
    analyses = []
    for inv in INVESTORS:
        result = engine.analyze_single_investor(inv, stock_data)
        analyses.append(result)

    # 按阵营排序
    faction_order = {"价值派": 0, "指数派": 1, "交易派": 2, "杠杆派": 3}
    analyses.sort(key=lambda x: (faction_order.get(x["faction"], 99), x["investor_id"]))

    _sessions[symbol]["analyses"] = analyses
    return jsonify({"analyses": analyses})


@app.route("/api/step3-debate", methods=["POST"])
def step3_debate():
    """第3步：三轮辩论"""
    data = request.get_json()
    symbol = data.get("symbol", "").strip().upper()
    round_num = data.get("round", 1)

    if symbol not in _sessions or "analyses" not in _sessions[symbol]:
        return jsonify({"error": "请先完成独立分析"}), 400

    analyses = _sessions[symbol]["analyses"]
    topic = DEBATE_TOPICS[round_num - 1]
    debate_round = engine.run_debate_round(topic, analyses, round_num)

    if "debates" not in _sessions[symbol]:
        _sessions[symbol]["debates"] = []
    _sessions[symbol]["debates"].append(debate_round)

    return jsonify(debate_round)


@app.route("/api/step4-summary", methods=["POST"])
def step4_summary():
    """第4步：生成最终总结"""
    data = request.get_json()
    symbol = data.get("symbol", "").strip().upper()

    if symbol not in _sessions:
        return jsonify({"error": "会话不存在"}), 400

    session = _sessions[symbol]
    summary = engine.generate_final_summary(
        symbol,
        session.get("stock_data", {}),
        session.get("debates", []),
    )

    return jsonify({"summary": summary})


@app.route("/api/analyze", methods=["POST"])
def analyze_all():
    """一次性运行完整分析（保留兼容）"""
    data = request.get_json()
    symbol = data.get("symbol", "").strip().upper()
    if not symbol:
        return jsonify({"error": "请输入股票代码"}), 400

    try:
        result = engine.run_full_debate(symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
