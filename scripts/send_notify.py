#!/usr/bin/env python3
"""Server酱通知发送器 - API周报项目"""
import sys, json, urllib.request, os
from datetime import datetime, timezone, timedelta

SENDKEY = os.environ.get("SERVERCHAN_SENDKEY", "")
if not SENDKEY:
    sys.exit(0)

beijing = datetime.now(timezone(timedelta(hours=8)))
date_str = beijing.strftime("%Y-%m-%d")
page_url = "https://liuruchuan.github.io/api-weekly-reports/"

html = f"<h3>免费API & 大模型情报周报</h3><p><b>日期</b>: {date_str}</p><p><a href='{page_url}'>查看完整报告 →</a></p><br/><hr/><p style='color:#999;font-size:12px;'>每周一 08:00 自动推送</p>"

title = f"API周报 ({date_str})"
payload = json.dumps({"title": title, "desp": html}).encode("utf-8")

req = urllib.request.Request(
    f"https://sctapi.ftqq.com/{SENDKEY}.send",
    data=payload, headers={"Content-Type": "application/json"}, method="POST")
resp = json.loads(urllib.request.urlopen(req).read().decode())
print(f"Notify: code={resp.get('code')} pushid={resp.get('data',{}).get('pushid','?')}")
