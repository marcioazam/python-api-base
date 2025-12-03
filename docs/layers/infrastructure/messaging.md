# Messaging Infrastructure

## Overview

O sistema suporta Kafka para event streaming e RabbitMQ para task queues.

## Kafka Producer

```python
from aiokafka import AIOKafkaProducer
import json

class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self._producer: AIOKafkaProducer | None = None
        self._bootstrap_servers = bootstrap_servers
    
    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self._producer.start()
    
    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
    
    async def send(
        self,
        topic: str,
        value: dict,
        key: str | None = None,
    ) -> None:
        await self._producer.send_and_wait(
            topic=topic,
            value=value,
            key=key.encode() if key else None,
        )
```

## Kafka Consumer

```python
from aiokafka import AIOKafkaConsumer

class KafkaConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
    ):
        self._consumer: AIOKafkaConsumer | None = None
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
    
    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode()),
        )
        await self._consumer.start()
    
    async def consume(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        async for msg in self._consumer:
            try:
                await handler(msg.value)
            except Exception as e:
                logger.error("message_processing_failed", error=str(e))
```

## RabbitMQ Queue

```python
import aio_pika

class RabbitMQQueue:
    def __init__(self, url: str, queue_name: str):
        self._url = url
        self._queue_name = queue_name
        self._connection: aio_pika.Connection | None = None
        self._channel: aio_pika.Channel | None = None
    
    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.declare_queue(self._queue_name, durable=True)
    
    async def publish(self, message: dict) -> None:
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=self._queue_name,
        )
    
    async def consume(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        queue = await self._channel.get_queue(self._queue_name)
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    await handler(data)
```

## Event Publishing

```python
class EventPublisher:
    def __init__(self, kafka: KafkaProducer):
        self._kafka = kafka
    
    async def publish(self, event: DomainEvent) -> None:
        await self._kafka.send(
            topic=f"events.{event.event_type}",
            value={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "data": asdict(event),
            },
            key=getattr(event, "aggregate_id", None),
        )
```

## Task Worker

```python
class TaskWorker:
    def __init__(self, queue: RabbitMQQueue):
        self._queue = queue
        self._handlers: dict[str, Callable] = {}
    
    def register(self, task_type: str, handler: Callable) -> None:
        self._handlers[task_type] = handler
    
    async def start(self) -> None:
        await self._queue.consume(self._process_task)
    
    async def _process_task(self, message: dict) -> None:
        task_type = message.get("type")
        handler = self._handlers.get(task_type)
        
        if handler:
            await handler(message.get("data", {}))
        else:
            logger.warning("unknown_task_type", task_type=task_type)
```

## Best Practices

1. **Use durable queues** - For reliability
2. **Implement idempotency** - Handle duplicate messages
3. **Use dead letter queues** - For failed messages
4. **Monitor lag** - Alert on consumer lag
5. **Use transactions** - For exactly-once semantics
