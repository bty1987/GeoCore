"""GEO 行业 AI 可见性快查报告生成器（P1-4，获客钩子）。

与周报生成器（weekly_report.py）同一数据底座（基线记录表 CSV），但产出面向
**潜在客户**的快查报告：短、狠、留钩子——10–20 问 × 3 平台的实测快照，
让对方看见"AI 正在怎么回答他客户的问题"。

用法：
  python3 quickcheck.py --this-week 台账_快查_YYMMDD.csv [--industry 房产家装] \
      [--brand 空针数据] [--outdir output/quickcheck] [--contact "微信 xxx"]

纪律：数字全部来自实测台账；"三大发现"只陈述事实不下保证；
      不出现"保证排名/保证收录"字样；解读与 CTA 留白由人工补齐后再发。
"""
import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from weekly_report import (MENTION_YES, PLATFORM_LABEL, load_rows, load_yaml_qtypes,
                           qtype_of, rate, stats, week_of)


def pick_misses(rows, yaml_map, n=3):
    """未提及的品类词优先（获客冲击最大），其次品牌词。"""
    miss = [r for r in rows
            if qtype_of(r.get("qid", ""), yaml_map)[0] in ("brand", "category")
            and (r.get("brand_mentioned") or "").strip() != MENTION_YES]
    miss.sort(key=lambda r: (0 if qtype_of(r.get("qid", ""), yaml_map)[0] == "category" else 1,
                             r.get("qid", "")))
    return miss[:n]


def render(args, rows, yaml_map) -> str:
    s = stats(rows, yaml_map)
    total_brand = s["by_qtype"].get("brand", 0)
    total_cat = s["by_qtype"].get("category", 0)
    brate, byes = rate(s["mention"].get("brand", Counter()), total_brand)
    crate, cyes = rate(s["mention"].get("category", Counter()), total_cat)
    plats = "、".join(PLATFORM_LABEL.get(p, p) for p in sorted(s["by_platform"])) or "—"
    comp_top = s["competitors"].most_common(3)

    L = []
    L.append(f"# {args.industry or ''}行业 AI 可见性快查 · {week_of(rows)}")
    L.append("")
    L.append(f"> 实测平台：{plats} ｜ 样本：{s['total']} 个真实问法（快查版 10–20 问，正式监测为 40 词四类 × 3 平台）")
    L.append(f"> 生成：{datetime.now():%Y-%m-%d %H:%M} ｜ 数字全部来自实测台账，可提供截图核验")
    L.append("")
    L.append("## 您的客户正在这样问 AI")
    L.append("")
    qs = [r.get("query_text", "") for r in rows if qtype_of(r.get("qid", ""), yaml_map)[0] in ("brand", "category")][:6]
    for q in qs:
        L.append(f"- 「{q}」")
    L.append("")
    L.append("## 快查数字")
    L.append("")
    L.append("| 指标 | 结果 | 说明 |")
    L.append("|---|---|---|")
    L.append(f"| 品牌词提及率 | {brate}（{byes}/{total_brand}） | 客户直接问您时，AI 能否答对 |")
    best = f"最佳第{min(s['ranks'])}位" if s["ranks"] else "暂未进入推荐位"
    L.append(f"| 品类词提及率 | {crate}（{cyes}/{total_cat}） | 客户问品类问题时，您是否被推荐（{best}） |")
    L.append(f"| 平均引用来源 | {s['citation_avg']:.1f} 条/回答 | AI 回答依据的语料量 |"
             if s["citation_avg"] is not None else "| 平均引用来源 | — | 无数据 |")
    L.append(f"| 来源含贵司 | {s['us_sources']} 条 | AI 会不会把流量导给您 |")
    L.append("")
    L.append("## 三大发现")
    L.append("")
    if comp_top:
        c0, n0 = comp_top[0]
        L.append(f"1. **竞品占位**：「{c0}」在本次实测中被 AI 提及 {n0} 次"
                 + (f"，同期贵司被提及 {byes + cyes} 次" if (byes + cyes) else "，同期贵司在品类词中基本未出现"))
    else:
        L.append("1. **竞品占位**：本次样本未填竞品列（补齐台账竞品列后重跑可出）")
    misses = pick_misses(rows, yaml_map)
    if misses:
        words = "、".join(f"「{m.get('query_text', '')}」" for m in misses)
        L.append(f"2. **空白词位**：{words} 等 {len([r for r in rows if (r.get('brand_mentioned') or '').strip() != MENTION_YES])} 个提问中 AI 未提及贵司——**空白意味着第一入驻成本最低**")
    else:
        L.append("2. **空白词位**：本次样本内品牌词/品类词全部被提及（继续保持，警惕竞品进攻）")
    L.append(f"3. **引用缺失**：{s['total']} 条回答中仅 {s['us_sources']} 条引用了贵司自有内容——"
             + ("AI 想引用，却找不到可引的权威语料" if s["us_sources"] < max(1, s["total"] // 5)
                else "贵司语料已能被部分引用，可继续加固"))
    L.append("")
    L.append("## 这对您意味着什么")
    L.append("")
    L.append("（人工补两三句：结合对方行业，把空白词位翻译成生意机会。不承诺效果，不拍胸脯。）")
    L.append("")
    L.append("## 下一步（15 分钟，讲清三件事）")
    L.append("")
    L.append("1. 这份快查的完整截图证据怎么核验；")
    L.append("2. 正式 40 词基线监测怎么做、多久见效窗口（2–4 周起）；")
    L.append("3. 【试点方案：定金+效果对赌，不达标全额退】——以《服务确认函》为准，此处不报价。")
    L.append("")
    L.append(f"---")
    L.append(f"*联系人：{args.contact or '【待填：联系方式】'} ｜ {args.brand or ''}*")
    L.append("*口径声明：本快查为单轮抽测样本，非承诺性文件；不保证任何平台排名或收录。*")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="GEO 行业 AI 可见性快查报告（获客钩子）")
    ap.add_argument("--this-week", nargs="+", required=True, help="快查台账 CSV（基线记录表同 schema）")
    ap.add_argument("--industry", default="", help="行业名，如：房产家装")
    ap.add_argument("--brand", default="", help="我方署名（留空则不署）")
    ap.add_argument("--contact", default="", help="CTA 联系方式文案")
    ap.add_argument("--outdir", default="output/quickcheck")
    ap.add_argument("--queries", default="queries/kongzhen-40.yaml")
    a = ap.parse_args()

    yaml_map = load_yaml_qtypes(a.queries if Path(a.queries).exists() else None)
    rows = load_rows(a.this_week)
    if not rows:
        sys.exit("[错误] 快查台账为空——先按 templates/基线记录表-模板.csv 填 10–20 问实测结果")
    md = render(a, rows, yaml_map)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"快查报告_{week_of(rows).replace('-', '')}.md"
    dest.write_text(md, encoding="utf-8")
    print(f"✅ 快查报告草稿已生成：{dest}")
    print("   发出前人工补：『这对您意味着什么』两三句 + 联系方式；并核对三大发现措辞。")


if __name__ == "__main__":
    main()
