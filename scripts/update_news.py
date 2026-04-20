#!/usr/bin/env python3
# scripts/update_news.py
# 每日要闻更新脚本 —— 手动运行，爬取新闻 + AI增强 → 写入 daily_news.json
#
# 用法:  python scripts/update_news.py
#        python scripts/update_news.py --no-ai       # 跳过AI增强，只爬取
#        python scripts/update_news.py --dry-run      # 只爬取不写文件

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 项目根目录 & 输出文件
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "daily_news.json"

# ==================== 配置 ====================

NEWS_SOURCES = [
    {"name": "新华网", "url": "https://www.news.cn/politics/", "type": "xinhua"},
    {"name": "求是网", "url": "http://www.qstheory.cn/", "type": "qstheory"},
    {"name": "光明网", "url": "https://politics.gmw.cn/", "type": "gmw"},
]

NEWS_LOOKBACK_DAYS = 3
NEWS_MAX_ITEMS = 8

NEWS_RECOMMEND_KEYWORDS = {
    "强": [
        "习近平", "党中央", "总书记", "中国式现代化", "新时代", "高质量发展", "党的领导", "党的建设",
        "理论学习", "思想政治", "思政", "马克思主义", "意识形态", "文化自信", "四个自信", "两个维护",
        "共同富裕", "教育强国", "青年", "改革", "法治中国"
    ],
    "中": [
        "全国", "中国", "政府工作", "治理", "法治", "乡村振兴", "绿色发展", "生态文明", "人才", "就业",
        "科技创新", "教育", "文明", "宣传", "基层", "社会治理", "开放", "发展", "民生", "国家安全"
    ],
    "弱": ["经济", "文化", "社会", "科技", "开放"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


# ==================== 工具函数 ====================

def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _parse_date_from_text(text: str) -> str:
    if not text:
        return ""
    # 优先识别 YYYYMMDD（如求是网 URL: /20260415/），避免被后续替换破坏
    m8 = re.search(r"(?<![0-9])(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?![0-9])", text)
    if m8:
        try:
            return datetime.strptime(f"{m8.group(1)}-{m8.group(2)}-{m8.group(3)}", "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 再识别 YYYY-MM-DD / YYYY/MM/DD / YYYY年MM月DD日 等带分隔符格式
    text = text.replace("/", "-").replace(".", "-").replace("年", "-").replace("月", "-").replace("日", "")
    match = re.search(r"(20\d{2}-\d{1,2}-\d{1,2})", text)
    if not match:
        return ""
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _is_recent(date_str: str) -> bool:
    if not date_str:
        return False
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    today = datetime.now().date()
    return today - timedelta(days=NEWS_LOOKBACK_DAYS - 1) <= d <= today


def _score(title: str, source: str, published_at: str) -> int:
    s = 0
    for kw in NEWS_RECOMMEND_KEYWORDS["强"]:
        if kw in title: s += 10
    for kw in NEWS_RECOMMEND_KEYWORDS["中"]:
        if kw in title: s += 6
    for kw in NEWS_RECOMMEND_KEYWORDS["弱"]:
        if kw in title: s += 1
    if any(k in title for k in ["习近平", "党中央", "总书记", "中国式现代化", "思想政治", "思政", "马克思主义", "党的建设", "理论学习", "意识形态"]):
        s += 10
    if source == "求是网": s += 3
    elif source == "新华网": s += 4
    elif source == "光明网": s += 2
    if published_at:
        try:
            days = (datetime.now().date() - datetime.strptime(published_at, "%Y-%m-%d").date()).days
            s += max(0, 4 - days)
        except ValueError:
            pass
    return s


def _extract_detail_date(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
        soup = BeautifulSoup(r.text, "html.parser")
        for meta in [
            soup.find("meta", attrs={"name": "publishdate"}),
            soup.find("meta", attrs={"property": "article:published_time"}),
            soup.find("meta", attrs={"name": "PubDate"}),
            soup.find("meta", attrs={"name": "pubdate"}),
        ]:
            if meta and meta.get("content"):
                p = _parse_date_from_text(meta.get("content", ""))
                if p: return p
        for sel in [".time", ".pub_time", ".date", ".fl", ".rm_txt_con .box01", ".box01", "span", "div"]:
            for node in soup.select(sel):
                p = _parse_date_from_text(_clean_text(node.get_text()))
                if p: return p
        p = _parse_date_from_text(r.text)
        if p: return p
    except Exception as e:
        print(f"  [WARN] 日期抓取失败 {url}: {e}")
    return ""


def _extract_summary(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
        soup = BeautifulSoup(r.text, "html.parser")
        candidates = []
        for meta in [
            soup.find("meta", attrs={"name": "description"}),
            soup.find("meta", attrs={"property": "og:description"}),
        ]:
            if meta and meta.get("content"):
                candidates.append(meta.get("content", ""))
        for sel in [".article p", ".rm_txt_con p", ".m-con p", ".u-mainText p", ".content p", ".detail p", "p"]:
            for node in soup.select(sel):
                t = _clean_text(node.get_text())
                if len(t) >= 35:
                    candidates.append(t)
            if candidates:
                break
        for t in candidates:
            c = _clean_text(t)
            if len(c) >= 35:
                return c[:120] + ("..." if len(c) > 120 else "")
    except Exception as e:
        print(f"  [WARN] 摘要抓取失败 {url}: {e}")
    return "点击查看新闻原文，了解完整内容。"


def _build_item(source: str, title: str, url: str, published_at: str) -> dict | None:
    title = _clean_text(title)
    if not title or len(title) < 12 or not url.startswith("http"):
        return None
    if not published_at:
        published_at = _extract_detail_date(url)
    if not published_at or not _is_recent(published_at):
        return None
    print(f"  ✓ {source}: {title[:40]}...")
    return {
        "title": title,
        "url": url,
        "source": source,
        "publishedAt": published_at,
        "description": _extract_summary(url),
        "score": _score(title, source, published_at),
    }


# ==================== 各源抓取 ====================

def _fetch_xinhua() -> list:
    print("[1/3] 抓取新华网...")
    r = requests.get("https://www.news.cn/politics/", headers=HEADERS, timeout=15, verify=False)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, "html.parser")
    items, seen = [], set()
    for link in soup.select("a"):
        title = _clean_text(link.get_text())
        url = urljoin("https://www.news.cn/politics/", link.get("href", "").strip())
        parent_text = " ".join(link.parent.stripped_strings) if link.parent else ""
        pub = _parse_date_from_text(parent_text) or _parse_date_from_text(url)
        if "news.cn" not in url or url in seen:
            continue
        item = _build_item("新华网", title, url, pub)
        if item:
            items.append(item)
            seen.add(url)
    return items


def _fetch_qstheory() -> list:
    print("[2/3] 抓取求是网...")
    try:
        base = "https://www.qstheory.cn/"   # 首页内容最全，/politics/ 子页文章较旧
        r = requests.get(base, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
        soup = BeautifulSoup(r.text, "html.parser")
        items, seen = [], set()
        for link in soup.select("a"):
            title = _clean_text(link.get_text())
            href = link.get("href", "").strip()
            full_url = urljoin("http://www.qstheory.cn", href) if href.startswith("/") else (href if href.startswith("http") else "")
            if not full_url or "qstheory.cn" not in full_url or full_url in seen:
                continue
            if not title or len(title) < 12:
                continue
            pub = _parse_date_from_text(full_url)
            if not pub and link.parent:
                pub = _parse_date_from_text(_clean_text(link.parent.get_text()))
            item = _build_item("求是网", title, full_url, pub)
            if item:
                items.append(item)
                seen.add(full_url)
        return items
    except Exception as e:
        print(f"  [WARN] 求是网抓取失败: {e}")
        return []


def _fetch_gmw() -> list:
    print("[3/3] 抓取光明网...")
    r = requests.get("https://politics.gmw.cn/", headers=HEADERS, timeout=15, verify=False)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, "html.parser")
    items, seen = [], set()
    for link in soup.select("a"):
        title = _clean_text(link.get_text())
        url = urljoin("https://politics.gmw.cn/", link.get("href", "").strip())
        parent_text = " ".join(link.parent.stripped_strings) if link.parent else ""
        pub = _parse_date_from_text(parent_text) or _parse_date_from_text(url)
        if "gmw.cn" not in url or url in seen:
            continue
        item = _build_item("光明网", title, url, pub)
        if item:
            items.append(item)
            seen.add(url)
    return items


# ==================== 主流程 ====================

def fetch_all_news() -> list:
    """抓取所有来源并合并去重、排序"""
    all_news, seen_urls = [], set()
    for fetcher in [_fetch_xinhua, _fetch_qstheory, _fetch_gmw]:
        try:
            for item in fetcher():
                if item["url"] not in seen_urls:
                    all_news.append(item)
                    seen_urls.add(item["url"])
        except Exception as e:
            print(f"  [WARN] {fetcher.__name__} 失败: {e}")

    if not all_news:
        print("\n⚠️  未抓取到新闻！")
        return []

    all_news.sort(key=lambda x: (x.get("score", 0), x.get("publishedAt", "")), reverse=True)
    for item in all_news:
        item.pop("score", None)
    print(f"\n共抓取 {len(all_news)} 条新闻，取前 {NEWS_MAX_ITEMS} 条")
    return all_news[:NEWS_MAX_ITEMS]


def run_ai_enhancement(news_list: list) -> list:
    """调用项目的 AI 增强模块"""
    print("\n" + "=" * 50)
    print("AI 增强处理")
    print("=" * 50)

    # 把项目根目录加入 path，以包路径方式导入（保证相对导入正常工作）
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.daily_news.ai_agent import enhance_news_list

    enhanced = enhance_news_list(news_list, enable_all=True)
    print(f"AI 增强完成，共处理 {len(enhanced)} 条")
    return enhanced


def main():
    parser = argparse.ArgumentParser(description="每日要闻更新脚本")
    parser.add_argument("--no-ai", action="store_true", help="跳过 AI 增强，只爬取")
    parser.add_argument("--dry-run", action="store_true", help="只爬取不写文件")
    args = parser.parse_args()

    print("=" * 50)
    print("每日要闻更新脚本")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出: {OUTPUT_FILE}")
    print("=" * 50 + "\n")

    # Step 1: 爬取
    news_list = fetch_all_news()
    if not news_list:
        print("\n无新闻可处理，退出")
        return

    # Step 2: AI 增强
    if not args.no_ai:
        news_list = run_ai_enhancement(news_list)

    # Step 3: 写入文件
    payload = {
        "cached_at": datetime.now().isoformat(),
        "news": news_list,
        "ai_enhanced": not args.no_ai,
    }

    if args.dry_run:
        print("\n[DRY RUN] 不写入文件，预览结果：")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:2000])
        return

    # 原子写入：先写临时文件，再重命名，避免中途中断损坏数据
    tmp_file = OUTPUT_FILE.with_suffix('.json.tmp')
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp_file.replace(OUTPUT_FILE)

    print(f"\n✅ 已写入 {OUTPUT_FILE}")
    print(f"   新闻条数: {len(news_list)}")
    print(f"   AI增强: {'是' if not args.no_ai else '否'}")


if __name__ == "__main__":
    main()
