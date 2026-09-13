# -*- coding: utf-8 -*-
"""
爬虫真实数据能力测试 - 逐个验证每个爬虫能否抓到真实数据
"""
import sys, os, io, json, asyncio, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import Database

db = Database()

def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =====================================================
# 1. 东方财富 - 股票K线
# =====================================================
separator("1. 东方财富股票K线 (eastmoney)")
import urllib.request, re

codes = [("600519","1","贵州茅台"),("000001","0","平安银行"),("601318","1","中国平安"),("300750","0","宁德时代"),("002594","0","比亚迪")]
total = 0
for code, prefix, name in codes:
    try:
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={prefix}.{code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=10"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(re.search(r'\{.*\}', resp.read().decode()).group())
        klines = data.get("data",{}).get("klines",[])
        if klines:
            print(f"  OK {name}({code}): {len(klines)} 条, 最新={klines[-1][:10]}...")
            total += len(klines)
        else:
            print(f"  EMPTY {name}({code}): 0 条")
    except Exception as e:
        print(f"  FAIL {name}({code}): {e}")
print(f"  => Real API: {total} total records")


# =====================================================
# 2. 新浪财经 - 指数行情
# =====================================================
separator("2. 新浪财经指数 (sina)")

index_codes = {
    "sh000001": "上证指数", "sz399001": "深证成指", "sh000300": "沪深300",
    "sz399006": "创业板指", "sh000688": "科创50", "sh000016": "上证50"
}
try:
    codes_str = ",".join(index_codes.keys())
    url = f"https://hq.sinajs.cn/list={codes_str}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("gbk")
    count = 0
    for line in raw.strip().split("\n"):
        m = re.search(r'"([^"]+)"', line)
        if m:
            parts = m.group(1).split(",")
            if len(parts) > 3:
                name = parts[0]
                price = parts[3]
                count += 1
                print(f"  OK {name}: {price}")
    if count == 0:
        print("  FAIL: 0 records parsed")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 3. 京东 - 商品搜索
# =====================================================
separator("3. 京东商品搜索 (jd)")

import httpx
try:
    async def test_jd():
        url = "https://search.jd.com/Search"
        params = {"keyword": "手机", "enc": "utf-8", "page": 1}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            html = resp.text
            # 检查真实数据
            sku_pattern = r'data-sku="(\d+)"'
            skus = re.findall(sku_pattern, html)
            title_pattern = r'<em>([^<]{5,})</em>'
            titles = re.findall(title_pattern, html)
            print(f"  HTML length: {len(html)}")
            print(f"  SKU count: {len(skus)}")
            print(f"  Title count: {len(titles)}")
            if skus:
                print(f"  Sample SKUs: {skus[:3]}")
            if titles:
                print(f"  Sample titles: {titles[:3]}")
            if not skus and not titles:
                # Check if we got a login/captcha page
                if "验证" in html or "login" in html.lower() or "滑动" in html:
                    print("  BLOCKED: Anti-crawl detected (captcha/login)")
                else:
                    print("  EMPTY: No product data found")
            return len(skus) > 0
    ok = asyncio.run(test_jd())
    print(f"  => Real data: {'YES' if ok else 'NO (needs JS rendering)'}")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 4. 淘宝 - 搜索建议API
# =====================================================
separator("4. 淘宝搜索建议 (taobao)")

try:
    async def test_taobao():
        url = "https://suggest.taobao.com/sug"
        params = {"q": "手机", "code": "utf-8"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.taobao.com/"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            data = resp.json()
            result = data.get("result", [])
            print(f"  Suggestions: {len(result)}")
            if result:
                for r in result[:3]:
                    print(f"    - {r[0]}")
            return len(result) > 0
    ok = asyncio.run(test_taobao())
    print(f"  => Real API: {'YES (suggestions only)' if ok else 'NO'}")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 5. 网易新闻 - 分类API
# =====================================================
separator("5. 网易新闻 (netease)")

cat_urls = {
    "科技": "https://tech.163.com/special/00097DHA/news_data.js",
    "财经": "https://money.163.com/special/00251U62/news_data.js",
}
for cat, url in cat_urls.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode("utf-8")
        # JSONP format
        m = re.search(r'\((.*)\)', raw.strip())
        if m:
            data = json.loads(m.group(1))
            items = data if isinstance(data, list) else data.get("推荐", data.get("list", []))
            print(f"  OK {cat}: {len(items)} news")
        else:
            print(f"  FAIL {cat}: Cannot parse JSONP")
    except Exception as e:
        print(f"  FAIL {cat}: {e}")


# =====================================================
# 6. 网易新闻热点 (rank API)
# =====================================================
separator("6. 网易热点新闻 (netease hot)")

try:
    url = "https://news.163.com/rank/getHotList.do"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    items = data.get("list", data.get("data", []))
    print(f"  OK: {len(items)} hot news")
    if items:
        for item in items[:3]:
            t = item.get("title", item.get("docurl", "?"))[:50]
            print(f"    - {t}")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 7. 百度新闻 API
# =====================================================
separator("7. 百度新闻 (baidu news)")

try:
    url = "https://news.baidu.com/widget?id=TopNews&ajax=json"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    items = data.get("data", data.get("list", data.get("TopNews", {}).get("items", [])))
    if isinstance(items, dict):
        items = items.get("items", items.get("list", []))
    if isinstance(items, str):
        items = json.loads(items) if items else []
    print(f"  OK: {len(items)} news")
    if items:
        for item in items[:3]:
            if isinstance(item, dict):
                t = item.get("title", item.get("name", "?"))[:50]
            else:
                t = str(item)[:50]
            print(f"    - {t}")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 8. 国家电网 - Sina行情
# =====================================================
separator("8. 电力股行情 (sina hq)")

power_codes = {
    "sh600900": "长江电力", "sh600795": "国电电力", "sh600886": "国投电力",
    "sh600025": "华能水电", "sh600905": "三峡能源"
}
try:
    codes_str = ",".join(power_codes.keys())
    url = f"https://hq.sinajs.cn/list={codes_str}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("gbk")
    count = 0
    for line in raw.strip().split("\n"):
        m = re.search(r'"([^"]+)"', line)
        if m:
            parts = m.group(1).split(",")
            if len(parts) > 3:
                name = parts[0]
                price = parts[3]
                change = parts[8]
                count += 1
                print(f"  OK {name}: {price} ({change}%)")
    if count == 0:
        print("  FAIL: 0 records")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 9. Tushare - 专业金融数据 (免费API)
# =====================================================
separator("9. Tushare 金融数据接口 (tushare.pro)")

# Tushare 需要注册 token，测试公开接口
try:
    # 免费 STK_LIST 接口
    url = "https://api.tushare.pro"
    payload = json.dumps({"api_name": "stock_basic", "token": "", "params": {"list_status": "L"}, "fields": "ts_code,symbol,name,area,industry"})
    req = urllib.request.Request(url, data=payload.encode(), headers={
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    })
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    items = data.get("data", {}).get("items", [])
    print(f"  OK: {len(items)} stocks (no token = limited)")
except Exception as e:
    print(f"  INFO: {str(e)[:80]}")


# =====================================================
# 10. 新浪K线历史数据
# =====================================================
separator("10. 新浪股票历史K线 (sina history)")

try:
    url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    params = "symbol=sh600519&scale=240&ma=no&datalen=5"
    full_url = f"{url}?{params}"
    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    print(f"  OK: {len(data)} K-line records")
    for d in data[:3]:
        print(f"    {d.get('day','')}: open={d.get('open','')} close={d.get('close','')}")
except Exception as e:
    print(f"  FAIL: {e}")


# =====================================================
# 11. 快手/抖音商品搜索 (开放API)
# =====================================================
separator("11. 拼多多商品 (PDD API test)")

try:
    # 拼多多开放平台搜索（需要API key，测试公开接口）
    url = "https://mobile.yangkeduo.com/proxy/api/search?q=手机&page=1&size=20"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.16.15"
    })
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    items = data.get("items", data.get("list", []))
    print(f"  OK: {len(items)} products")
except Exception as e:
    print(f"  FAIL: {str(e)[:80]}")


# =====================================================
# SUMMARY
# =====================================================
separator("SUMMARY")
print("""
| 数据源 | 真实API | 说明 |
|--------|---------|------|
| 东方财富(股票K线) | YES | push2his.eastmoney.com |
| 新浪财经(指数) | YES | hq.sinajs.cn |
| 新浪K线(历史) | YES | money.finance.sina.com.cn |
| 网易新闻(分类) | MAYBE | JSONP接口可能变化 |
| 网易热点 | MAYBE | getHotList.do |
| 百度新闻 | YES | news.baidu.com/widget |
| 电力股(新浪) | YES | hq.sinajs.cn |
| 京东商品 | BLOCKED | 需JS渲染/登录 |
| 淘宝商品 | BLOCKED | 强反爬 |
""")
