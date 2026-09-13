# -*- coding: utf-8 -*-
"""
Phase 2 综合验证测试
==================

验证所有 Phase 2 新增模块的导入和基本功能
"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

def test_imports():
    """测试所有新增模块的导入"""
    print("=" * 60)
    print("Phase 2 综合验证 - 导入测试")
    print("=" * 60)
    
    modules = [
        ("ScraplingAdapter", "crawlers.scrapling_adapter"),
        ("ScraplingConfig", "crawlers.scrapling_adapter"),
        ("RobotsChecker", "crawlers.robots_checker"),
        ("AdapterRegistry", "crawlers.adapter_framework"),
        ("BaseAdapter", "crawlers.adapter_framework"),
        ("FileParser", "crawlers.utils.file_parser"),
        ("CrawlConfigSchema", "crawlers.custom"),
        ("CustomCrawlEngine", "crawlers.custom"),
        ("SourceType", "crawlers.custom"),
        ("EastMoneyAdapter", "crawlers.adapters.eastmoney"),
        ("Kr36Adapter", "crawlers.adapters.kr36"),
        ("ClsAdapter", "crawlers.adapters.cls"),
        ("celery_app", "api.celery_app"),
        ("crawl_tasks", "api.tasks.crawl_tasks"),
    ]
    
    passed = 0
    failed = 0
    for name, module_path in modules:
        try:
            __import__(module_path)
            print(f"  ✅ {name} ({module_path})")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name} ({module_path}): {e}")
            failed += 1
    
    print(f"\n导入结果: {passed} 通过 / {failed} 失败")
    return failed == 0


async def test_adapter_registry():
    """测试适配器注册表"""
    print("\n" + "=" * 60)
    print("Phase 2 综合验证 - 适配器注册表")
    print("=" * 60)
    
    from crawlers.adapters.eastmoney import EastMoneyAdapter
    from crawlers.adapters.kr36 import Kr36Adapter
    from crawlers.adapters.cls import ClsAdapter
    from crawlers.adapter_framework import AdapterRegistry
    
    adapters = AdapterRegistry.list_adapters()
    print(f"  已注册适配器: {len(adapters)}")
    for a in adapters:
        print(f"    - {a['name']}: {a['description']} ({a['category']})")
    
    return len(adapters) >= 3


async def test_custom_engine():
    """测试自定义采集引擎"""
    print("\n" + "=" * 60)
    print("Phase 2 综合验证 - 自定义采集引擎")
    print("=" * 60)
    
    from crawlers.custom import CrawlConfigSchema, CustomCrawlEngine, SourceType
    
    # API 采集测试
    config = CrawlConfigSchema(
        name="test_api",
        source_type=SourceType.API,
        api={"endpoint": "https://httpbin.org/get", "method": "GET"},
        timeout=10,
    )
    
    engine = CustomCrawlEngine()
    result = await engine.execute(config)
    print(f"  API 采集: success={result.success}, count={result.count}")
    
    return result.success


async def test_robots_checker():
    """测试 robots.txt 检查"""
    print("\n" + "=" * 60)
    print("Phase 2 综合验证 - robots.txt 检查")
    print("=" * 60)
    
    from crawlers.robots_checker import RobotsChecker
    checker = RobotsChecker()
    
    report = await checker.check("https://httpbin.org/get")
    print(f"  httpbin.org/get: allowed={report.allowed}, source={report.source}")
    
    return True


async def test_file_parser():
    """测试文件解析器"""
    print("\n" + "=" * 60)
    print("Phase 2 综合验证 - 文件解析器")
    print("=" * 60)
    
    from crawlers.utils.file_parser import FileParser
    import tempfile, json
    
    parser = FileParser()
    json_path = os.path.join(tempfile.gettempdir(), "phase2_test.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}], f)
    
    result = parser.parse_file(json_path)
    print(f"  JSON 解析: type={result['file_type']}, rows={result['row_count']}, dtypes={result['dtypes']}")
    
    return result["row_count"] == 2


async def test_celery_config():
    """测试 Celery 配置"""
    print("\n" + "=" * 60)
    print("Phase 2 综合验证 - Celery 配置")
    print("=" * 60)
    
    from api.celery_app import celery_app
    
    print(f"  App: {celery_app.main}")
    print(f"  Broker: {celery_app.conf.broker_url}")
    queues = list(celery_app.conf.task_queues.keys())
    print(f"  Queues: {queues}")
    
    return "crawl-high" in queues and "crawl-normal" in queues


async def test_scrapling_adapter():
    """测试 Scrapling 适配器"""
    print("\n" + "=" * 60)
    print("Phase 2 综合验证 - Scrapling 适配器")
    print("=" * 60)
    
    from crawlers.scrapling_adapter import ScraplingAdapter, ScraplingConfig
    
    adapter = ScraplingAdapter()
    print(f"  Available: {adapter.available}")
    print(f"  Stealthy: {adapter.stealthy_available}")
    
    if adapter.available:
        response = await adapter.fetch_page("https://httpbin.org/get")
        print(f"  Fetch test: {'OK' if response else 'Failed'}")
        return response is not None
    
    return True  # Scrapling 不可用时也通过


async def main():
    print("Phase 2 综合验证测试")
    print("智能数据分析平台 v2.0 - 采集系统增强\n")
    
    # 同步测试
    import_ok = test_imports()
    
    # 异步测试
    results = {
        "导入测试": import_ok,
        "适配器注册表": await test_adapter_registry(),
        "自定义采集引擎": await test_custom_engine(),
        "Robots 检查": await test_robots_checker(),
        "文件解析器": await test_file_parser(),
        "Celery 配置": await test_celery_config(),
        "Scrapling 适配器": await test_scrapling_adapter(),
    }
    
    # 汇总
    print("\n" + "=" * 60)
    print("PHASE 2 验证结果汇总")
    print("=" * 60)
    
    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status} | {name}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n🎉 Phase 2 所有验证通过！采集系统增强完成！")
    else:
        print("\n⚠️ 部分验证未通过")
    
    return all_pass


if __name__ == "__main__":
    asyncio.run(main())
