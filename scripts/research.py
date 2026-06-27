#!/usr/bin/env python3
"""
免费API/大模型情报周报调研脚本
每周一自动运行，搜索免费API及大模型的最新动态，生成 Markdown 周报。
"""

import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from duckduckgo_search import DDGS

# Windows GBK 控制台兼容：避免 emoji 报错
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------- 配置 ----------
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# 搜索关键词（每个维度多组变体）
SEARCH_QUERIES = [
    # 中文 - 免费大模型API
    "2026年 免费大模型API 新活动",
    "大模型 Token 免费额度 2026",
    "AI大模型API 免费 新用户 注册送额度",
    "大模型API 限时免费 活动 2026",

    # 中文 - AI服务免费
    "LLM API 免费调用 新平台 2026",
    "AI开放平台 免费额度 最新活动",
    
    # English - global
    "free LLM API 2026 new platform credits",
    "free AI model API tokens 2026 update",
    "ChatGPT API free tier 2026 latest",

    # 已有平台变动
    "阿里通义千问 API 免费额度 更新",
    "百度文心一言 API 免费 2026",
    "OpenAI API 免费额度 change June 2026",
]

# 限免关键词——优先关注
PROMO_KEYWORDS = ["限时免费", "限免", "免费领取", "免费试用", "free trial", "limited time",
                   "新用户", "新人专享", "注册送", "free credits", "free tier"]


def safe_search(ddgs, query: str, max_results: int = 8, retries: int = 2) -> list[dict]:
    """安全搜索，带重试机制，处理异常和空结果。"""
    for attempt in range(1 + retries):
        try:
            results = list(ddgs.text(query, max_results=max_results))
            return results
        except Exception as e:
            if attempt < retries:
                wait = attempt * 3
                print(f"  [RETRY] 搜索失败，{wait}s 后重试 ({attempt}/{retries}): {e}")
                time.sleep(wait)
            else:
                print(f"  [WARN] 搜索失败: {query} → {e}")
                return []
    return []


def extract_platforms_events(results: list[dict]) -> list[dict]:
    """从搜索结果中提取平台名称、活动描述、链接、日期。"""
    items = []
    for r in results:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        text = f"{title} {body}"

        is_promo = any(kw.lower() in text.lower() for kw in PROMO_KEYWORDS)

        # 尝试提取日期
        date = None
        date_patterns = [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{4})-(\d{2})-(\d{2})",
        ]
        for pat in date_patterns:
            m = re.search(pat, text)
            if m:
                date = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
                break

        items.append({
            "title": title.strip()[:120],
            "snippet": body.strip()[:200],
            "url": href,
            "is_promo": is_promo,
            "date": date,
        })
    return items


def run_research() -> str:
    """执行调研，返回报告 Markdown 字符串。"""
    print("=" * 60)
    print("开始免费API/大模型情报调研")
    print(f"时间: {datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    all_platforms = []
    seen_urls = set()

    with DDGS() as ddgs:
        for idx, query in enumerate(SEARCH_QUERIES, 1):
            print(f"\n[{idx}/{len(SEARCH_QUERIES)}] 搜索: {query}")
            results = safe_search(ddgs, query)
            items = extract_platforms_events(results)

            old_count = len(seen_urls)
            for item in items:
                if item["url"] and item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    all_platforms.append(item)

            new_count = len(all_platforms)
            print(f"  → 获取 {len(items)} 条，新增 {new_count - old_count} 条")

    # 去重完成后分类
    promo_items = [p for p in all_platforms if p["is_promo"]]
    normal_items = [p for p in all_platforms if not p["is_promo"]]

    # 按日期排序（有日期在前）
    def sort_key(item):
        return (0 if item["date"] else 1, item["date"] or "")

    promo_items.sort(key=sort_key, reverse=True)
    normal_items.sort(key=sort_key, reverse=True)

    all_sorted = promo_items + normal_items

    # ---------- 生成 Markdown ----------
    lines = []
    beijing = datetime.now(timezone(timedelta(hours=8)))
    date_str = beijing.strftime("%Y-%m-%d")
    weekday_cn = ["一", "二", "三", "四", "五", "六", "日"][beijing.weekday()]

    lines.append(f"# 📡 免费API & 大模型情报周报")
    lines.append(f"")
    lines.append(f"**调研日期**: {date_str} 周{weekday_cn}")
    lines.append(f"")
    lines.append(f"**搜索时间**: {beijing.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    lines.append(f"")
    lines.append(f"**搜索关键词数**: {len(SEARCH_QUERIES)}组")
    lines.append(f"")
    lines.append(f"**去重结果数**: {len(all_sorted)}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    if not all_sorted:
        lines.append("## 📭 本周无更新")
        lines.append("")
        lines.append("本次调研未发现新的免费API平台或重大活动变化。")
        lines.append("")
    else:
        # 限时活动
        if promo_items:
            lines.append("## 🔥 限时活动 / 新用户福利")
            lines.append("")
            for p in promo_items:
                date_tag = f" `[{p['date']}]`" if p["date"] else ""
                lines.append(f"- **{p['title']}**{date_tag}")
                lines.append(f"  - {p['snippet'][:150]}")
                lines.append(f"  - [链接]({p['url']})")
                lines.append("")

        # 所有结果
        lines.append("## 📋 完整搜索结果")
        lines.append("")
        lines.append(f"（共 {len(all_sorted)} 条去重结果，排名不分先后）")
        lines.append("")
        for i, p in enumerate(all_sorted, 1):
            date_tag = f" `[{p['date']}]`" if p["date"] else ""
            tag = " 🔥限时" if p["is_promo"] else ""
            lines.append(f"{i}. **{p['title']}**{date_tag}{tag}")
            lines.append(f"   - {p['snippet'][:150]}")
            lines.append(f"   - [链接]({p['url']})")
            lines.append("")

    # 底部注
    lines.append("---")
    lines.append("")
    lines.append(f"*报告由自动化脚本于 {beijing.strftime('%Y-%m-%d %H:%M')} 生成*")
    lines.append(f"*搜索工具: DuckDuckGo | 数据仅供参考，请以各平台官网为准*")
    lines.append("")

    report = "\n".join(lines)
    total = len(all_sorted)
    print(f"\n== 调研完成，共 {total} 条有效结果 ==")

    return report


def save_report(report: str) -> str:
    """保存报告到 reports/ 目录。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    filename = f"{now.strftime('%Y-%m-%d')}-API周报.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[SAVED] 报告已保存: {filepath}")
    return filepath


def update_index_html():
    """生成 reports/index.html —— 报告目录页"""
    md_files = sorted(
        [f for f in os.listdir(REPORTS_DIR) if f.endswith(".md")],
        reverse=True,
    )
    beijing = datetime.now(timezone(timedelta(hours=8)))
    update_time = beijing.strftime("%Y-%m-%d %H:%M")

    report_items = ""
    if md_files:
        for fname in md_files:
            date_part = fname.split("-API周报")[0] if "-API周报" in fname else fname.replace(".md", "")
            report_items += f'<li class="report-item"><a href="{fname}">{fname}</a><span class="date">{date_part}</span></li>\n'
    else:
        report_items = '<li class="report-item">暂无报告，等待首次运行</li>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>免费API & 大模型情报周报</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f0f2f5;color:#333;min-height:100vh}}
.header{{background:linear-gradient(135deg,#4a90d9,#357abd);color:white;padding:32px 20px;text-align:center}}
.header h1{{font-size:22px;margin-bottom:4px}}
.header p{{font-size:14px;opacity:0.85}}
.container{{max-width:720px;margin:0 auto;padding:16px}}
.card{{background:white;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06)}}
.card h3{{font-size:15px;margin-bottom:12px;color:#555}}
.report-list{{list-style:none;padding:0}}
.report-item{{background:#f8f9fa;margin:6px 0;padding:12px 16px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;transition:transform .1s,background .2s}}
.report-item:hover{{transform:translateX(4px);background:#e3f2fd}}
.report-item a{{color:#4a90d9;text-decoration:none;font-weight:500;font-size:15px}}
.report-item a:hover{{text-decoration:underline}}
.report-item .date{{color:#999;font-size:13px;white-space:nowrap}}
.footer{{text-align:center;color:#aaa;font-size:12px;padding:20px}}
</style>
</head>
<body>
<div class="header">
  <h1>免费API & 大模型情报周报</h1>
  <p>每周一自动调研 | 最后更新: {update_time}</p>
</div>

<div class="container">
  <div class="card">
    <h3>周报列表（{len(md_files)} 期）</h3>
    <ul class="report-list">{report_items}</ul>
  </div>
</div>

<div class="footer">自动运行 · 每周一 08:00 CST | 数据源: DuckDuckGo 搜索</div>
</body>
</html>'''

    index_path = os.path.join(REPORTS_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[SAVED] 目录页已更新: {index_path}")


if __name__ == "__main__":
    report = run_research()
    save_report(report)
    update_index_html()
    print("\n== 全部完成 ==")
