"""In-process inter-agent message bus with optional compression."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from workflow_automation.compression.compressor import ContextCompressor


@dataclass
class AgentMessage:
    id: str
    sender_role: str
    receiver_role: str
    message_type: str
    content: str
    compressed: bool = False
    original_size: int = 0
    compressed_size: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MessageBus:
    """Publish/subscribe bus for structured agent communication."""

    def __init__(self, compressor: ContextCompressor | None = None) -> None:
        self.compressor = compressor or ContextCompressor()
        self._messages: list[AgentMessage] = []
        self._subscribers: dict[str, list[Callable[[AgentMessage], None]]] = {}

    def subscribe(self, role: str, handler: Callable[[AgentMessage], None]) -> None:
        self._subscribers.setdefault(role, []).append(handler)

    def publish(
        self,
        *,
        sender_role: str,
        receiver_role: str,
        content: str,
        message_type: str = "task",
        compress: bool = True,
    ) -> AgentMessage:
        body = content
        compressed = False
        original_size = len(content)
        compressed_size = original_size
        if compress:
            result = self.compressor.compress(content)
            body = result.text
            compressed = result.compressed
            original_size = result.original_size
            compressed_size = result.compressed_size

        message = AgentMessage(
            id=str(uuid4()),
            sender_role=sender_role,
            receiver_role=receiver_role,
            message_type=message_type,
            content=body,
            compressed=compressed,
            original_size=original_size,
            compressed_size=compressed_size,
        )
        self._messages.append(message)
        for handler in self._subscribers.get(receiver_role, []):
            handler(message)
        for handler in self._subscribers.get("*", []):
            handler(message)
        return message

    @property
    def messages(self) -> list[AgentMessage]:
        return list(self._messages)

    def compression_ratio(self) -> float:
        original = sum(m.original_size for m in self._messages) or 1
        compressed = sum(m.compressed_size for m in self._messages) or 1
        return compressed / original
