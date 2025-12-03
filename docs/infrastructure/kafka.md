# Kafka Integration

## Overview

Apache Kafka é usado para event streaming e comunicação assíncrona entre serviços.

## Configuration

```bash
KAFKA__BOOTSTRAP_SERVERS=localhost:9092
KAFKA__GROUP_ID=python-api-base
KAFKA__AUTO_OFFSET_RESET=earliest
```

## Producer

```python
from aiokafka import AIOKafkaProducer

class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self._producer: AIOKafkaProducer | None = None
        self._servers = bootstrap_servers
    
    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._servers,
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
        )
        await self._producer.start()
    
    async def send(self, topic: str, value: dict, key: str | None = None) -> None:
        await self._producer.send_and_wait(topic, value=value, key=key)
    
    async def stop(self) -> None:
        await self._producer.stop()
```

## Consumer

```python
from aiokafka import AIOKafkaConsumer

class KafkaConsumer:
    def __init__(self, bootstrap_servers: str, group_id: str, topics: list[str]):
        self._consumer: AIOKafkaConsumer | None = None
        self._servers = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
    
    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._servers,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
    
    async def consume(self, handler: Callable[[dict], Awaitable[None]]) -> None:
        async for msg in self._consumer:
            try:
                await handler(msg.value)
            except Exception as e:
                logger.error("kafka_message_error", error=str(e), topic=msg.topic)
```

## Event Publishing

```python
class EventPublisher:
    def __init__(self, producer: KafkaProducer):
        self._producer = producer
    
    async def publish(self, event: DomainEvent) -> None:
        topic = f"events.{event.event_type.lower()}"
        await self._producer.send(
            topic=topic,
            value={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "data": asdict(event),
            },
            key=getattr(event, "aggregate_id", None),
        )
```

## Event Handling

```python
class UserEventHandler:
    async def handle(self, message: dict) -> None:
        event_type = message.get("event_type")
        
        match event_type:
            case "UserCreated":
                await self._handle_user_created(message["data"])
            case "UserUpdated":
                await self._handle_user_updated(message["data"])
            case _:
                logger.warning("unknown_event", event_type=event_type)
    
    async def _handle_user_created(self, data: dict) -> None:
        # Send welcome email, update search index, etc.
        pass
```

## Transactions

```python
async def transactional_send(producer: AIOKafkaProducer, messages: list[tuple[str, dict]]) -> None:
    async with producer.transaction():
        for topic, value in messages:
            await producer.send(topic, value=value)
```

## Error Handling

```python
class RetryableConsumer:
    MAX_RETRIES = 3
    
    async def consume_with_retry(self, handler: Callable) -> None:
        async for msg in self._consumer:
            retries = 0
            while retries < self.MAX_RETRIES:
                try:
                    await handler(msg.value)
                    break
                except Exception as e:
                    retries += 1
                    if retries >= self.MAX_RETRIES:
                        await self._send_to_dlq(msg)
                    else:
                        await asyncio.sleep(2 ** retries)
    
    async def _send_to_dlq(self, msg) -> None:
        await self._producer.send(f"{msg.topic}.dlq", value=msg.value)
```

## Monitoring

```bash
# List topics
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Describe topic
kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic events.user

# Consumer lag
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group python-api-base

# Read messages
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic events.user --from-beginning
```

## Best Practices

1. **Use idempotent consumers** - Handle duplicate messages
2. **Set appropriate partitions** - For parallelism
3. **Monitor consumer lag** - Alert on growing lag
4. **Use dead letter queues** - For failed messages
5. **Set retention policies** - Based on use case
