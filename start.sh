#!/bin/bash
# 投资辩论竞技场 - 启动脚本

cd "$(dirname "$0")"

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，从 .env.example 复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入你的 DEEPSEEK_API_KEY"
    exit 1
fi

# 检查 API Key
source .env
if [ "$DEEPSEEK_API_KEY" = "your_deepseek_api_key_here" ] || [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  请先在 .env 文件中设置 DEEPSEEK_API_KEY"
    exit 1
fi

PORT=${FLASK_PORT:-5000}

echo "🏛️  投资辩论竞技场启动中..."
echo "📍 访问地址: http://localhost:$PORT"
echo ""
FLASK_DEBUG=false python app.py
