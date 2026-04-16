"""
投资辩论竞技场 - 股票数据获取模块
数据源优先级（全部免费，无需 API Key）：
1. Google Finance 爬虫（最准确，实时数据）
2. Yahoo Finance 直接 API（备用）
3. yahooquery（第三备用）
4. yfinance（第四备用）

注意：不使用任何 AI 生成数据，确保所有数据来自真实数据源
"""

import json
import re
import time
import logging

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """多数据源股票数据获取器（纯真实数据，无 AI 兜底）"""

    def __init__(self):
        self.sources = [
            self._fetch_google_finance,
            self._fetch_yahoo_direct,
            self._fetch_yahooquery,
            self._fetch_yfinance,
        ]

    def fetch(self, symbol: str) -> dict:
        """尝试所有数据源，合并最优结果"""
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
                    logger.info(f"✅ {source_name} 成功 → ${result.get('current_price')}")
                else:
                    err = result.get("error", "无数据") if result else "返回空"
                    errors.append(f"{source_name}: {err}")
            except Exception as e:
                errors.append(f"{source_name}: {e}")
                logger.warning(f"{source_name} 异常: {e}")

        if not results:
            return {
                "symbol": symbol.upper(),
                "error": f"所有数据源均失败，请检查网络连接或股票代码是否正确。失败详情: {'; '.join(errors)}",
                "data_source": "none",
            }

        if len(results) == 1:
            return results[0]

        return self._merge_best(results)

    def _merge_best(self, results: list) -> dict:
        """合并多个数据源的最优结果"""
        priority = {"google_finance": 0, "yahoo_direct": 1, "yahooquery": 2, "yfinance": 3}
        results.sort(key=lambda r: priority.get(r["data_source"], 99))
        merged = results[0].copy()

        # 价格交叉验证
        prices = [r["current_price"] for r in results if r.get("current_price")]
        if len(prices) >= 2:
            prices_sorted = sorted(prices)
            median_price = prices_sorted[len(prices_sorted) // 2]
            max_dev = max(abs(p - median_price) / median_price for p in prices)
            if max_dev > 0.05:
                logger.warning(f"价格偏差较大({max_dev:.1%})，使用中位数 ${median_price}")
                merged["current_price"] = round(median_price, 2)

        # 补全缺失字段
        for r in results[1:]:
            for key in ["pe_ratio", "pb_ratio", "dividend_yield", "roe", "revenue_growth",
                         "profit_margin", "beta", "52w_high", "52w_low", "market_cap",
                         "sector", "industry", "debt_to_equity", "avg_volume", "name",
                         "3m_change_pct"]:
                if (merged.get(key) is None or merged.get(key) == 0) and r.get(key):
                    merged[key] = r[key]

        sources = [r["data_source"] for r in results]
        merged["data_source"] = "+".join(sources)
        return merged

    # ===== 数据源 1: Google Finance 爬虫 =====
    def _fetch_google_finance(self, symbol: str) -> dict:
        """爬取 Google Finance 页面获取实时数据（最准确）"""
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 确定 Google Finance 的代码格式
        gf_symbol = symbol
        # 常见美股后缀映射
        if ":" not in symbol and not symbol.endswith(".HK"):
            gf_symbol = f"{symbol}:NASDAQ"

        url = f"https://www.google.com/finance/quote/{gf_symbol}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")

            html = r.text

            # 提取公司名称
            name = self._gf_extract(html, r'<div[^>]*class="[^"]*zzDege"[^>]*>(.*?)</div>')
            if not name:
                name = self._gf_extract(html, r'<h1[^>]*>(.*?)</h1>')

            # 提取当前价格
            price = self._gf_extract(html, r'data-last-price="([^"]+)"')
            if not price:
                price = self._gf_extract(html, r'class="[^"]*YMlKec[^"]*"[^>]*>\s*([\d,]+\.\d+)')

            if not price:
                raise ValueError("无法提取价格")

            # 提取其他数据
            prev_close = self._gf_extract(html, r'Previous close</td><td[^>]*>([\d,]+\.\d+)')
            pe = self._gf_extract(html, r'P/E ratio</td><td[^>]*>([\d,.]+)')
            pb = self._gf_extract(html, r'Price to book</td><td[^>]*>([\d,.]+)')
            dividend = self._gf_extract(html, r'Dividend yield</td><td[^>]*>([\d,.]+)')
            beta = self._gf_extract(html, r'Beta</td><td[^>]*>([\d,.]+)')
            week52_high = self._gf_extract(html, r'Fifty-two week high</td><td[^>]*>([\d,]+\.\d+)')
            week52_low = self._gf_extract(html, r'Fifty-two week low</td><td[^>]*>([\d,]+\.\d+)')
            market_cap = self._gf_extract(html, r'Market cap</td><td[^>]*>([\d.]+[TBMK]?)')

            # 提取板块
            sector = self._gf_extract(html, r'Industry</td><td[^>]*><a[^>]*>(.*?)</a>')

            # 计算涨跌幅
            change_pct = None
            if prev_close and price:
                try:
                    p = float(price.replace(",", ""))
                    pc = float(prev_close.replace(",", ""))
                    change_pct = round((p - pc) / pc * 100, 2)
                except:
                    pass

            return {
                "symbol": symbol.upper(),
                "name": name or symbol,
                "current_price": self._parse_number(price),
                "market_cap": self._parse_market_cap(market_cap),
                "pe_ratio": self._parse_number(pe),
                "pb_ratio": self._parse_number(pb),
                "dividend_yield": self._parse_percent(dividend),
                "beta": self._parse_number(beta),
                "52w_high": self._parse_number(week52_high),
                "52w_low": self._parse_number(week52_low),
                "sector": sector or "未知",
                "industry": sector or "未知",
                "3m_change_pct": change_pct,
            }
        except Exception as e:
            return {"symbol": symbol.upper(), "error": f"google_finance: {e}"}

    def _gf_extract(self, html: str, pattern: str) -> str:
        """从 HTML 中提取第一个匹配"""
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def _parse_number(self, s: str):
        if not s:
            return None
        try:
            return float(s.replace(",", "").replace(" ", ""))
        except:
            return None

    def _parse_percent(self, s: str):
        if not s:
            return None
        try:
            val = float(s.replace("%", "").replace(",", ""))
            return val / 100 if val > 1 else val
        except:
            return None

    def _parse_market_cap(self, s: str):
        if not s:
            return None
        try:
            s = s.replace(",", "").replace(" ", "")
            multipliers = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
            for suffix, mult in multipliers.items():
                if s.upper().endswith(suffix):
                    return float(s[:-1]) * mult
            return float(s)
        except:
            return None

    # ===== 数据源 2: Yahoo Finance 直接 API =====
    def _fetch_yahoo_direct(self, symbol: str) -> dict:
        """直接调用 Yahoo Finance API（无需第三方库）"""
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            # 获取报价
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            data = r.json()
            result = data.get("chart", {}).get("result", [])
            if not result:
                raise ValueError("无数据")
            meta = result[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if not price:
                raise ValueError("无价格")

            # 获取摘要信息
            quote_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=defaultKeyStatistics,financialData,summaryDetail"
            rq = requests.get(quote_url, headers=headers, timeout=12)
            summary = {}
            if rq.status_code == 200:
                sd = rq.json().get("quoteSummary", {}).get("result", [])
                if sd:
                    summary = sd[0]

            fin = summary.get("financialData", {}) or {}
            stats = summary.get("defaultKeyStatistics", {}) or {}
            detail = summary.get("summaryDetail", {}) or {}

            # 计算3个月涨跌幅
            closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            change_3m = 0
            if len(closes) >= 2:
                change_3m = round(((closes[-1] / closes[0]) - 1) * 100, 2)

            return {
                "symbol": symbol.upper(),
                "name": meta.get("longName") or meta.get("shortName") or symbol,
                "current_price": round(float(price), 2),
                "market_cap": meta.get("marketCap"),
                "pe_ratio": self._safe_float(detail.get("trailingPE") or stats.get("trailingPE")),
                "pb_ratio": self._safe_float(stats.get("priceToBook")),
                "dividend_yield": self._safe_float(detail.get("dividendYield")),
                "roe": self._safe_float(fin.get("returnOnEquity")),
                "revenue_growth": self._safe_float(fin.get("revenueGrowth")),
                "profit_margin": self._safe_float(fin.get("profitMargins")),
                "sector": detail.get("sector", "未知"),
                "industry": detail.get("industry", "未知"),
                "52w_high": self._safe_float(detail.get("fiftyTwoWeekHigh")),
                "52w_low": self._safe_float(detail.get("fiftyTwoWeekLow")),
                "beta": self._safe_float(detail.get("beta")),
                "3m_change_pct": change_3m,
            }
        except Exception as e:
            return {"symbol": symbol.upper(), "error": f"yahoo_direct: {e}"}

    # ===== 数据源 3: yahooquery =====
    def _fetch_yahooquery(self, symbol: str) -> dict:
        """yahooquery - Yahoo Finance API 封装"""
        try:
            from yahooquery import Ticker
        except ImportError:
            return {"symbol": symbol.upper(), "error": "yahooquery 未安装"}
        try:
            t = Ticker(symbol)
            price_data = t.price
            if not price_data or not price_data.get("regularMarketPrice"):
                raise ValueError("返回空数据")
            summary = t.summary_detail or {}
            financial_data = t.financial_data or {}
            key_stats = t.key_stats or {}
            hist = t.history(period="3mo")
            return {
                "symbol": symbol.upper(),
                "name": price_data.get("longName") or price_data.get("shortName") or symbol,
                "current_price": round(float(price_data.get("regularMarketPrice", 0)), 2),
                "market_cap": price_data.get("marketCap", 0),
                "pe_ratio": self._safe_float(summary.get("trailingPE")),
                "pb_ratio": self._safe_float(key_stats.get("priceToBook")),
                "dividend_yield": self._safe_float(summary.get("dividendYield")),
                "roe": self._safe_float(financial_data.get("returnOnEquity")),
                "revenue_growth": self._safe_float(financial_data.get("revenueGrowth")),
                "profit_margin": self._safe_float(financial_data.get("profitMargins")),
                "sector": summary.get("sector", "未知"),
                "industry": summary.get("industry", "未知"),
                "52w_high": self._safe_float(price_data.get("fiftyTwoWeekHigh")),
                "52w_low": self._safe_float(price_data.get("fiftyTwoWeekLow")),
                "beta": self._safe_float(key_stats.get("beta")),
                "3m_change_pct": round(((hist["close"].iloc[-1] / hist["close"].iloc[0]) - 1) * 100, 2) if len(hist) > 1 else 0,
            }
        except Exception as e:
            return {"symbol": symbol.upper(), "error": f"yahooquery: {e}"}

    # ===== 数据源 4: yfinance =====
    def _fetch_yfinance(self, symbol: str) -> dict:
        """yfinance - 备用"""
        import yfinance as yf
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if not info or not info.get("regularMarketPrice"):
                raise ValueError("返回空数据")
            hist = ticker.history(period="3mo")
            return {
                "symbol": symbol.upper(),
                "name": info.get("longName") or info.get("shortName") or symbol,
                "current_price": round(float(info.get("currentPrice") or info.get("regularMarketPrice") or 0), 2),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "roe": info.get("returnOnEquity"),
                "revenue_growth": info.get("revenueGrowth"),
                "profit_margin": info.get("profitMargins"),
                "sector": info.get("sector", "未知"),
                "industry": info.get("industry", "未知"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "beta": info.get("beta"),
                "3m_change_pct": round(((hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1) * 100, 2) if len(hist) > 0 else 0,
            }
        except Exception as e:
            return {"symbol": symbol.upper(), "error": f"yfinance: {e}"}

    @staticmethod
    def _safe_float(val):
        if val is None or val == "None" or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
