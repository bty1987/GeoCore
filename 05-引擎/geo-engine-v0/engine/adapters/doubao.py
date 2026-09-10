"""豆包适配器骨架。流程 = 执行手册 2.2 手动 SOP 的自动化翻译；TODO 处按实测补齐选择器。

纪律提醒（写死在注释里，防止未来自己踩）：
- 逐字输入＋随机停顿，不做瞬发 paste；
- 回答下方"搜索来源"条必须解析（消费类引用的高发区，头条/搜狐域名）；
- 每问一个新对话，避免上下文污染；
- 连续失败即熔断该账号 24h（runner 层实现），不要硬重试。
"""
import asyncio
import random

from ..adapter import BaseAdapter
from ..models import AIResponse, Citation, QueryItem

# TODO 实测后填：输入框 / 发送按钮 / 回答区容器 / 引用来源条 / 流式结束标志 的选择器
SEL_INPUT = "TODO"
SEL_SEND = "TODO"
SEL_ANSWER = "TODO"
SEL_SOURCES = "TODO"


class DoubaoAdapter(BaseAdapter):
    platform = "doubao"

    def __init__(self, context):  # context: playwright.async_api.BrowserContext（持久化）
        self.ctx = context
        self.page = None

    async def login(self) -> None:
        self.page = await self.ctx.new_page()
        await self.page.goto("https://www.doubao.com/chat/")
        # 持久化 context 内已有登录态则直接可用；否则需要人工扫码一次（首跑半自动是可接受的）
        # TODO 检测登录态元素；未登录 -> 提示人工登录后继续（v0 半自动）
        await self.page.wait_for_load_state("networkidle")

    async def health_check(self) -> bool:
        # TODO 检测风控/验证码/掉登录标记
        return True

    async def ask(self, item: QueryItem) -> AIResponse:
        run_id = f"{AIResponse.__name__ and ''}{self._run_id(item)}"  # 占位，见 _run_id
        # 1. 新对话
        # TODO: await self.page.click(SEL_NEW_CHAT)
        # 2. 逐字输入（人类节奏）
        for ch in item.text:
            # TODO: await self.page.type(SEL_INPUT, ch, delay=0)
            await asyncio.sleep(random.uniform(0.05, 0.25))
        # TODO: await self.page.click(SEL_SEND)
        # 3. 等待流式完成（监听 DOM 稳定或"停止生成"消失，超时 120s）
        # TODO: await self.page.wait_for_selector(...)
        # 4. 抓取回答与引用
        raw = ""   # TODO: await self.page.inner_text(SEL_ANSWER)
        cites = [] # TODO: 解析 SEL_SOURCES 下每条的 标题/域名/URL -> Citation(...)
        # 5. 全页截图存证
        snap = f"output/screenshots/{run_id}.jpg"
        # TODO: await self.page.screenshot(path=snap, full_page=True)
        return AIResponse(
            run_id=run_id, platform=self.platform, qid=item.qid,
            query_text=item.text, raw_text=raw, citations=cites or [Citation()],
            snapshot_path=snap,
        )

    @staticmethod
    def _run_id(item: QueryItem) -> str:
        from datetime import date
        return f"{date.today():%y%m%d}_doubao_{item.qid}"
