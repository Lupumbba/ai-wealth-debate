# 🏛️ 投资辩论竞技场 | Investment Debate Arena

> 让 7 位投资大师为你辩论一只股票——独立分析、激烈交锋、最终给出综合投资建议。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-purple.svg)
![License](https://img.shields.io/badge/License-MIT-orange.svg)

---

## ✨ 功能亮点

- **7 位投资大师同台辩论**：巴菲特、芒格、段永平、博格、日内交易导师、交易信号系统、Naval Ravikant
- **三轮辩论机制**：好生意？→ 好价格？→ 该不该买？
- **聊天框实时展示**：你一句我一句的交替辩论，每轮有总结
- **多数据源自动切换**：yahooquery → yfinance → DeepSeek AI，确保数据可用
- **颜色标签区分**：🟢利好/推荐 🔴利空/不推荐 🟡观望/谨慎
- **白色现代 UI**：清爽的卡片式设计，阵营筛选，响应式布局

---

## 📸 效果预览

### 独立分析（分栏对比）

每位大师从自己的投资哲学出发，给出独立判断。支持按阵营筛选：

| 阵营 | 角色 |
|------|------|
| 🏛️ 价值派 | 巴菲特、芒格、段永平 |
| 📊 指数派 | 约翰·博格 |
| ⚡ 交易派 | 日内交易导师、交易信号系统 |
| 🚀 杠杆派 | Naval Ravikant |

### 辩论现场（聊天框）

大师们围绕三个议题展开激烈辩论，每轮结束后有总结卡片。

### 辩论总结（颜色标签）

最终报告用 🟢🟡🔴 颜色标签区分利好/观望/风险，一目了然。

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/investment-debate-arena.git
cd investment-debate-arena
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

> 💡 **获取 DeepSeek API Key**：访问 [https://platform.deepseek.com](https://platform.deepseek.com) 注册即可获得免费额度。

### 4. 启动服务

```bash
bash start.sh
```

或者手动启动：

```bash
FLASK_DEBUG=false python app.py
```

### 5. 打开浏览器

访问 [http://localhost:5000](http://localhost:5000)，输入股票代码（如 AAPL、TSLA、NVDA），点击"开始辩论"。

---

## 📁 项目结构

```
investment-debate-arena/
├── app.py                    # Flask 主应用（API 路由）
├── debate_engine.py          # AI 辩论引擎（DeepSeek 驱动）
├── roles_config.py           # 7 位投资大师角色配置
├── stock_data_fetcher.py     # 多数据源股票数据获取
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── start.sh                  # 启动脚本
├── .gitignore
├── README.md
├── templates/
│   └── index.html            # 前端页面
└── static/
    ├── css/
    │   └── style.css         # 白色主题样式
    └── js/
        └── app.js            # 前端交互逻辑
```

---

## 🔧 技术架构

### 后端

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | Flask | 轻量级 Python Web 框架 |
| AI 引擎 | DeepSeek API | 驱动 7 位角色的分析和辩论 |
| 数据获取 | yahooquery / yfinance | 多数据源自动切换 |
| 数据兜底 | DeepSeek AI | 前两个数据源失败时用 AI 获取 |

### 前端

| 组件 | 技术 | 说明 |
|------|------|------|
| 页面结构 | HTML5 | 语义化标签 |
| 样式 | CSS3 | 白色主题，卡片式设计，响应式 |
| 交互 | 原生 JavaScript | 无框架依赖，轻量快速 |

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/step1-stock-data` | POST | 获取股票数据 |
| `/api/step2-analyses` | POST | 7 位大师独立分析 |
| `/api/step3-debate` | POST | 单轮辩论（round: 1/2/3） |
| `/api/step4-summary` | POST | 生成最终总结 |
| `/api/analyze` | POST | 一次性完整分析（兼容） |
| `/api/investors` | GET | 获取角色信息 |

---

## 🎭 7 位投资大师

| 角色 | 阵营 | 核心哲学 |
|------|------|---------|
| 🧓 沃伦·巴菲特 | 价值派 | 能力圈、护城河、安全边际、长期持有 |
| 🧠 查理·芒格 | 价值派 | 逆向思考、多元思维模型、避免愚蠢 |
| 🇨🇳 段永平 | 价值派 | 本分、不为清单、买股票就是买公司 |
| 📊 约翰·博格 | 指数派 | 指数基金、成本复利、输家的游戏 |
| ⚡ 日内交易导师 | 交易派 | 价格行为、技术分析、风险管理 |
| 📡 交易信号系统 | 交易派 | 量化信号、机构级综合评判 |
| 🚀 Naval Ravikant | 杠杆派 | 特定知识、无需许可的杠杆、财富创造 |

---

## 📊 数据源说明

系统内置三级数据源自动切换：

1. **yahooquery**（优先）：比 yfinance 更稳定的 Yahoo Finance API 封装，无需 API Key
2. **yfinance**（备用）：经典 Yahoo Finance 数据获取库
3. **DeepSeek AI**（兜底）：当前两个数据源都失败时，通过 AI 从互联网获取最新数据

多个数据源成功时，系统会自动交叉验证价格，偏差超过 3% 时用更可靠的数据源修正。

---

## ⚙️ 配置说明

### 环境变量（.env）

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | ❌ | `https://api.deepseek.com/v1` | API 地址 |
| `DEEPSEEK_MODEL` | ❌ | `deepseek-chat` | 模型名称 |
| `FLASK_PORT` | ❌ | `5000` | 服务端口 |
| `FLASK_HOST` | ❌ | `0.0.0.0` | 监听地址 |
| `FLASK_DEBUG` | ❌ | `false` | 调试模式 |

### 支持的股票代码

- **美股**：AAPL、TSLA、NVDA、GOOGL、MSFT 等
- **港股**：0700.HK（腾讯）、9988.HK（阿里）等
- **其他**：任何 Yahoo Finance 支持的代码

---

## 🛡️ 免责声明

本工具仅供学习和参考用途，不构成任何投资建议。投资有风险，决策需谨慎。所有分析均由 AI 生成，可能存在不准确之处，请结合专业投资顾问的意见做出决策。

---

## 📄 License

MIT License - 自由使用、修改和分发。
