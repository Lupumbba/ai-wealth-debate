"""
投资辩论竞技场 - 多数据源股票数据获取模块
数据源优先级：
1. yahooquery（Yahoo Finance API，比 yfinance 更稳定）
2. yfinance（备用）
3. DeepSeek AI（兜底）
"""

import json
import time
import logging

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """多数据源股票数据获取器"""

    def __init__(self):
        self.sources = [
            self._fetch_yahooquery,
            self._fetch_yfinance,
            self._fetch_via_deepseek,
        ]

    def fetch(self, symbol: str) -> dict:
        """尝试所有数据源，交叉验证后返回最可靠结果"""
        errors = []
        results = []

        for i, fetch_fn in enumerate(self.sources):
            source_name = fetch_fn.__name__.replace("_fetch_", "")
            logger.info(f"尝试数据源 {i + 1}/{len(self.sources)}: {source_name}")
            try:
                result = fetch_fn(symbol)
                if result and not result.get("error") and result.get("current_price"):
                    result["data_source"] = source_name
                    results.append(result)
                    logger.info(f"✅ 数据获取成功: {source_name} → ${result.get('current_price')}")
                else:
                    err = result.get("error", "无数据") if result else "返回空"
                    errors.append(f"{source_name}: {err}")
                    logger.warning(f"数据源 {source_name} 失败: {err}")
            except Exception as e:
                errors.append(f"{source_name}: {str(e)}")
                logger.warning(f"数据源 {source_name} 异常: {e}")

        if not results:
            return {"symbol": symbol.upper(), "error": f"所有数据源均失败: {'; '.join(errors)}", "data_source": "none"}

        if len(results) > 1:
            return self._cross_validate(results)
        return results[0]

    def _cross_validate(self, results: list) -> dict:
        """交叉验证：用最可靠的数据源校验价格"""
        # 找到 yahooquery 或 yfinance 作为基准
        primary = None
        secondary = None
        for r in results:
            if r["data_source"] in ("yahooquery", "yfinance") and primary is None:
                primary = r
            elif secondary is None:
                secondary = r

        if not primary:
            primary, secondary = results[0], results[1]

        # 价格校验
        if primary.get("current_price") and secondary.get("current_price"):
            deviation = abs(primary["current_price"] - secondary["current_price"]) / primary["current_price"]
            if deviation > 0.03:  # 偏差超过 3%
                logger.warning(f"价格偏差 {deviation:.1%}: {primary['data_source']}=${primary['current_price']} vs {secondary['data_source']}=${secondary['current_price']}")
                secondary["current_price"] = primary["current_price"]

        # 合并：以 primary 为主体，用 secondary 补充缺失字段
        merged = primary.copy()
        for key in ["pe_ratio", "pb_ratio", "dividend_yield", "roe", "revenue_growth",
                     "profit_margin", "beta", "52w_high", "52w_low", "market_cap", "sector", "industry"]:
            if (merged.get(key) is None or merged.get(key) == 0) and secondary.get(key):
                merged[key] = secondary[key]

        merged["data_source"] = f"{primary['data_source']}(校验)"
        return merged

    # ===== 数据源 1: yahooquery（最稳定） =====
    def _fetch_yahooquery(self, symbol: str) -> dict:
        """yahooquery - 比 yfinance 更稳定的 Yahoo Finance API 封装"""
        try:
            from yahooquery import Ticker
        except ImportError:
            return {"symbol": symbol.upper(), "error": "yahooquery 未安装"}

        try:
            t = Ticker(symbol)
            price_data = t.price
            summary = t.summary_detail
            financial_data = t.financial_data
            key_stats = t.key_stats

            if not price_data or not price_data.get("regularMarketPrice"):
                raise ValueError("yahooquery 返回空数据")

            current_price = price_data.get("regularMarketPrice", 0)
            hist = t.history(period="3mo")

            return {
                "symbol": symbol.upper(),
                "name": price_data.get("longName") or price_data.get("shortName") or symbol,
                "current_price": round(float(current_price), 2),
                "market_cap": price_data.get("marketCap", 0),
                "pe_ratio": self._safe_float(summary.get("trailingPE") or summary.get("forwardPE")),
                "pb_ratio": self._safe_float(key_stats.get("priceToBook")),
                "dividend_yield": self._safe_float(summary.get("dividendYield")),
                "roe": self._safe_float(financial_data.get("returnOnEquity")),
                "debt_to_equity": self._safe_float(key_stats.get("debtToEquity")),
                "revenue_growth": self._safe_float(financial_data.get("revenueGrowth")),
                "profit_margin": self._safe_float(financial_data.get("profitMargins")),
                "sector": summary.get("sector", "未知") or price_data.get("sector", "未知"),
                "industry": summary.get("industry", "未知") or price_data.get("industry", "未知"),
                "52w_high": self._safe_float(price_data.get("fiftyTwoWeekHigh")),
                "52w_low": self._safe_float(price_data.get("fiftyTwoWeekLow")),
                "avg_volume": self._safe_int(price_data.get("averageVolume")),
                "beta": self._safe_float(key_stats.get("beta")),
                "3m_change_pct": round(((hist["close"].iloc[-1] / hist["close"].iloc[0]) - 1) * 100, 2) if len(hist) > 1 else 0,
            }
        except Exception as e:
            return {"symbol": symbol.upper(), "error": f"yahooquery: {e}"}

    # ===== 数据源 2: yfinance（备用） =====
    def _fetch_yfinance(self, symbol: str, max_retries: int = 2) -> dict:
        """yfinance - Yahoo Finance 备用方案"""
        import yfinance as yf

        last_error = None
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="3mo")

                if not info or not info.get("regularMarketPrice"):
                    raise ValueError("yfinance 返回空数据")

                current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
                return {
                    "symbol": symbol.upper(),
                    "name": info.get("longName") or info.get("shortName") or symbol,
                    "current_price": round(current_price, 2),
                    "market_cap": info.get("marketCap", 0),
                    "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                    "pb_ratio": info.get("priceToBook"),
                    "dividend_yield": info.get("dividendYield"),
                    "roe": info.get("returnOnEquity"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "profit_margin": info.get("profitMargins"),
                    "sector": info.get("sector", "未知"),
                    "industry": info.get("industry", "未知"),
                    "52w_high": info.get("fiftyTwoWeekHigh"),
                    "52w_low": info.get("fiftyTwoWeekLow"),
                    "avg_volume": info.get("averageVolume"),
                    "beta": info.get("beta"),
                    "3m_change_pct": round(((hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1) * 100, 2) if len(hist) > 0 else 0,
                }
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
        return {"symbol": symbol.upper(), "error": f"yfinance: {last_error}"}

    # ===== 数据源 3: DeepSeek AI（兜底） =====
    def _fetch_via_deepseek(self, symbol: str) -> dict:
        """通过 DeepSeek AI 获取最新股票数据（最后兜底）"""
        import os
        try:
            import openai
        except ImportError:
            return {"symbol": symbol.upper(), "error": "deepseek: openai 未安装"}

        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            return {"symbol": symbol.upper(), "error": "deepseek: 未配置 API Key"}

        try:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            prompt = f"""请查询股票 {symbol} 的最新财务数据，以 JSON 格式返回。只返回 JSON。

{{
    "name": "公司全称",
    "current_price": 当前股价(数字,美元),
    "market_cap": 市值(数字,美元),
    "pe_ratio": 滚动市盈率(数字),
    "pb_ratio": 市净率(数字),
    "dividend_yield": 年化股息率(小数,如0.005),
    "roe": ROE(小数,如0.45),
    "revenue_growth": 营收同比增长率(小数,如0.08),
    "profit_margin": 净利润率(小数,如0.25),
    "sector": "行业板块",
    "industry": "具体子行业",
    "52w_high": 52周最高价(数字),
    "52w_low": 52周最低价(数字),
    "beta": Beta系数(数字),
    "3m_change_pct": 近3个月涨跌幅(百分比数字)
}}

重要：所有字段必须有值，不要填null！"""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个金融数据助手，只返回纯 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)
            data["symbol"] = symbol.upper()

            if not data.get("current_price"):
                return {"symbol": symbol.upper(), "error": "deepseek: AI 未能获取价格"}

            return data

        except Exception as e:
            return {"symbol": symbol.upper(), "error": f"deepseek: {e}"}

    # ===== 工具方法 =====
    @staticmethod
    def _safe_float(val):
        if val is None or val == "None" or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(val):
        if val is None or val == "None" or val == "":
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None
