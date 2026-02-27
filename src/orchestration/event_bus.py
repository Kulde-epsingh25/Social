"""In-process event bus with optional Kafka backend."""

from __future__ import annotations

import logging
import queue
import threading
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    """Lightweight publish/subscribe event bus.

    Uses an in-process ``queue.Queue`` by default.  When Kafka is available
    and ``KAFKA_BOOTSTRAP_SERVERS`` is configured, messages are also forwarded
    to the Kafka topic.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self._kafka_producer = self._init_kafka()
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop, daemon=True
        )
        self._dispatch_thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(self, topic: str, event: dict[str, Any]) -> None:
        """Publish *event* to *topic*."""
        self._queue.put((topic, event))
        self._publish_kafka(topic, event)

    def subscribe(self, topic: str, handler: Callable[[dict], None]) -> None:
        """Register *handler* to be called for every event on *topic*."""
        self._subscribers[topic].append(handler)
        logger.debug("Subscribed handler '%s' to topic '%s'.", handler.__name__, topic)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dispatch_loop(self) -> None:
        while True:
            try:
                topic, event = self._queue.get(timeout=1)
                for handler in self._subscribers.get(topic, []):
                    try:
                        handler(event)
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "Handler '%s' raised on topic '%s': %s",
                            handler.__name__,
                            topic,
                            exc,
                        )
            except queue.Empty:
                continue

    @staticmethod
    def _init_kafka():  # noqa: ANN
        from src.config.settings import settings

        if not settings.kafka_bootstrap_servers:
            return None
        try:
            from kafka import KafkaProducer  # type: ignore[import]
            import json

            producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            logger.info("Kafka producer connected.")
            return producer
        except Exception as exc:  # noqa: BLE001
            logger.debug("Kafka unavailable (%s) – using in-process queue only.", exc)
            return None

    def _publish_kafka(self, topic: str, event: dict) -> None:
        if self._kafka_producer is None:
            return
        try:
            self._kafka_producer.send(topic, event)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kafka publish failed: %s", exc)


# Module-level singleton
event_bus = EventBus()
