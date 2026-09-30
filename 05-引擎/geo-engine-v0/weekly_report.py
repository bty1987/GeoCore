"""GEO 监测周报半自动生成器（P0-1）。

输入：基线记录表 CSV（字段=引擎 CSV_FIELDS + 人工复核两列，见 templates/基线记录表-模板.csv），
输出：周报草稿 Markdown——五个核心数字 + 周环比变化 + 需优化词清单 + 竞品动态，
解读性文字留白由人工补齐。引擎未上线前同样可用（手动监测照此 schema 填表）。

用法：
  单周统计：  python weekly_report.py --this-week output/ledger_doubao_250930.csv
  周环比：    python weekly_report.py --this-week ledger_..._1007.csv --last-week ledger_..._0930.csv
  可选参数：  --brand 空针数据 --outdir output/reports --queries queries/kongzhen-40.yaml
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

# 与 engine/runner.py CSV_FIELDS 对齐；后两列为 v0 人工复核列（引擎产出缺省为空）
FIELDS = ["run_id", "platform", "qid", "query_text", "brand_mentioned",
          "recommend_rank", "sentiment", "citation_count", "citations",
          "sources_contain_us", "competitors_mentioned", "snapshot_path",
          "online_mode", "collected_at"]

PLATFORM_LABEL = {"doubao": "豆包", "yuanbao": "腾讯元宝", "deepseek": "DeepSeek"}
# 口径锚（防 A3 类漂移）：监测口径=40 词四类 × 3 平台，与执行手册 2.3 一致
PREFIX_QTYPE = {"A": ("brand", "品牌词（防守层）"), "B": ("category", "品类词（进攻层）"),
                "C": ("compare", "对比词"), "D": ("scenario", "场景词（长尾层）")}
MENTION_YES = "是"
SENTIMENTS = ["正", "中", "负"]
COMPETITOR_SEPARATORS = ["；", ";", "、", ",", "，"]


def qtype_of(qid: str, yaml_map: dict | None) -> tuple[str, str]:
    if yaml_map and qid in yaml_map:
        return yaml_map[qid]
    prefix = (qid or " ")[:1].upper()
    return PREFIX_QTYPE.get(prefix, ("other", "其他"))


def load_yaml_qtypes(path: str | None) -> dict:
    if not path:
        return {}
    try:
        import yaml
    except ImportError:
        print("[提示] 未装 pyyaml，词表类型改用 qid 前缀推断（A/B/C/D）", file=sys.stderr)
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    mapping = {}
    for group in data.get("queries", []):
        for q in group.get("items", []):
            mapping[q["id"]] = (group["type"], group["type"])
    return mapping


def load_rows(paths: list[str]) -> list[dict]:
    rows = []
    for p in paths:
        f = Path(p)
        if not f.exists():
            sys.exit(f"[错误] 找不到数据文件：{p}")
        with f.open(newline="", encoding="utf-8-sig") as fh:
            for i, row in enumerate(csv.DictReader(fh), 2):
                if not (row.get("run_id") or "").strip():
                    continue  # 空行跳过
                missing = [c for c in ("run_id", "platform", "qid") if not (row.get(c) or "").strip()]
                if missing:
                    print(f"[警告] {f.name} 第{i}行缺 {missing}，跳过", file=sys.stderr)
                    continue
                rows.append(row)
    return rows


def split_competitors(cell: str) -> list[str]:
    for sep in COMPETITOR_SEPARATORS:
        cell = cell.replace(sep, "|")
    return [c.strip() for c in cell.split("|") if c.strip() and c.strip() != ";"]


def parse_rank(cell: str):
    cell = (cell or "").strip()
    if cell.endswith("位"):
        cell = cell[:-1]
    return int(cell) if cell.isdigit() else None


def week_of(rows: list[dict]) -> str:
    days = []
    for r in rows:
        v = (r.get("collected_at") or "").strip()
        try:
            days.append(datetime.strptime(v[:10], "%Y-%m-%d"))
        except ValueError:
            pass
    return max(days).strftime("%Y-%m-%d") if days else date.today().strftime("%Y-%m-%d")


def stats(rows: list[dict], yaml_map: dict | None) -> dict:
    s = {"total": len(rows), "by_platform": Counter(), "by_qtype": Counter(),
         "mention": defaultdict(Counter), "ranks": [], "citation_avg": None,
         "citation_nums": [], "us_sources": 0, "sentiment": Counter(),
         "competitors": Counter(), "descriptive": 0}
    cite_vals = []
    for r in rows:
        plat = (r.get("platform") or "").strip()
        s["by_platform"][plat] += 1
        qt, _ = qtype_of(r.get("qid", ""), yaml_map)
        s["by_qtype"][qt] += 1
        m = (r.get("brand_mentioned") or "").strip()
        s["mention"][qt][m] += 1
        if m == MENTION_YES:
            rank = parse_rank(r.get("recommend_rank", ""))
            if rank and qt == "category":  # 「最佳推荐位次」只统计品类词，防对比词位次混入
                s["ranks"].append(rank)
            senti = (r.get("sentiment") or "").strip()
            if senti:
                s["sentiment"][senti] += 1
        elif m == "描述性提及":
            s["descriptive"] += 1
        try:
            n = int((r.get("citation_count") or "0").strip() or 0)
        except ValueError:
            n = 0
        cite_vals.append(n)
        if (r.get("sources_contain_us") or "").strip() == MENTION_YES:
            s["us_sources"] += 1
        for c in split_competitors(r.get("competitors_mentioned", "")):
            s["competitors"][c] += 1
    if cite_vals:
        s["citation_avg"] = sum(cite_vals) / len(cite_vals)
    return s


def rate(mention_counter: Counter, total: int) -> tuple[str, int]:
    if not total:
        return "—", 0
    yes = mention_counter.get(MENTION_YES, 0)
    return f"{yes / total * 100:.0f}%", yes


def diff(this_rows: list[dict], last_rows: list[dict], yaml_map: dict | None) -> list[dict]:
    def keyed(rows):
        return {(r["platform"], r["qid"]): r for r in rows}

    cur, prev = keyed(this_rows), keyed(last_rows)
    out = []
    for k in sorted(set(cur) & set(prev)):
        a, b = cur[k], prev[k]
        ma = (a.get("brand_mentioned") or "").strip()
        mb = (b.get("brand_mentioned") or "").strip()
        ra, rb = parse_rank(a.get("recommend_rank", "")), parse_rank(b.get("recommend_rank", ""))
        ca = int((a.get("citation_count") or "0").strip() or 0)
        cb = int((b.get("citation_count") or "0").strip() or 0)
        item = {"key": k, "query": a.get("query_text", ""),
                "mention": (mb, ma), "rank": (rb, ra), "cites": ca - cb}
        if ma != mb or ra != rb:
            out.append(item)
    return out


def render(args, this_rows, last_rows, yaml_map) -> str:
    s = stats(this_rows, yaml_map)
    plats = "、".join(PLATFORM_LABEL.get(p, p) for p in sorted(s["by_platform"])) or "—"
    L = []
    L.append(f"# {args.brand} GEO 监测周报（{week_of(this_rows)}）· 草稿")
    L.append("")
    L.append(f"> 口径：40 词四类 × 3 平台（豆包/腾讯元宝/DeepSeek），字段=基线记录表 schema v1。")
    L.append(f"> 数据源：{', '.join(Path(p).name for p in args.this_week)}"
             + (f" ｜ 环比基线：{', '.join(Path(p).name for p in args.last_week)}" if args.last_week else "（首周，无环比）"))
    L.append(f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}（半自动：数字已核，解读待人工）")
    L.append("")
    L.append("## 一、五个核心数字")
    L.append("")
    L.append(f"1. **采集量**：{s['total']} 条（平台分布：{'、'.join(f'{PLATFORM_LABEL.get(p,p)} {n}' for p, n in sorted(s['by_platform'].items())) or '—'}）"
             f"{'；⚠️ 未跑满 40×3=120 条' if s['total'] < 120 and args.expect_full else ''}")
    bqt, cqt = s["mention"].get("brand", Counter()), s["mention"].get("category", Counter())
    brate, byes = rate(bqt, s["by_qtype"].get("brand", 0))
    crate, cyes = rate(cqt, s["by_qtype"].get("category", 0))
    L.append(f"2. **品牌词提及率**：{brate}（{byes}/{s['by_qtype'].get('brand', 0)}）"
             + (f"，另有描述性提及 {s['descriptive']} 条" if s["descriptive"] else ""))
    rank_txt = f"最佳推荐位次 第{min(s['ranks'])} 位" if s["ranks"] else "暂未进入推荐位"
    L.append(f"3. **品类词提及率**：{crate}（{cyes}/{s['by_qtype'].get('category', 0)}），{rank_txt}")
    L.append(f"4. **平均引用来源数**：{s['citation_avg']:.1f} 条/回答" if s["citation_avg"] is not None
             else "4. **平均引用来源数**：—")
    L.append(f"5. **来源含我方**：{s['us_sources']} 条 ｜ 倾向分布：正 {s['sentiment'].get('正',0)} / 中 {s['sentiment'].get('中',0)} / 负 {s['sentiment'].get('负',0)}")
    L.append("")
    if args.last_week:
        d = diff(this_rows, last_rows, yaml_map)
        ups = [x for x in d if x["mention"][0] != MENTION_YES and x["mention"][1] == MENTION_YES]
        downs = [x for x in d if x["mention"][0] == MENTION_YES and x["mention"][1] != MENTION_YES]
        L.append("## 二、周环比变化")
        L.append("")
        L.append(f"共 {len(d)} 条词位有变化：新提及 {len(ups)}，掉出 {len(downs)}；下表列提及翻转与位次变化（引用数变化附在对应行）。")
        L.append("")
        if d:
            L.append("| 平台 | 词 | 查询词 | 变化 |")
            L.append("|---|---|---|---|")
            for x in d:
                plat, qid = x["key"]
                if x["mention"][0] != x["mention"][1]:
                    chg = f"提及 {x['mention'][0]}→{x['mention'][1]}{' ⭐' if x['mention'][1] == MENTION_YES else ' ⚠️'}"
                else:
                    fmt = lambda r: "未上榜" if r is None else f"第{r}位"
                    chg = f"位次 {fmt(x['rank'][0])}→{fmt(x['rank'][1])}"
                    if x["cites"]:
                        chg += f"｜引用 {x['cites']:+d}"
                L.append(f"| {PLATFORM_LABEL.get(plat, plat)} | {qid} | {x['query']} | {chg} |")
            L.append("")
    L.append("## 三、竞品动态（被提及次数排行）")
    L.append("")
    if s["competitors"]:
        for name, n in s["competitors"].most_common(8):
            L.append(f"- {name}：{n} 次")
    else:
        L.append("- 本周数据未填竞品列（人工复核列，手动监测时必填）")
    L.append("")
    L.append("## 四、需优化提问词清单")
    L.append("")
    misses = [r for r in this_rows
              if qtype_of(r.get("qid", ""), yaml_map)[0] in ("brand", "category")
              and (r.get("brand_mentioned") or "").strip() != MENTION_YES]
    if misses:
        L.append("| 平台 | 词 | 查询词 | 现状 |")
        L.append("|---|---|---|---|")
        for r in misses:
            m = (r.get("brand_mentioned") or "").strip() or "未填"
            L.append(f"| {PLATFORM_LABEL.get(r['platform'], r['platform'])} | {r['qid']} | {r['query_text']} | {m} |")
    else:
        L.append("品牌词/品类词全部提及——本周无待优化词（保持警戒，见周环比）。")
    L.append("")
    L.append("## 五、待人工补充")
    L.append("")
    L.append("- 本周解读（两三句：主打进展或主打风险，引用上面数字）：")
    L.append("- 下周动作（内容/平台/词表调整，各一条即可）：")
    L.append("- 证据抽查：截图在 screenshots/，文件名主干=run_id，可对照人工抽检")
    L.append("")
    L.append("---")
    L.append("*本报告由 weekly_report.py 半自动生成；结论与解读需人工确认后对外发送（口径红线：不承诺保证排名/收录）。*")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="GEO 监测周报半自动生成器")
    ap.add_argument("--this-week", nargs="+", required=True, help="本周基线记录表 CSV（可多文件=多平台）")
    ap.add_argument("--last-week", nargs="*", default=[], help="上周 CSV（可选，提供则出周环比）")
    ap.add_argument("--brand", default="空针数据")
    ap.add_argument("--outdir", default="output/reports")
    ap.add_argument("--queries", default="queries/kongzhen-40.yaml", help="词表 yaml（读 qid→类型；缺 pyyaml 时按前缀推断）")
    ap.add_argument("--expect-full", action="store_true", help="按 40×3=120 条校验采集完成率")
    a = ap.parse_args()

    yaml_map = load_yaml_qtypes(a.queries if Path(a.queries).exists() else None)
    this_rows = load_rows(a.this_week)
    if not this_rows:
        sys.exit("[错误] 本周数据为空，先填基线记录表（templates/基线记录表-模板.csv）")
    last_rows = load_rows(a.last_week) if a.last_week else []
    md = render(a, this_rows, last_rows, yaml_map)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"周报草稿_{week_of(this_rows).replace('-', '')}.md"
    dest.write_text(md, encoding="utf-8")
    print(f"✅ 周报草稿已生成：{dest}")
    print("   下一步：补齐「五、待人工补充」三处留白，人工确认后对外。")


if __name__ == "__main__":
    main()
