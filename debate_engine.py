"""
投资辩论竞技场 - AI 分析引擎
使用 DeepSeek API 驱动多个投资角色进行独立分析和辩论
"""

import json
import os
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import openai
from dotenv import load_dotenv

from roles_config import INVESTORS, DEBATE_TOPICS
from stock_data_fetcher import StockDataFetcher

load_dotenv()


class DebateEngine:
    """投资辩论引擎"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._client: Optional[openai.OpenAI] = None
        self._data_fetcher = StockDataFetcher()

    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def _call_model(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 800) -> str:
        """调用 DeepSeek 模型"""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[分析失败: {str(e)}]"

    def fetch_stock_data(self, symbol: str) -> dict:
        """获取股票数据（多数据源自动切换）"""
        return self._data_fetcher.fetch(symbol)

    def analyze_single_investor(self, investor: dict, stock_data: dict) -> dict:
        """单个投资者的独立分析"""
        # 预格式化数值，避免 f-string 中花括号冲突
        market_cap = stock_data.get('market_cap', 0)
        market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"

        stock_summary = f"""
股票：{stock_data.get('name', 'N/A')}（{stock_data.get('symbol', 'N/A')}）
当前价格：${stock_data.get('current_price', 'N/A')}
市值：{market_cap_str}
市盈率(PE)：{stock_data.get('pe_ratio', 'N/A')}
市净率(PB)：{stock_data.get('pb_ratio', 'N/A')}
股息率：{stock_data.get('dividend_yield', 'N/A')}
ROE：{stock_data.get('roe', 'N/A')}
营收增长：{stock_data.get('revenue_growth', 'N/A')}
利润率：{stock_data.get('profit_margin', 'N/A')}
行业：{stock_data.get('sector', 'N/A')} / {stock_data.get('industry', 'N/A')}
52周高/低：${stock_data.get('52w_high', 'N/A')} / ${stock_data.get('52w_low', 'N/A')}
近3个月涨跌幅：{stock_data.get('3m_change_pct', 'N/A')}%
Beta：{stock_data.get('beta', 'N/A')}
""".strip()

        user_prompt = f"请分析以下股票：\n\n{stock_summary}\n\n请用你的投资框架给出独立判断，3-5句话核心观点。"

        analysis = self._call_model(
            system_prompt=investor["system_prompt"],
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=600,
        )

        return {
            "investor_id": investor["id"],
            "name": investor["name"],
            "name_en": investor["name_en"],
            "emoji": investor["emoji"],
            "faction": investor["faction"],
            "faction_color": investor["faction_color"],
            "tagline": investor["tagline"],
            "analysis": analysis.strip(),
        }

    def run_independent_analyses(self, symbol: str) -> dict:
        """并行运行所有投资者的独立分析"""
        stock_data = self.fetch_stock_data(symbol)

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.analyze_single_investor, inv, stock_data): inv
                for inv in INVESTORS
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    inv = futures[future]
                    results.append({
                        "investor_id": inv["id"],
                        "name": inv["name"],
                        "emoji": inv["emoji"],
                        "faction": inv["faction"],
                        "faction_color": inv["faction_color"],
                        "tagline": inv["tagline"],
                        "analysis": f"[分析失败: {str(e)}]",
                    })

        # 按阵营排序
        faction_order = {"价值派": 0, "指数派": 1, "交易派": 2, "杠杆派": 3}
        results.sort(key=lambda x: (faction_order.get(x["faction"], 99), x["investor_id"]))

        return {
            "stock_data": stock_data,
            "analyses": results,
        }

    def run_debate_round(self, topic: dict, analyses: list, round_num: int) -> dict:
        """运行一轮辩论"""
        # 构建辩论上下文
        analyses_text = "\n\n".join([
            f"【{a['emoji']} {a['name']}（{a['faction']}）】：{a['analysis']}"
            for a in analyses
        ])

        debate_prompt = f"""现在进行第{round_num}轮辩论。

辩论议题：{topic['title']}
议题说明：{topic['description']}

以下是各位投资大师的独立分析：

{analyses_text}

现在请模拟一场真实的辩论。要求：
1. 采用"你一句我一句"的交替发言方式（不要每人一段连续说完）
2. 每位大师每次只说1-2句话，可以反驳、赞同、补充
3. 要有交锋感——价值派和交易派应该有观点冲突
4. 保持各自的说话风格和投资哲学
5. 辩论3-4个回合后，给出本轮总结

请用以下格式输出（JSON）：
{{"debate": [
  {{"investor_id": "xxx", "name": "xxx", "emoji": "xxx", "faction": "xxx", "statement": "发言内容"}},
  ...
],
"round_summary": "本轮辩论的核心结论和共识点（2-3句话）"}}

只输出JSON，不要其他内容。"""

        system_prompt = """你是一位资深的投资辩论主持人，能够精准模拟不同投资大师的思维方式、
表达风格和投资哲学。你需要让每位大师保持自己独特的声音，同时让辩论有逻辑、有交锋、有深度。
重要：发言必须是交替的（A说→B反驳→C补充→A回应），不能每人连续说多句。
输出必须是合法的JSON格式。"""

        response = self._call_model(
            system_prompt=system_prompt,
            user_prompt=debate_prompt,
            temperature=0.85,
            max_tokens=2000,
        )

        try:
            # 提取 JSON
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("```", 1)[0]
            debate_data = json.loads(json_str)
            return {
                "topic": topic,
                "round": round_num,
                "statements": debate_data.get("debate", []),
                "round_summary": debate_data.get("round_summary", ""),
            }
        except json.JSONDecodeError:
            return {
                "topic": topic,
                "round": round_num,
                "statements": [],
                "error": "辩论结果解析失败",
                "raw_response": response[:500],
            }

    def generate_final_summary(self, symbol: str, stock_data: dict, debate_results: list) -> str:
        """生成最终总结"""
        all_debates = ""
        for dr in debate_results:
            all_debates += f"\n## 辩论议题：{dr['topic']['title']}\n"
            for stmt in dr.get("statements", []):
                all_debates += f"- {stmt.get('emoji', '')} {stmt.get('name', '')}（{stmt.get('faction', '')}）：{stmt.get('statement', '')}\n"

        summary_prompt = f"""基于以下关于 {stock_data.get('name', symbol)}（{symbol}）的投资辩论，请生成一份结构化总结报告。

股票信息：
{json.dumps(stock_data, ensure_ascii=False, indent=2)}

辩论记录：
{all_debates}

请严格按以下格式输出（使用 Markdown），注意颜色标记：

# 📊 投资辩论总结：{stock_data.get('name', symbol)}（{symbol}）

## 🤝 共识点
（所有阵营都同意的观点，每条用 [积极] 或 [消极] 标记情感倾向）

## ⚔️ 核心分歧
（各阵营的主要分歧，用 [看多] [看空] [中性] 标记每方立场）

## 📈 综合评估
（综合所有视角的评估，利好因素用 [利好] 标记，利空因素用 [利空] 标记）

## ⚠️ 风险提示
（辩论中提到的关键风险，每条风险用 [高风险] [中风险] [低风险] 标记等级）

## 🎯 行动建议
（综合建议，区分短期/中期/长期，每条建议用 [推荐] [观望] [不推荐] 标记操作方向）

## 💡 一句话总结
（用一句话概括最终结论，用 [积极] [谨慎] [消极] 标记整体态度）

颜色标记规则：
- [利好] [推荐] [积极] [看多] = 正面/乐观/建议买入
- [利空] [不推荐] [消极] [看空] [高风险] = 负面/悲观/建议回避
- [观望] [中性] [中风险] [谨慎] = 中性/等待/需要更多信息"""

        system_prompt = """你是一位资深的投资分析师，擅长综合多方观点给出客观、全面的投资分析报告。
你的报告应该结构清晰、逻辑严密、观点平衡，既不过度乐观也不过度悲观。
重要：你必须在每条观点前加上颜色标记如 [利好] [利空] [推荐] [不推荐] [观望] [高风险] [中风险] 等，以便读者快速识别观点倾向。"""

        return self._call_model(
            system_prompt=system_prompt,
            user_prompt=summary_prompt,
            temperature=0.5,
            max_tokens=2000,
        )

    def run_full_debate(self, symbol: str) -> dict:
        """运行完整的辩论流程"""
        # 第一步：独立分析
        analysis_result = self.run_independent_analyses(symbol)

        # 第二步：三轮辩论
        debate_results = []
        for i, topic in enumerate(DEBATE_TOPICS, 1):
            debate_round = self.run_debate_round(topic, analysis_result["analyses"], i)
            debate_results.append(debate_round)

        # 第三步：最终总结
        final_summary = self.generate_final_summary(
            symbol,
            analysis_result["stock_data"],
            debate_results,
        )

        return {
            "symbol": symbol,
            "stock_data": analysis_result["stock_data"],
            "analyses": analysis_result["analyses"],
            "debates": debate_results,
            "final_summary": final_summary,
        }
