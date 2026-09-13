"""
数据库连接测试脚本
测试 PostgreSQL、ClickHouse、Kafka、Redis 连接
"""
import os
import sys
import json
from datetime import datetime

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def test_postgresql():
    """测试 PostgreSQL 连接"""
    print("=" * 60)
    print("🐘 测试 PostgreSQL 连接")
    print("=" * 60)
    
    try:
        import psycopg2
        
        # 获取连接信息
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "data_platform")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        # 连接数据库
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=db,
            user=user,
            password=password,
            connect_timeout=5
        )
        
        # 测试查询
        cursor = conn.cursor()
        cursor.execute("SELECT version(), current_database(), current_user")
        version, database, current_user = cursor.fetchone()
        
        # 获取表列表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ PostgreSQL 连接成功")
        print(f"   版本: {version.split()[0]}")
        print(f"   主机: {host}:{port}")
        print(f"   数据库: {database}")
        print(f"   用户: {current_user}")
        print(f"   表数量: {len(tables)}")
        if tables:
            print(f"   表列表: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("⚠️  未安装 psycopg2")
        print("   安装命令: pip install psycopg2-binary")
        return False
        
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {str(e)}")
        print(f"   请确保 PostgreSQL 服务已启动:")
        print(f"   docker-compose up -d postgres")
        return False


def test_sqlalchemy():
    """测试 SQLAlchemy 连接"""
    print("\n" + "=" * 60)
    print("🔗 测试 SQLAlchemy 连接")
    print("=" * 60)
    
    try:
        from sqlalchemy import create_engine, text
        
        # 使用与应用相同的配置
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/data_platform"
        )
        
        print(f"   连接 URL: {DATABASE_URL[:50]}...")
        
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        
        # 测试连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test, current_timestamp as time"))
            row = result.fetchone()
            
        print(f"✅ SQLAlchemy 连接成功")
        print(f"   测试查询: {row.test}")
        print(f"   服务器时间: {row.time}")
        return True
        
    except ImportError:
        print("⚠️  未安装 SQLAlchemy")
        print("   安装命令: pip install sqlalchemy")
        return False
        
    except Exception as e:
        print(f"❌ SQLAlchemy 连接失败: {str(e)}")
        return False


def test_clickhouse():
    """测试 ClickHouse 连接"""
    print("\n" + "=" * 60)
    print("🚀 测试 ClickHouse 连接")
    print("=" * 60)
    
    try:
        from clickhouse_client import ClickHouseClient
        
        client = ClickHouseClient()
        
        print(f"   连接地址: {client.base_url}")
        
        # 测试连接
        if not client.ping():
            print(f"❌ ClickHouse 连接失败")
            print(f"   请确保 ClickHouse 服务已启动:")
            print(f"   docker-compose up -d clickhouse")
            return False
        
        print(f"✅ ClickHouse 连接成功")
        
        # 测试查询
        result = client.query("SELECT 1 as test, now() as time")
        if result:
            print(f"   测试查询: {result[0]}")
        
        # 获取数据库列表
        databases = client.query("SHOW DATABASES")
        db_names = [db['name'] for db in databases]
        print(f"   数据库列表: {', '.join(db_names[:5])}")
        
        return True
        
    except ImportError:
        print("⚠️  未找到 clickhouse_client 模块")
        return False
        
    except Exception as e:
        print(f"❌ ClickHouse 连接失败: {str(e)}")
        print(f"   请确保 ClickHouse 服务已启动:")
        print(f"   docker-compose up -d clickhouse")
        return False


def test_kafka():
    """测试 Kafka 连接"""
    print("\n" + "=" * 60)
    print("📨 测试 Kafka 连接")
    print("=" * 60)
    
    try:
        from kafka_client import KafkaClient
        
        client = KafkaClient()
        
        print(f"   服务器: {client.bootstrap_servers}")
        
        # 列出主题
        topics = client.list_topics()
        print(f"   现有主题: {topics if topics else '无'}")
        
        # 创建测试主题
        client.create_topic('test-topic')
        
        # 发送测试消息
        test_msg = {
            'message': 'Hello Kafka!',
            'test': True,
            'time': datetime.now().isoformat()
        }
        
        success = client.send('test-topic', test_msg)
        
        if success:
            print(f"✅ Kafka 连接成功")
            print(f"   测试消息已发送")
        else:
            print(f"❌ Kafka 消息发送失败")
        
        client.close()
        return success
        
    except ImportError:
        print("⚠️  未找到 kafka_client 模块")
        return False
        
    except Exception as e:
        print(f"❌ Kafka 连接失败: {str(e)}")
        print(f"   请确保 Kafka 服务已启动:")
        print(f"   docker-compose up -d kafka")
        return False


def test_redis():
    """测试 Redis 连接"""
    print("\n" + "=" * 60)
    print("⚡ 测试 Redis 连接")
    print("=" * 60)
    
    try:
        import redis
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        
        print(f"   服务器: {host}:{port}")
        
        r = redis.Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # 测试连接
        if r.ping():
            print(f"✅ Redis 连接成功")
            
            # 获取信息
            info = r.info()
            print(f"   版本: {info.get('redis_version')}")
            print(f"   模式: {info.get('redis_mode')}")
            print(f"   已用内存: {info.get('used_memory_human')}")
            
            # 测试读写
            r.set('test_key', 'Hello Redis!')
            value = r.get('test_key')
            print(f"   测试读写: {value}")
            r.delete('test_key')
            
            return True
        else:
            print(f"❌ Redis 连接失败")
            return False
            
    except ImportError:
        print("⚠️  未安装 redis")
        print("   安装命令: pip install redis")
        return False
        
    except Exception as e:
        print(f"❌ Redis 连接失败: {str(e)}")
        print(f"   请确保 Redis 服务已启动:")
        print(f"   docker-compose up -d redis")
        return False


def test_mongodb():
    """测试 MongoDB 连接"""
    print("\n" + "=" * 60)
    print("🍃 测试 MongoDB 连接")
    print("=" * 60)
    
    try:
        from pymongo import MongoClient
        
        mongo_url = os.getenv(
            "MONGO_URL",
            "mongodb://admin:admin123@localhost:27017"
        )
        
        print(f"   连接 URL: {mongo_url[:40]}...")
        
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        
        # 测试连接
        client.admin.command('ping')
        
        print(f"✅ MongoDB 连接成功")
        
        # 获取数据库列表
        dbs = client.list_database_names()
        print(f"   数据库列表: {', '.join(dbs[:5])}")
        
        client.close()
        return True
        
    except ImportError:
        print("⚠️  未安装 pymongo")
        print("   安装命令: pip install pymongo")
        return False
        
    except Exception as e:
        print(f"❌ MongoDB 连接失败: {str(e)}")
        print(f"   请确保 MongoDB 服务已启动:")
        print(f"   docker-compose up -d mongodb")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 智能数据分析平台 - 数据库连接测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "PostgreSQL": test_postgresql(),
        "SQLAlchemy": test_sqlalchemy(),
        "ClickHouse": test_clickhouse(),
        "Kafka": test_kafka(),
        "Redis": test_redis(),
        "MongoDB": test_mongodb(),
    }
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:15} {status}")
    
    # 统计
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！数据库配置正确。")
    else:
        print("\n⚠️  部分测试失败")
        print("\n启动所有服务命令:")
        print("  docker-compose up -d")
        print("\n或单独启动:")
        print("  docker-compose up -d postgres clickhouse kafka redis mongodb")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
