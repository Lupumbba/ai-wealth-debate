"""
投资辩论竞技场 - 股票数据获取模块
数据源：Twelve Data API（实时准确数据）
"""

import json
import time
import logging

logger = logging.getLogger(__name__)

# Twelve Data API（免费，无需注册）
TWELVE_DATA_BASE = "https://api.twelvedata.com"
TWELVE_DATA_API_KEY = "demo"  # 免费key，可替换为付费key提升限额


class StockDataFetcher:
    """股票数据获取器（Twelve Data API）"""

    def __init__(self):
        pass

    def fetch(self, symbol: str) -> dict:
        """获取股票数据"""
        try:
            # 并行获取三个端点
            quote = self._fetch_quote(symbol)
            stats = self._fetch_statistics(symbol)
            profile = self._fetch_profile(symbol)

            if not quote or not quote.get("close"):
                return {
                    "symbol": symbol.upper(),
                    "error": f"无法获取 {symbol} 的数据，请检查股票代码是否正确",
                    "data_source": "none",
                }

            # 合并数据
            result = {
                "symbol": symbol.upper(),
                "name": quote.get("name", profile.get("name", symbol)),
                "current_price": round(float(quote.get("close", 0)), 2),
                "market_cap": stats.get("market_capitalization"),
                "pe_ratio": stats.get("trailing_pe"),
                "pb_ratio": stats.get("price_to_book_mrq"),
                "dividend_yield": stats.get("dividend_yield_ttm"),
                "roe": stats.get("return_on_equity_ttm"),
                "debt_to_equity": stats.get("total_debt_to_equity_mrq"),
                "revenue_growth": stats.get("quarterly_revenue_growth"),
                "profit_margin": stats.get("profit_margin"),
                "sector": profile.get("sector", "未知"),
                "industry": profile.get("industry", "未知"),
                "52w_high": quote.get("fifty_two_week_high"),
                "52w_low": quote.get("fifty_two_week_low"),
                "avg_volume": stats.get("avg_10_volume"),
                "beta": stats.get("beta"),
                "3m_change_pct": round(float(quote.get("percent_change", 0)), 2),
                "data_source": "twelve_data",
            }

            # 清理 None 值为 0（方便前端显示）
            for key in ["market_cap", "avg_volume"]:
                if result[key] is None:
                    result[key] = 0

            return result

        except Exception as e:
            logger.error(f"数据获取异常: {e}")
            return {
                "symbol": symbol.upper(),
                "error": f"数据获取失败: {str(e)}",
                "data_source": "none",
            }

    def _api_get(self, endpoint: str, params: dict) -> dict:
        """调用 Twelve Data API"""
        import requests
        params["apikey"] = TWELVE_DATA_API_KEY
        url = f"{TWELVE_DATA_BASE}{endpoint}"
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            else:
                logger.warning(f"Twelve Data API 错误 {r.status_code}: {r.text[:200]}")
                return {}
        except Exception as e:
            logger.warning(f"Twelve Data 请求失败: {e}")
            return {}

    def _fetch_quote(self, symbol: str) -> dict:
        """获取实时报价"""
        data = self._api_get("/quote", {"symbol": symbol})
        return data if isinstance(data, dict) and "close" in data else {}

    def _fetch_statistics(self, symbol: str) -> dict:
        """获取估值和财务指标"""
        data = self._api_get("/statistics", {"symbol": symbol})
        if isinstance(data, dict) and "statistics" in data:
            stats = data["statistics"]
            # 扁平化嵌套结构
            result = {}
            # 估值指标
            vm = stats.get("valuations_metrics", {})
            result["market_capitalization"] = vm.get("market_capitalization")
            result["trailing_pe"] = vm.get("trailing_pe")
            result["forward_pe"] = vm.get("forward_pe")
            result["price_to_book_mrq"] = vm.get("price_to_book_mrq")
            result["dividend_yield_ttm"] = vm.get("dividend_yield_ttm")
            # 财务指标
            fin = stats.get("financials", {})
            result["profit_margin"] = fin.get("profit_margin")
            result["return_on_equity_ttm"] = fin.get("return_on_equity_ttm")
            result["quarterly_revenue_growth"] = fin.get("income_statement", {}).get("quarterly_revenue_growth")
            result["total_debt_to_equity_mrq"] = fin.get("balance_sheet", {}).get("total_debt_to_equity_mrq")
            # 股票统计
            ss = stats.get("stock_statistics", {})
            result["avg_10_volume"] = ss.get("avg_10_volume")
            result["beta"] = ss.get("beta")
            return result
        return {}

    def _fetch_profile(self, symbol: str) -> dict:
        """获取公司信息"""
        data = self._api_get("/profile", {"symbol": symbol})
        if isinstance(data, dict) and "sector" in data:
            return data
        return {}
