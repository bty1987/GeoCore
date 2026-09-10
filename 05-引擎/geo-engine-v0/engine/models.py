"""数据结构。约定：一切外部 ID（平台雪花 ID 等）一律以 str 存储，防精度丢失。"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QueryItem:
    qid: str            # 词表编号，如 "B03"
    text: str           # 查询词原文
    qtype: str          # brand / category / compare / scenario
    brand: str = "空针数据"   # 监测目标品牌


@dataclass
class Citation:
    source_url: str = ""
    source_domain: str = ""
    source_title: str = ""


@dataclass
class AIResponse:
    run_id: str                 # 日期_平台_查询编号，同截图文件名主干
    platform: str               # doubao / yuanbao / deepseek
    qid: str
    query_text: str
    raw_text: str = ""          # 回答全文
    citations: list[Citation] = field(default_factory=list)
    snapshot_path: str = ""     # 截图相对路径
    model_version: str = ""     # 可得则填
    online_mode: bool = True    # DeepSeek 不联网回答记 False
    collected_at: datetime = field(default_factory=datetime.now)
    # —— 以下三列 v0 允许人工复核填写，v1 交 LLM 解析 ——
    brand_mentioned: str = ""   # 是/否/描述性提及
    recommend_rank: str = ""    # 推荐位次（品类词）
    sentiment: str = ""         # 正/中/负
