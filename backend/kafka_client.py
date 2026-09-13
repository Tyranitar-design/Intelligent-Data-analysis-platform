"""
Kafka 客户端封装
提供与 Kafka/Redpanda 的交互接口
"""
import os
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime


class KafkaClient:
    """Kafka 客户端封装"""
    
    def __init__(
        self,
        bootstrap_servers: str = None,
        client_id: str = "data-platform"
    ):
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092"
        )
        self.client_id = client_id
        self._producer = None
        self._consumer = None
    
    def _get_producer(self):
        """获取或创建生产者"""
        if self._producer is None:
            try:
                from kafka import KafkaProducer
                
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    client_id=self.client_id,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=3,
                    acks='all'
                )
            except ImportError:
                raise ImportError("请安装 kafka-python: pip install kafka-python")
        
        return self._producer
    
    def send(
        self,
        topic: str,
        value: Dict[str, Any],
        key: str = None,
        headers: Dict[str, str] = None
    ) -> bool:
        """
        发送消息到 Kafka
        
        Args:
            topic: 主题名
            value: 消息内容
            key: 消息键
            headers: 消息头
            
        Returns:
            是否成功
        """
        try:
            producer = self._get_producer()
            
            # 添加时间戳
            if isinstance(value, dict):
                value['_timestamp'] = datetime.now().isoformat()
            
            # 发送消息
            future = producer.send(
                topic=topic,
                value=value,
                key=key,
                headers=[(k, v.encode('utf-8')) for k, v in (headers or {}).items()]
            )
            
            # 等待确认
            record_metadata = future.get(timeout=10)
            
            print(f"✅ 消息已发送: {topic} [{record_metadata.partition}] @ {record_metadata.offset}")
            return True
            
        except Exception as e:
            print(f"❌ 发送失败: {str(e)}")
            return False
    
    def send_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]],
        key_field: str = None
    ) -> int:
        """
        批量发送消息
        
        Args:
            topic: 主题名
            messages: 消息列表
            key_field: 用作 key 的字段名
            
        Returns:
            成功发送的数量
        """
        success_count = 0
        
        for msg in messages:
            key = msg.get(key_field) if key_field else None
            if self.send(topic, msg, key):
                success_count += 1
        
        return success_count
    
    def consume(
        self,
        topics: List[str],
        group_id: str = None,
        auto_offset_reset: str = "earliest",
        max_messages: int = None,
        timeout_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        消费消息
        
        Args:
            topics: 主题列表
            group_id: 消费者组 ID
            auto_offset_reset: 偏移量重置策略
            max_messages: 最大消费数量
            timeout_ms: 超时时间
            
        Returns:
            消息列表
        """
        try:
            from kafka import KafkaConsumer
            
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id or f"{self.client_id}-consumer",
                auto_offset_reset=auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                consumer_timeout_ms=timeout_ms
            )
            
            messages = []
            for message in consumer:
                messages.append({
                    'topic': message.topic,
                    'partition': message.partition,
                    'offset': message.offset,
                    'key': message.key,
                    'value': message.value,
                    'timestamp': message.timestamp
                })
                
                if max_messages and len(messages) >= max_messages:
                    break
            
            consumer.close()
            return messages
            
        except ImportError:
            raise ImportError("请安装 kafka-python: pip install kafka-python")
        except Exception as e:
            print(f"❌ 消费失败: {str(e)}")
            return []
    
    def create_topic(
        self,
        topic: str,
        num_partitions: int = 1,
        replication_factor: int = 1
    ) -> bool:
        """
        创建主题
        
        Args:
            topic: 主题名
            num_partitions: 分区数
            replication_factor: 副本数
            
        Returns:
            是否成功
        """
        try:
            from kafka.admin import KafkaAdminClient, NewTopic
            
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"{self.client_id}-admin"
            )
            
            topic_obj = NewTopic(
                name=topic,
                num_partitions=num_partitions,
                replication_factor=replication_factor
            )
            
            admin_client.create_topics([topic_obj])
            admin_client.close()
            
            print(f"✅ 主题创建成功: {topic}")
            return True
            
        except Exception as e:
            if "TopicAlreadyExistsError" in str(type(e)):
                print(f"⚠️  主题已存在: {topic}")
                return True
            
            print(f"❌ 创建主题失败: {str(e)}")
            return False
    
    def list_topics(self) -> List[str]:
        """列出所有主题"""
        try:
            from kafka.admin import KafkaAdminClient
            
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"{self.client_id}-admin"
            )
            
            topics = admin_client.list_topics()
            admin_client.close()
            
            return topics
            
        except Exception as e:
            print(f"❌ 获取主题列表失败: {str(e)}")
            return []
    
    def close(self):
        """关闭连接"""
        if self._producer:
            self._producer.close()
            self._producer = None


# 便捷函数
def send_event(event_type: str, event_data: Dict[str, Any], user_id: str = None):
    """
    发送事件到 Kafka
    
    Args:
        event_type: 事件类型
        event_data: 事件数据
        user_id: 用户 ID
    """
    client = KafkaClient()
    
    event = {
        'event_type': event_type,
        'event_data': event_data,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }
    
    return client.send('events', event, key=user_id)


def send_analytics(metric_name: str, value: float, tags: Dict[str, str] = None):
    """
    发送分析指标
    
    Args:
        metric_name: 指标名称
        value: 指标值
        tags: 标签
    """
    client = KafkaClient()
    
    metric = {
        'metric_name': metric_name,
        'value': value,
        'tags': tags or {},
        'timestamp': datetime.now().isoformat()
    }
    
    return client.send('analytics', metric)


if __name__ == "__main__":
    # 测试连接
    print("测试 Kafka 连接...")
    
    client = KafkaClient()
    
    # 列出主题
    topics = client.list_topics()
    print(f"现有主题: {topics}")
    
    # 创建测试主题
    client.create_topic('test-topic')
    
    # 发送测试消息
    success = client.send('test-topic', {
        'message': 'Hello Kafka!',
        'test': True
    })
    
    if success:
        print("✅ Kafka 测试成功")
    else:
        print("❌ Kafka 测试失败")
        print("请确保 Kafka 服务已启动:")
        print("  docker-compose up -d kafka")
    
    client.close()
