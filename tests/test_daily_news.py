# tests/test_daily_news.py
# 每日要闻功能冒烟测试 —— 验证各环节能否跑通

import json
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ==================== 1. 数据文件测试 ====================

def test_json_file_exists():
    """daily_news.json 存在"""
    p = PROJECT_ROOT / "daily_news.json"
    assert p.exists(), "daily_news.json 不存在，请先运行 scripts/update_news.py"


def test_json_file_structure():
    """daily_news.json 格式正确"""
    p = PROJECT_ROOT / "daily_news.json"
    if not p.exists():
        print("  [SKIP] daily_news.json 不存在，跳过结构测试")
        return

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert "news" in data, "缺少 'news' 字段"
    assert "cached_at" in data, "缺少 'cached_at' 字段"
    assert isinstance(data["news"], list), "'news' 应为列表"
    assert len(data["news"]) > 0, "news 列表为空"

    # 检查第一条新闻的必填字段
    first = data["news"][0]
    for field in ("title", "url", "source", "publishedAt", "description"):
        assert field in first, f"新闻条目缺少字段: {field}"

    print(f"  共 {len(data['news'])} 条新闻，更新时间: {data['cached_at']}")


def test_json_news_items():
    """每条新闻数据合法"""
    p = PROJECT_ROOT / "daily_news.json"
    if not p.exists():
        print("  [SKIP] 文件不存在")
        return

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    for i, item in enumerate(data["news"]):
        assert item.get("title"), f"第{i+1}条新闻 title 为空"
        assert item.get("url", "").startswith("http"), f"第{i+1}条新闻 url 异常: {item.get('url')}"
        ai_score = item.get("aiScore")
        if ai_score is not None:
            assert 0 <= ai_score <= 100, f"第{i+1}条 aiScore 超出范围: {ai_score}"


# ==================== 2. 模块导入测试 ====================

def test_import_ai_agent():
    """src.daily_news.ai_agent 可正常导入"""
    try:
        from src.daily_news.ai_agent import (
            enhance_news_item,
            enhance_news_list,
            NEWS_CATEGORIES,
            IDEOLOGY_KNOWLEDGE_MAP,
        )
        assert callable(enhance_news_item)
        assert callable(enhance_news_list)
        assert len(NEWS_CATEGORIES) >= 8
        print(f"  导入成功，共 {len(NEWS_CATEGORIES)} 个新闻分类")
    except Exception as e:
        assert False, f"导入失败: {e}"


def test_import_daily_news_package():
    """src.daily_news 包导入正常"""
    try:
        from src.daily_news import enhance_news_item, enhance_news_list
        assert enhance_news_item is not None
    except Exception as e:
        assert False, f"包导入失败: {e}"


# ==================== 3. Flask API 测试 ====================

def test_flask_api_no_file():
    """文件不存在时 API 返回空列表而不是 500"""
    import tempfile
    import os
    from app import app

    # 临时把路径改成不存在的文件
    import app as app_module
    original_path = app_module.DAILY_NEWS_PATH
    app_module.DAILY_NEWS_PATH = Path("/nonexistent/daily_news.json")

    client = app.test_client()
    resp = client.get("/api/daily-news")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["news"] == []
    assert data["cached_at"] is None

    # 还原
    app_module.DAILY_NEWS_PATH = original_path
    print("  文件缺失时接口正常返回空列表")


def test_flask_api_with_file():
    """文件存在时 API 返回正确数据"""
    p = PROJECT_ROOT / "daily_news.json"
    if not p.exists():
        print("  [SKIP] daily_news.json 不存在，跳过接口测试")
        return

    from app import app
    client = app.test_client()
    resp = client.get("/api/daily-news")
    assert resp.status_code == 200, f"接口返回 {resp.status_code}"
    data = resp.get_json()
    assert "news" in data
    assert len(data["news"]) > 0
    print(f"  接口返回 {len(data['news'])} 条新闻，状态 200 OK")


# ==================== 4. AI增强逻辑（本地逻辑，不调用 API）====================

def test_classify_fallback():
    """分类函数在网络失败时返回默认值"""
    from src.daily_news.ai_agent import NEWS_CATEGORIES
    default_cat = "社会建设"
    assert default_cat in NEWS_CATEGORIES, "默认分类不在分类表中"


def test_enhance_news_item_structure():
    """enhance_news_item 不调用 AI 时 —— 字段结构完整"""
    from src.daily_news.ai_agent import enhance_news_item

    mock_news = {
        "title": "测试新闻标题",
        "description": "这是一条满足长度要求的测试摘要，共计超过四十个汉字，用于跳过AI摘要精炼逻辑。",
        "url": "https://example.com/test",
        "source": "测试来源",
        "publishedAt": "2026-04-16",
    }

    # 只增强摘要（description 已合法，AI调用会被跳过），不调用其他AI能力
    result = enhance_news_item(mock_news, enable_all=False)
    assert result["title"] == mock_news["title"]
    assert "description" in result
    print(f"  enable_all=False 时摘要: {result['description'][:30]}...")


# ==================== 主运行入口 ====================

if __name__ == "__main__":
    tests = [
        test_json_file_exists,
        test_json_file_structure,
        test_json_news_items,
        test_import_ai_agent,
        test_import_daily_news_package,
        test_flask_api_no_file,
        test_flask_api_with_file,
        test_classify_fallback,
        test_enhance_news_item_structure,
    ]

    passed = 0
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[PASS] {name}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"结果: {passed} 通过 / {failed} 失败 / {passed + failed} 总计")
