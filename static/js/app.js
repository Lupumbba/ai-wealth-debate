/**
 * 投资辩论竞技场 - 前端逻辑（分步请求版）
 * 每一步独立调用 API，实时展示进度
 */

// ===== 全局状态 =====
let currentSymbol = '';
let currentAnalyses = [];
let abortController = null; // 用于取消进行中的请求

// ===== 工具函数 =====
function formatNumber(num, prefix = '', suffix = '') {
    if (num == null || isNaN(num)) return 'N/A';
    const absNum = Math.abs(num);
    if (absNum >= 1e12) return prefix + (num / 1e12).toFixed(2) + 'T' + suffix;
    if (absNum >= 1e9) return prefix + (num / 1e9).toFixed(2) + 'B' + suffix;
    if (absNum >= 1e6) return prefix + (num / 1e6).toFixed(2) + 'M' + suffix;
    return prefix + num.toLocaleString() + suffix;
}

function formatPercent(num) {
    if (num == null || isNaN(num)) return 'N/A';
    return (num >= 0 ? '+' : '') + (num * 100).toFixed(2) + '%';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ===== 搜索 =====
function quickSearch(symbol) {
    document.getElementById('stockInput').value = symbol;
    startAnalysis();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('stockInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startAnalysis();
    });
});

// ===== 进度控制 =====
function setProgress(step, percent, text) {
    for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`step${i}`);
        el.classList.remove('active', 'done');
        if (i < step) el.classList.add('done');
        if (i === step) el.classList.add('active');
    }
    document.getElementById('progressBar').style.width = percent + '%';
    document.getElementById('progressText').textContent = text;
}

function showSection(id) {
    document.getElementById(id).style.display = 'block';
}

function addLog(msg) {
    const el = document.getElementById('progressText');
    el.textContent = msg;
    console.log('[Arena]', msg);
}

// ===== API 请求封装（支持中断） =====
async function apiPost(url, body) {
    // 如果有旧的控制器，先中止
    if (abortController) {
        abortController.abort();
    }
    abortController = new AbortController();

    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortController.signal,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || '请求失败');
    return data;
}

// ===== 中断当前分析 =====
function cancelCurrentAnalysis() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    const btn = document.getElementById('analyzeBtn');
    btn.disabled = false;
    btn.querySelector('span:last-child').textContent = '开始辩论';
}

// ===== 主分析流程（分步，支持中断切换） =====
async function startAnalysis() {
    const input = document.getElementById('stockInput');
    const symbol = input.value.trim().toUpperCase();
    if (!symbol) { input.focus(); return; }

    // 中断之前的分析
    cancelCurrentAnalysis();

    currentSymbol = symbol;
    const btn = document.getElementById('analyzeBtn');
    btn.disabled = true;
    btn.querySelector('span:last-child').textContent = '分析中...';

    // 清除之前的错误提示
    document.querySelectorAll('.error-toast').forEach(el => el.remove());

    // 显示进度，隐藏旧结果
    document.getElementById('progressSection').style.display = 'block';
    ['stockInfoSection', 'analysisSection', 'debateSection', 'summarySection'].forEach(id => {
        document.getElementById(id).style.display = 'none';
    });
    document.getElementById('debateRounds').innerHTML = '';

    try {
        // ===== 第1步：获取股票数据 =====
        setProgress(1, 5, `📊 正在获取 ${symbol} 的实时数据...`);
        addLog(`正在连接 Yahoo Finance 获取 ${symbol} 数据...`);

        const step1 = await apiPost('/api/step1-stock-data', { symbol });
        renderStockInfo(step1.stock_data);
        setProgress(1, 15, `✅ 数据获取完成`);
        addLog(`${step1.stock_data.name || symbol} 数据获取成功`);
        await sleep(400);

        // ===== 第2步：7位大师独立分析 =====
        setProgress(2, 20, `🧠 巴菲特正在分析...`);
        addLog('开始独立分析（7位大师并行思考中）...');

        const step2 = await apiPost('/api/step2-analyses', { symbol });
        currentAnalyses = step2.analyses;
        renderAnalyses(currentAnalyses);
        setProgress(2, 50, `✅ 7位大师分析完成`);
        addLog('独立分析全部完成');
        await sleep(400);

        // ===== 第3步：三轮辩论（聊天框实时展示） =====
        const debateTopics = ['好生意？', '好价格？', '该不该买？'];
        showSection('debateSection'); // 先显示辩论区域
        const chatWelcome = document.getElementById('chatWelcome');
        if (chatWelcome) chatWelcome.remove();

        for (let i = 1; i <= 3; i++) {
            setProgress(3, 50 + (i - 1) * 12, `⚔️ 辩论第${i}轮：${debateTopics[i - 1]}`);
            addLog(`正在进行第${i}轮辩论：${debateTopics[i - 1]}`);

            const step3 = await apiPost('/api/step3-debate', { symbol, round: i });
            appendDebateRound(step3);
            setProgress(3, 50 + i * 12, `✅ 第${i}轮辩论完成`);
            await sleep(300);
        }

        // ===== 第4步：生成总结 =====
        setProgress(4, 90, `📋 正在生成总结报告...`);
        addLog('综合所有观点，生成最终报告...');

        const step4 = await apiPost('/api/step4-summary', { symbol });
        renderSummary(step4.summary);
        setProgress(4, 100, `🎉 分析完成！`);
        addLog('全部完成！');

        // 滚动到总结
        setTimeout(() => {
            document.getElementById('summarySection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 500);

    } catch (error) {
        // 忽略用户主动中断的错误
        if (error.name === 'AbortError') {
            console.log('[Arena] 分析已中断（用户切换股票）');
            return;
        }
        console.error('分析失败:', error);
        addLog(`❌ 失败: ${error.message}`);
        setProgress(1, 0, `❌ ${error.message}`);

        // 在页面上显示错误
        const errDiv = document.createElement('div');
        errDiv.className = 'error-toast';
        errDiv.style.cssText = 'max-width:700px;margin:20px auto;padding:16px;background:#2a1a1a;border:1px solid #dc2626;border-radius:12px;color:#fca5a5;';
        errDiv.innerHTML = `<strong>❌ 分析失败</strong><br>${escapeHtml(error.message)}<br><br><small>提示：请检查 DeepSeek API Key 是否正确配置</small>`;
        document.getElementById('progressSection').after(errDiv);
    } finally {
        btn.disabled = false;
        btn.querySelector('span:last-child').textContent = '开始辩论';
    }
}

// ===== 渲染股票信息 =====
function renderStockInfo(data) {
    document.getElementById('stockName').textContent = data.name || data.symbol;
    document.getElementById('stockSymbol').textContent = data.symbol;
    document.getElementById('stockSector').textContent = [data.sector, data.industry].filter(Boolean).join(' / ');

    if (data.error) {
        document.getElementById('stockMetrics').innerHTML = `
            <div class="metric-item" style="grid-column:1/-1;text-align:center;color:var(--accent-red);">
                ⚠️ 数据获取失败: ${escapeHtml(data.error)}
            </div>`;
    } else {
        const priceChange = data['3m_change_pct'];
        const metrics = [
            { label: '当前价格', value: data.current_price ? `$${data.current_price}` : 'N/A' },
            { label: '市值', value: formatNumber(data.market_cap, '$') },
            { label: '市盈率 PE', value: data.pe_ratio != null ? data.pe_ratio.toFixed(2) : 'N/A' },
            { label: '市净率 PB', value: data.pb_ratio != null ? data.pb_ratio.toFixed(2) : 'N/A' },
            { label: '股息率', value: formatPercent(data.dividend_yield) },
            { label: 'ROE', value: formatPercent(data.roe) },
            { label: '营收增长', value: formatPercent(data.revenue_growth) },
            { label: '利润率', value: formatPercent(data.profit_margin) },
            { label: '52周高', value: data['52w_high'] ? `$${data['52w_high']}` : 'N/A' },
            { label: '52周低', value: data['52w_low'] ? `$${data['52w_low']}` : 'N/A' },
            { label: '3月涨跌', value: priceChange != null ? `${priceChange >= 0 ? '+' : ''}${priceChange}%` : 'N/A',
              cls: priceChange > 0 ? 'positive' : (priceChange < 0 ? 'negative' : '') },
            { label: 'Beta', value: data.beta != null ? data.beta.toFixed(2) : 'N/A' },
        ];
        document.getElementById('stockMetrics').innerHTML = metrics.map(m => `
            <div class="metric-item">
                <div class="metric-label">${m.label}</div>
                <div class="metric-value ${m.cls || ''}">${m.value}</div>
            </div>
        `).join('');
    }
    showSection('stockInfoSection');
}

// ===== 渲染独立分析 =====
function renderAnalyses(analyses) {
    const grid = document.getElementById('analysisGrid');
    grid.innerHTML = analyses.map((a, i) => `
        <div class="analysis-card" style="--card-color: ${a.faction_color}; animation-delay: ${i * 0.08}s;"
             data-faction="${a.faction}">
            <div class="card-header">
                <div class="card-avatar">${a.emoji}</div>
                <div class="card-info">
                    <div class="card-name">${escapeHtml(a.name)}
                        <span class="card-faction" style="background: ${a.faction_color}">${a.faction}</span>
                    </div>
                    <div class="card-name-en">${escapeHtml(a.name_en)}</div>
                </div>
            </div>
            <div class="card-tagline">"${escapeHtml(a.tagline)}"</div>
            <div class="card-analysis">${escapeHtml(a.analysis)}</div>
        </div>
    `).join('');
    showSection('analysisSection');
}

// ===== 阵营筛选 =====
function filterFaction(faction) {
    document.querySelectorAll('.faction-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.faction === faction);
    });
    document.querySelectorAll('.analysis-card').forEach(card => {
        card.style.display = (faction === 'all' || card.dataset.faction === faction) ? 'block' : 'none';
    });
}

// ===== 追加辩论轮次（聊天框形式） =====
function appendDebateRound(round) {
    const container = document.getElementById('debateRounds');

    // 议题横幅
    const banner = document.createElement('div');
    banner.className = 'chat-topic-banner';
    banner.innerHTML = `
        <span class="topic-num">${round.round}</span>
        <span>${escapeHtml(round.topic.title)}</span>
        <span class="topic-desc">${escapeHtml(round.topic.description)}</span>
    `;
    container.appendChild(banner);

    // 消息列表
    const messages = document.createElement('div');
    messages.className = 'chat-messages';

    (round.statements || []).forEach((stmt, si) => {
        const msg = document.createElement('div');
        msg.className = 'chat-msg';
        msg.style.animationDelay = `${si * 0.1}s`;
        msg.innerHTML = `
            <div class="chat-avatar" style="--msg-color: ${getFactionColor(stmt.faction)}">${stmt.emoji || '🗣️'}</div>
            <div class="chat-bubble">
                <div class="chat-bubble-header">
                    <span class="chat-bubble-name">${escapeHtml(stmt.name)}</span>
                    <span class="chat-bubble-faction" style="background: ${getFactionColor(stmt.faction)}">${escapeHtml(stmt.faction || '')}</span>
                </div>
                <div class="chat-bubble-text">${escapeHtml(stmt.statement)}</div>
            </div>
        `;
        messages.appendChild(msg);
    });

    if (round.error) {
        const errMsg = document.createElement('div');
        errMsg.style.cssText = 'padding: 10px 16px; color: var(--red); font-size: 13px;';
        errMsg.textContent = `⚠️ ${round.error}`;
        messages.appendChild(errMsg);
    }

    container.appendChild(messages);

    // 本轮总结卡片
    if (round.round_summary) {
        const summary = document.createElement('div');
        summary.className = 'chat-round-summary';
        summary.innerHTML = `
            <div class="round-summary-icon">📝</div>
            <div class="round-summary-content">
                <div class="round-summary-title">第${round.round}轮总结</div>
                <div class="round-summary-text">${escapeHtml(round.round_summary)}</div>
            </div>
        `;
        container.appendChild(summary);
    }

    // 分隔线（如果不是最后一轮）
    if (round.round < 3) {
        const divider = document.createElement('div');
        divider.className = 'chat-divider';
        divider.textContent = '─── 下一轮辩论 ───';
        container.appendChild(divider);
    }

    // 自动滚动到底部
    container.scrollTop = container.scrollHeight;
}

// ===== 渲染辩论（全量，兼容旧接口） =====
function renderDebates(debates) {
    const container = document.getElementById('debateRounds');
    container.innerHTML = '';
    debates.forEach(d => appendDebateRound(d));
    showSection('debateSection');
}

function getFactionColor(faction) {
    const colors = { '价值派': '#2563eb', '指数派': '#16a34a', '交易派': '#dc2626', '杠杆派': '#9333ea' };
    return colors[faction] || '#6b7280';
}

// ===== 渲染总结 =====
function renderSummary(markdown) {
    const container = document.getElementById('summaryContent');

    // 颜色标记映射
    const positiveTags = ['利好', '推荐', '积极', '看多', '买入', '低风险'];
    const negativeTags = ['利空', '不推荐', '消极', '看空', '卖出', '高风险', '回避'];
    const neutralTags = ['观望', '中性', '中风险', '谨慎', '持有', '等待'];

    function replaceTag(match, tag) {
        const tagText = tag.replace('[', '').replace(']', '');
        let cls = 'tag-neutral';
        if (positiveTags.some(t => tagText.includes(t))) cls = 'tag-positive';
        else if (negativeTags.some(t => tagText.includes(t))) cls = 'tag-negative';
        else if (neutralTags.some(t => tagText.includes(t))) cls = 'tag-neutral';
        return `<span class="${cls}">${tagText}</span>`;
    }

    // 先替换颜色标记，再做 Markdown 转换
    let html = markdown.replace(/\[([^\]]+)\]/g, replaceTag);

    // Markdown 转 HTML
    html = html
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/((?:<li>[\s\S]*?<\/li>\s*)+)/g, '<ul>$1</ul>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');

    container.innerHTML = html;
    showSection('summarySection');
}
