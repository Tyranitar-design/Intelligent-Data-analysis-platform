"""
ClickHouse 客户端封装
提供与 ClickHouse 的交互接口
"""
import os
import json
from typing import List, Dict, Any, Optional
from urllib import request, error


class ClickHouseClient:
    """ClickHouse HTTP 客户端"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None
    ):
        self.host = host or os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = port or int(os.getenv("CLICKHOUSE_PORT", "8123"))
        self.database = database or os.getenv("CLICKHOUSE_DB", "data_platform")
        self.user = user or os.getenv("CLICKHOUSE_USER", "default")
        self.password = password or os.getenv("CLICKHOUSE_PASSWORD", "")
        
        self.base_url = f"http://{self.host}:{self.port}"
    
    def _build_url(self, query: str, params: Dict = None) -> str:
        """构建请求 URL"""
        url = f"{self.base_url}/?database={self.database}"
        
        if self.user:
            url += f"&user={self.user}"
        if self.password:
            url += f"&password={self.password}"
        
        # 添加查询参数
        if params:
            for key, value in params.items():
                url += f"&{key}={value}"
        
        return url
    
    def execute(self, query: str, data: str = None) -> str:
        """
        执行 SQL 查询
        
        Args:
            query: SQL 查询语句
            data: 批量插入数据
            
        Returns:
            查询结果字符串
        """
        url = self._build_url(query)
        
        # 编码查询
        encoded_query = request.quote(query, safe='')
        url += f"&query={encoded_query}"
        
        # 构建请求
        req = request.Request(url, data=data.encode('utf-8') if data else None)
        
        try:
            with request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"ClickHouse 查询失败: {error_body}")
    
    def query(self, query: str) -> List[Dict[str, Any]]:
        """
        执行查询并返回结构化结果
        
        Args:
            query: SQL 查询语句
            
        Returns:
            字典列表
        """
        # 添加 FORMAT JSON 以获取结构化结果
        if "FORMAT" not in query.upper():
            query += " FORMAT JSON"
        
        result = self.execute(query)
        
        try:
            data = json.loads(result)
            return data.get('data', [])
        except json.JSONDecodeError:
            # 非 JSON 格式，返回原始数据
            return [{"result": result}]
    
    def insert(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """
        批量插入数据
        
        Args:
            table: 表名
            data: 数据字典列表
            
        Returns:
            是否成功
        """
        if not data:
            return True
        
        # 获取列名
        columns = list(data[0].keys())
        
        # 构建 VALUES 部分
        values_list = []
        for row in data:
            row_values = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    row_values.append("NULL")
                elif isinstance(val, str):
                    row_values.append(f"'{val}'")
                else:
                    row_values.append(str(val))
            values_list.append(f"({', '.join(row_values)})")
        
        query = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES {', '.join(values_list)}
        """
        
        try:
            self.execute(query)
            return True
        except Exception as e:
            print(f"插入失败: {str(e)}")
            return False
    
    def create_table(self, table: str, schema: Dict[str, str], engine: str = "MergeTree") -> bool:
        """
        创建表
        
        Args:
            table: 表名
            schema: 列定义 {列名: 类型}
            engine: 表引擎
            
        Returns:
            是否成功
        """
        columns_def = ",\n".join([f"    {name} {dtype}" for name, dtype in schema.items()])
        
        query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
{columns_def}
        ) ENGINE = {engine}()
        ORDER BY tuple()
        """
        
        try:
            self.execute(query)
            return True
        except Exception as e:
            print(f"创建表失败: {str(e)}")
            return False
    
    def ping(self) -> bool:
        """检查连接"""
        try:
            url = f"{self.base_url}/ping"
            req = request.Request(url)
            with request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except:
            return False


# 全局客户端实例
clickhouse = ClickHouseClient()


if __name__ == "__main__":
    # 测试连接
    client = ClickHouseClient()
    
    print("测试 ClickHouse 连接...")
    if client.ping():
        print("✅ ClickHouse 连接成功")
        
        # 测试查询
        result = client.query("SELECT 1 as test")
        print(f"测试查询结果: {result}")
    else:
        print("❌ ClickHouse 连接失败")
        print("请确保 ClickHouse 服务已启动:")
        print("  docker-compose up -d clickhouse")
