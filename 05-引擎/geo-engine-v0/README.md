# GEO 监测引擎 v0

> 一句话：自动向豆包/腾讯元宝/DeepSeek 发送监测查询词，采集回答全文＋引用来源＋截图存证，输出结构化台账，替代每周 2 小时的手动监测（执行手册 Phase 2/6 的自动化）。
> 创建：2026-09-08 | v0 目标期限：2026-10-05

## v0 目标（按序勾选）

- [ ] 豆包适配器跑通（优先——消费类问答引用最活跃）
- [ ] 空针 40 词 × 1 轮自动采集，结果落 `output/` CSV
- [ ] 元宝适配器（公众号引用归因是重点字段）
- [ ] DeepSeek 适配器（联网/不联网两种模式分开记录）
- [ ] 快照按 `日期_平台_查询编号.jpg` 归档，可对照人工抽检

## 纪律（先于功能，违反一条全盘皆输）

1. **频率**：单账号日查询 ≤15；查询间随机等待 3–10 分钟；全任务错峰。宁可慢，不可封。
2. **证据**：每次回答全页截图＋时间戳＋（可得的）模型版本，全部入记录——报告的可信度=证据链的完整度。
3. **隔离**：账号/指纹/代理一一绑定；`config.yaml` 与 `output/` 不入仓库（见 .gitignore）。
4. **EyeCore 经验直接复用**：先建登录态再操作；雪花 ID 一律文本；签名类问题先查双重编码；iframe/内嵌页先看会话时序。

## 结构

```
engine/adapter.py        适配器抽象（所有平台实现同一接口）
engine/models.py         数据结构：QueryItem / AIResponse / Citation
engine/runner.py         读词表 → 调度（限频+断点续跑）→ 落盘 CSV
engine/adapters/doubao.py   豆包（先行）——Playwright 流程骨架
queries/kongzhen-40.yaml 空针 40 条监测词（来自执行手册 Phase 2.1）
config.example.yaml      配置样例（复制为 config.yaml 填真实值）
output/                  运行产出（CSV 台账 + screenshots/，不入库）
```

## 与手动 SOP 的对应（验收口径不变）

输出的 CSV 字段 = 执行手册 2.3 基线记录表：日期/平台/查询词/是否提及目标品牌/推荐位次/引用来源数/来源是否含我方/倾向(正中负)/提及了哪些竞品/截图文件名。
"是否提及/位次/倾向"三列 v0 阶段可人工复核填写，v1 交给 LLM 解析（品牌事实库做实体清单）。

## 运行

```bash
pip install -r requirements.txt
playwright install chromium
cp config.example.yaml config.yaml   # 填账号等
python -m engine.runner --queries queries/kongzhen-40.yaml --platform doubao
```
