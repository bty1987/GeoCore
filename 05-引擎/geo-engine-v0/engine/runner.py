"""调度器：读词表 → 限频循环 → 落 CSV（断点续跑：已有 run_id 跳过）。"""
import argparse
import asyncio
import csv
import random
from datetime import date
from pathlib import Path

import yaml

from .models import QueryItem

CSV_FIELDS = ["run_id", "platform", "qid", "query_text", "brand_mentioned",
              "recommend_rank", "sentiment", "citation_count", "citations",
              "snapshot_path", "online_mode", "collected_at"]


def load_queries(path: str) -> list[QueryItem]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    items = []
    for group in data["queries"]:
        qtype = group["type"]
        for q in group["items"]:
            items.append(QueryItem(qid=q["id"], text=q["text"], qtype=qtype))
    return items


def done_ids(out_csv: Path) -> set[str]:
    if not out_csv.exists():
        return set()
    with out_csv.open(newline="", encoding="utf-8-sig") as f:
        return {row["run_id"] for row in csv.DictReader(f)}


async def run(queries_path: str, platform: str) -> None:
    items = load_queries(queries_path)
    out_dir = Path("output"); out_dir.mkdir(exist_ok=True)
    out_csv = out_dir / f"ledger_{platform}_{date.today():%y%m%d}.csv"
    skip = done_ids(out_csv)
    # TODO: 按 config 建 playwright 持久化 context -> Adapter(platform) -> login()
    for item in items:
        run_id = f"{date.today():%y%m%d}_{platform}_{item.qid}"
        if run_id in skip:
            print(f"skip {run_id}")
            continue
        print(f"asking {run_id}: {item.text}")
        # TODO: resp = await adapter.ask(item)；写一行 CSV（CSV_FIELDS）
        # TODO: health_check() 为 False -> 切账号/熔断；随机 sleep uniform(min_gap, max_gap)
        await asyncio.sleep(random.uniform(180, 600))  # 3–10 分钟，宁可慢不可封


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="queries/kongzhen-40.yaml")
    ap.add_argument("--platform", default="doubao", choices=["doubao", "yuanbao", "deepseek"])
    a = ap.parse_args()
    asyncio.run(run(a.queries, a.platform))
