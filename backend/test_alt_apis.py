# -*- coding: utf-8 -*-
"""
测试替代新闻API和更多金融接口
"""
import sys, os, io, json, urllib.request, re, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_url(url, headers=None, desc=""):
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read()
        # Try decode
        for enc in ['utf-8', 'gbk', 'gb2312']:
            try:
                text = raw.decode(enc)
                break
            except:
                continue
        return resp.status, text[:500]
    except Exception as e:
        return None, str(e)


# ====== 新闻API ======
print("="*60)
print("  替代新闻API测试")
print("="*60)

# 1. 韩松API（免费新闻聚合）
print("\n1. 韩松 NewsAPI (hongsong)")
s, r = test_url("https://api.vvhan.com/api/hotlist?type=wbsHot", desc="微博热搜")
print(f"  微博热搜: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("data", [])
        print(f"    Items: {len(items)}")
        for item in items[:3]:
            print(f"    - {str(item.get('title',item))[:50]}")
    except:
        print(f"    Raw: {r[:200]}")

# 2. 今日热榜
print("\n2. 今日热榜 (tophub.today)")
s, r = test_url("https://api.vvhan.com/api/hotlist?type=zhihuHot", desc="知乎热榜")
print(f"  知乎热榜: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("data", [])
        print(f"    Items: {len(items)}")
    except:
        pass

# 3. 36kr 新闻
print("\n3. 36kr 热门新闻")
s, r = test_url("https://36kr.com/api/newsflash", desc="36kr")
print(f"  36kr: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("data",{}).get("items", d.get("data",{}).get("list",[]))
        print(f"    Items: {len(items)}")
    except:
        print(f"    Raw: {r[:200]}")

# 4. 财联社电报
print("\n4. 财联社电报 API")
s, r = test_url("https://www.cls.cn/api/subject/recommend?app=CailianpressWeb&os=web&sv=8.4.6", desc="财联社")
print(f"  财联社: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("data",{}).get("subject_list", d.get("data",{}).get("list",[]))
        print(f"    Items: {len(items)}")
        for item in items[:3]:
            if isinstance(item, dict):
                print(f"    - {item.get('title','?')[:50]}")
    except:
        print(f"    Raw: {r[:200]}")

# 5. 知创 API (学术新闻)
print("\n5. 知网热词 API")
s, r = test_url("https://api.vvhan.com/api/hotlist?type=baiduHot", desc="百度热搜")
print(f"  百度热搜: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("data", [])
        print(f"    Items: {len(items)}")
    except:
        pass

# ====== 金融API ======
print("\n" + "="*60)
print("  更多金融API测试")
print("="*60)

# 6. 东方财富 板块涨跌
print("\n6. 东方财富板块行情")
s, r = test_url("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f2,f3,f4,f12,f14")
print(f"  板块: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("data",{}).get("diff",[])
        print(f"    Items: {len(items)}")
        for item in items[:5]:
            print(f"    - {item.get('f14','?')}: {item.get('f3','')}")
    except:
        print(f"    Raw: {r[:200]}")

# 7. 东方财富 龙虎榜
print("\n7. 东方财富涨停股")
s, r = test_url("https://push2ex.eastmoney.com/getTopicBKDaily?ut=7eea3edcaed734bea9004fcfb7d45613&dession=20260424&_=1745500000000")
print(f"  龙虎榜: {s}")

# 8. 上交所 公告
print("\n8. 上交所公告")
s, r = test_url("https://query.sse.com.cn/sseQuery/commonQuery.do?isPagination=true&pageHelp.beginPage=1&pageHelp.pageSize=5&sqlId=SSE_ZQPJ_YGPG_C_GGXX_L&stockType=1", 
    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.sse.com.cn/"})
print(f"  上交所: {s}")

# 9. Free proxy test (for distributed crawling)
print("\n9. 免费代理池 API")
s, r = test_url("https://www.free-proxy-list.net/", desc="Free proxy")
print(f"  FreeProxy: {s}")

# ====== 电商 API ======
print("\n" + "="*60)
print("  电商API测试（替代方案）")
print("="*60)

# 10. 京东商品评价API
print("\n10. 京东评价API")
s, r = test_url("https://club.jd.com/comment/productCommentSummaries.action?referenceIds=100012043978",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
print(f"  评价API: {s}")
if s == 200:
    try:
        d = json.loads(r)
        items = d.get("CommentsCount",[])
        print(f"    Items: {len(items)}")
    except:
        print(f"    Raw: {r[:200]}")

# 11. 拼多多搜索
print("\n11. 拼多多搜索API")
import httpx
async def test_pdd():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 拼多多移动端搜索
            resp = await client.get(
                "https://mobile.yangkeduo.com/proxy/api/search",
                params={"q": "phone", "page": 1, "size": 20},
                headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.16.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"}
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                print(f"    OK: {len(items)} products")
            else:
                print(f"    Status: {resp.status_code}")
    except Exception as e:
        print(f"    FAIL: {str(e)[:80]}")
asyncio.run(test_pdd())

# 12. 大麦网/当当等
print("\n12. 当当网搜索API")
s, r = test_url("http://search.dangdang.com/?key=手机&act=input&sort_type=sort_score_asc",
    headers={"User-Agent": "Mozilla/5.0"})
print(f"  当当网: {s}")
if s == 200 and len(r) > 100:
    # parse
    titles = re.findall(r'title="([^"]{5,})"', r)
    prices = re.findall(r'¥(\d+\.?\d*)', r)
    print(f"    Titles: {len(titles)}, Prices: {len(prices)}")
    if titles:
        print(f"    Sample: {titles[0][:50]}")

print("\n" + "="*60)
print("  DONE")
print("="*60)
