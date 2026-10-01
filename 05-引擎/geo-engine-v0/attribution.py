"""GEO 归因核对器（P2-6）：发布台账 × 监测台账 → 谁的内容真被 AI 引用了。

原理：监测台账（基线记录表 schema）的 citations 列记录了 AI 回答引用的来源 URL；
本工具把它与发布台账（templates/归因台账-模板.csv）做 URL/域名匹配，输出：
  ① 被引用清单（对应发布条目 + 出现在哪个平台哪次采集 + 首见日期 + 证据 run_id）
  ② 未被引用清单（内容优化线索）
  ③ 可选 --fill 回填台账的被引用三列（cited_by_ai / first_seen_date / evidence）

用法：
  python3 attribution.py --book 台账.csv --ledger output/ledger_doubao_*.csv [more.csv ...] [--fill 回填.csv]

匹配口径（v0 宽松两级）：
  A 级=规范化后 URL 全等（去 scheme/www/尾斜杠）；B 级=注册域相同（如 mp.weixin.qq.com 与
  www.qq.com 不会互认，mp.weixin.qq.com 之间互认）。B 级匹配在报告中标注"域名级"。
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SUFFIX2 = {"com", "net", "org", "gov", "edu", "int", "ac"}


def registrable(host: str) -> str:
    labels = host.lower().split(".")
    if len(labels) >= 3 and labels[-1] in ("cn", "hk", "tw", "jp") and labels[-2] in SUFFIX2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host.lower()


def norm_url(u: str) -> str:
    u = u.strip().rstrip(".,;；，、）)")
    p = urlparse(u if "://" in u else "https://" + u)
    host = (p.netloc or "").lower().removeprefix("www.")
    path = p.path.rstrip("/") or ""
    return host + path


def urls_from_citations(cell: str) -> list[str]:
    out = []
    for tok in re.split(r"[;\s]+", cell or ""):
        tok = tok.strip()
        if tok.startswith("http") or (tok and "." in tok and "/" in tok):
            out.append(tok)
    return out


def load_csv(path: str) -> list[dict]:
    f = Path(path)
    if not f.exists():
        sys.exit(f"[错误] 找不到文件：{path}")
    with f.open(newline="", encoding="utf-8-sig") as fh:
        return [r for r in csv.DictReader(fh) if any((v or "").strip() for v in r.values())]


def main():
    ap = argparse.ArgumentParser(description="归因核对：发布台账 × 监测台账")
    ap.add_argument("--book", required=True, help="发布台账 CSV（归因台账-模板 schema）")
    ap.add_argument("--ledger", nargs="+", required=True, help="监测台账 CSV（可多个）")
    ap.add_argument("--fill", default="", help="可选：回填后的台账输出路径")
    ap.add_argument("--outdir", default="output/attribution")
    a = ap.parse_args()

    book = load_csv(a.book)
    if not book:
        sys.exit("[错误] 发布台账为空")
    # 监测侧索引：规范化URL/注册域 → [(platform, qid, run_id, date, exact_url)]
    url_hits, dom_hits = defaultdict(list), defaultdict(list)
    n_rows = n_cites = 0
    for row in load_rows_safe(a.ledger):
        n_rows += 1
        plat = (row.get("platform") or "").strip()
        qid = (row.get("qid") or "").strip()
        rid = (row.get("run_id") or "").strip()
        day = (row.get("collected_at") or "")[:10]
        for u in urls_from_citations(row.get("citations", "")):
            n_cites += 1
            nu, dom = norm_url(u), registrable(urlparse(u if "://" in u else "https://" + u).netloc)
            hit = (plat, qid, rid, day, u)
            url_hits[nu].append(hit)
            dom_hits[dom].append(hit)

    lines = ["# 归因核对报告", "",
             f"> 监测侧：{n_rows} 行采集 / {n_cites} 条引用来源 ｜ 生成：{datetime.now():%Y-%m-%d %H:%M}", ""]
    cited, uncited = [], []
    for b in book:
        pub_url = (b.get("url") or "").strip()
        if not pub_url:
            continue
        nu = norm_url(pub_url)
        dom = registrable(urlparse(pub_url if "://" in pub_url else "https://" + pub_url).netloc)
        exact, domain = url_hits.get(nu, []), [h for h in dom_hits.get(dom, [])
                                               if norm_url(h[4]) != nu]
        if exact or domain:
            plats = sorted({h[0] for h in exact + domain})
            first = min((h[3] for h in exact + domain if h[3]), default="")
            evid = "；".join(dict.fromkeys(h[2] for h in exact + domain if h[2]))[:120]
            level = "URL 级" if exact else "仅域名级（建议核对是否真为贵司页）"
            cited.append((b, plats, first, evid, level))
            lines.append(f"- ✅ [{b.get('publish_id', '')}] {b.get('title', '')} ← 被引用于 "
                         f"{'、'.join(plats)}（{level}）｜首见 {first or '—'}｜证据 run_id：{evid}")
        else:
            uncited.append(b)
            lines.append(f"- ⬜ [{b.get('publish_id', '')}] {b.get('title', '')} ← 暂未在监测引用中出现（发布后需 2–4 周语料期，持续观察）")
    lines += ["", f"## 汇总：发布 {len(book)} 条，已被引用 {len(cited)}，未引用 {len(uncited)}"
                  f"（引用率 {len(cited) / len(book) * 100:.0f}%）", "",
              "> 未引用 ≠ 白写：AI 语料有滞后；连续 4 周未引用的内容按内容工作台规则换角度重做。"]

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"归因核对_{datetime.now():%Y%m%d}.md"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ 归因核对报告：{dest}")

    if a.fill:
        cols = ["cited_by_ai", "first_seen_date", "evidence"]
        for b in book:
            match = [c for c in cited if c[0].get("publish_id") == b.get("publish_id")]
            if match:
                _, plats, first, evid, _ = match[0]
                b["cited_by_ai"] = "、".join(plats)
                b["first_seen_date"] = first
                b["evidence"] = evid
            else:
                for c in cols:
                    b[c] = b.get(c) or ""
        with Path(a.fill).open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(book[0].keys()))
            w.writeheader()
            w.writerows(book)
        print(f"✅ 台账已回填：{a.fill}")


def load_rows_safe(paths):
    rows = []
    for p in paths:
        rows.extend(load_csv(p))
    if not rows:
        sys.exit("[错误] 监测台账为空")
    return rows


if __name__ == "__main__":
    main()
