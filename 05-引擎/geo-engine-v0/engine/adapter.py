"""平台适配器抽象。每个平台一个 Adapter，接口统一；账号池/限频在 runner 层统筹。"""
from abc import ABC, abstractmethod

from .models import AIResponse, QueryItem


class BaseAdapter(ABC):
    platform: str = "base"

    @abstractmethod
    async def login(self) -> None:
        """建立/恢复登录态（复用持久化 context）。EyeCore 教训：先登录态，后操作。"""

    @abstractmethod
    async def ask(self, item: QueryItem) -> AIResponse:
        """新会话发送查询 → 等待流式完成 → 抓回答全文/引用/截图。失败抛 AdapterError。"""

    @abstractmethod
    async def health_check(self) -> bool:
        """会话健康度：掉登录/风控弹窗返回 False，由 runner 决定重建或熔断。"""
