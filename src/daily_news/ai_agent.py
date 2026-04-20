# src/daily_news/ai_agent.py
# 每日要闻AI增强模块 - 提供摘要精炼、思政解读、智能分类、知识点推荐、语义评分

import json
import re
from dataclasses import dataclass

from ..clients import openai_client
from ..config import settings

# ==================== 配置 ====================

@dataclass(frozen=True)
class NewsAIConfig:
    """AI增强模块配置"""
    model: str = settings.fast_model  # 使用主项目的快速模型
    max_retries: int = 2
    timeout: int = 30


news_ai_config = NewsAIConfig()

# 模块是否可用
AI_ENHANCEMENT_AVAILABLE = True


# ==================== 思政分类标签体系 ====================

NEWS_CATEGORIES = {
    "经济建设": ["经济发展", "高质量发展", "新质生产力", "数字经济", "产业升级", "区域发展", "投资", "消费"],
    "政治建设": ["党的建设", "全面从严治党", "反腐倡廉", "法治建设", "基层治理", "政府工作", "政策解读"],
    "文化建设": ["文化自信", "文明创建", "文化传承", "意识形态", "宣传思想", "网络文化", "文艺创作"],
    "社会建设": ["民生保障", "就业创业", "教育发展", "医疗卫生", "社会保障", "社会治理", "青年发展"],
    "生态文明": ["生态文明", "绿色发展", "环境保护", "双碳目标", "美丽中国", "乡村振兴"],
    "国防外交": ["国防建设", "军队建设", "大国外交", "国际关系", "一带一路", "全球治理"],
    "党建理论": ["理论学习", "主题教育", "党员教育", "基层党组织", "干部队伍建设"],
    "青年成长": ["青年就业", "青年发展", "大学生", "创新创业", "青年担当", "青春奋斗"],
}


# ==================== 思政知识库映射 ====================

IDEOLOGY_KNOWLEDGE_MAP = {
    "马克思主义基本原理": ["唯物辩证法", "认识论", "实践观", "矛盾论", "社会发展规律", "剩余价值", "科学社会主义"],
    "毛泽东思想": ["新民主主义革命", "社会主义改造", "群众路线", "实事求是", "独立自主", "人民民主专政"],
    "中国特色社会主义理论体系": ["邓小平理论", "三个代表", "科学发展观", "习近平新时代中国特色社会主义思想"],
    "中国近现代史纲要": ["近代中国历史", "革命道路", "改革开放史", "党史学习"],
    "思想道德与法治": ["理想信念", "爱国主义", "社会主义核心价值观", "公民道德", "法治精神"],
}


# ==================== AI增强功能模块 ====================

def enhance_summary(title: str, original_summary: str, source: str = "") -> str:
    """使用AI精炼新闻摘要"""
    if original_summary and "点击查看新闻原文" not in original_summary:
        if 40 <= len(original_summary) <= 100:
            return original_summary

    prompt = f"""你是一位思政教育新闻编辑。请根据新闻标题，生成一段50-80字的新闻摘要。

新闻标题：{title}
新闻来源：{source}
原始摘要：{original_summary if original_summary and "点击查看" not in original_summary else "无"}

要求：
1. 概括新闻核心内容，语言简洁有力
2. 突出与青年学生相关的社会意义
3. 避免使用"据悉"、"据报道"等套话开头
4. 直接输出摘要内容，不要加引号或其他格式"""

    try:
        response = openai_client.chat.completions.create(
            model=news_ai_config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        result = response.choices[0].message.content.strip()
        if len(result) > 100:
            result = result[:97] + "..."
        return result
    except Exception as e:
        print(f"[NewsAI] 摘要精炼失败: {e}")
        return original_summary if original_summary else f"《{title}》一文报道了相关时政要闻，点击查看详情。"


def generate_interpretation(title: str, summary: str, source: str = "") -> str:
    """生成思政知识点解读"""
    prompt = f"""你是一位思政教育专家。请从思想政治理论角度解读这条新闻的教育意义。

新闻标题：{title}
新闻摘要：{summary}
新闻来源：{source}

要求：
1. 关联马克思主义基本原理、毛泽东思想或中国特色社会主义理论体系
2. 突出对青年学生的教育启示
3. 语言精炼，60-100字
4. 直接输出解读内容，不要加标题或格式

示例输出：
这一报道体现了党中央对青年发展的高度重视，反映了新时代人才强国战略的深入推进。从唯物辩证法角度看，这是把握事物发展规律、积极发挥主观能动性的生动实践，激励青年学子将个人理想融入国家发展大局。"""

    try:
        response = openai_client.chat.completions.create(
            model=news_ai_config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[NewsAI] 思政解读生成失败: {e}")
        return "该新闻反映了国家发展战略与青年成长的紧密关联，有助于理解中国特色社会主义理论体系的实践价值。"


def classify_news_category(title: str, summary: str) -> str:
    """智能分类新闻标签"""
    categories_str = "、".join(NEWS_CATEGORIES.keys())

    prompt = f"""请分析这条新闻，从以下分类中选择最合适的一个类别。

新闻标题：{title}
新闻摘要：{summary}

可选分类：{categories_str}

要求：
1. 只输出分类名称，不要其他内容
2. 如果难以判断，选择"社会建设"
3. 直接输出分类名，如：经济建设"""

    try:
        response = openai_client.chat.completions.create(
            model=news_ai_config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1,
        )
        result = response.choices[0].message.content.strip()
        if result in NEWS_CATEGORIES:
            return result
        for cat in NEWS_CATEGORIES:
            if cat in result or result in cat:
                return cat
        return "社会建设"
    except Exception as e:
        print(f"[NewsAI] 分类失败: {e}")
        return "社会建设"


def recommend_knowledge_points(title: str, summary: str) -> list:
    """推荐相关思政知识点"""
    knowledge_str = "\n".join([f"- {k}: {', '.join(v[:3])}" for k, v in IDEOLOGY_KNOWLEDGE_MAP.items()])

    prompt = f"""请分析这条新闻，推荐最相关的思政理论知识点。

新闻标题：{title}
新闻摘要：{summary}

知识库参考：
{knowledge_str}

要求：
1. 从知识库中选择2-3个最相关的知识点
2. 优先选择具体的理论概念而非大类
3. 格式：JSON数组，如["矛盾论", "实践观", "青年担当"]
4. 只输出JSON数组，不要其他内容"""

    try:
        response = openai_client.chat.completions.create(
            model=news_ai_config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        result = response.choices[0].message.content.strip()
        try:
            points = json.loads(result)
            if isinstance(points, list):
                return points[:3]
        except json.JSONDecodeError:
            matches = re.findall(r'"([^"]+)"', result)
            if matches:
                return matches[:3]
        return ["时事热点", "理论学习"]
    except Exception as e:
        print(f"[NewsAI] 知识点推荐失败: {e}")
        return ["时事热点"]


def calculate_relevance_score(title: str, summary: str) -> int:
    """语义评分：评估新闻与思政教育的相关度"""
    prompt = f"""请评估这条新闻与高校思想政治教育主题的相关程度。

新闻标题：{title}
新闻摘要：{summary}

评估维度：
1. 是否涉及党的理论、路线、方针、政策（30分）
2. 是否与青年学生成长发展相关（25分）
3. 是否体现社会主义核心价值观（25分）
4. 是否具有时事教育价值（20分）

要求：
1. 只输出一个0-100的整数分数
2. 不要输出任何其他内容
3. 分数要客观合理"""

    try:
        response = openai_client.chat.completions.create(
            model=news_ai_config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1,
        )
        result = response.choices[0].message.content.strip()
        match = re.search(r'\d+', result)
        if match:
            score = int(match.group())
            return min(100, max(0, score))
        return 50
    except Exception as e:
        print(f"[NewsAI] 语义评分失败: {e}")
        return 50


# ==================== 综合增强函数 ====================

def enhance_news_item(news_item: dict, enable_all: bool = True) -> dict:
    """对单条新闻进行全方位AI增强"""
    title = news_item.get("title", "")
    summary = news_item.get("description", "")
    source = news_item.get("source", "")

    enhanced = news_item.copy()

    try:
        enhanced["description"] = enhance_summary(title, summary, source)

        if enable_all:
            enhanced["interpretation"] = generate_interpretation(
                title, enhanced["description"], source
            )
            enhanced["category"] = classify_news_category(title, enhanced["description"])
            enhanced["knowledgePoints"] = recommend_knowledge_points(title, enhanced["description"])
            enhanced["aiScore"] = calculate_relevance_score(title, enhanced["description"])

    except Exception as e:
        print(f"[NewsAI] 增强失败: {e}")

    return enhanced


def enhance_news_list(news_list: list, enable_all: bool = True) -> list:
    """批量增强新闻列表"""
    enhanced_list = []
    for i, item in enumerate(news_list):
        print(f"[NewsAI] 正在增强第 {i+1}/{len(news_list)} 条新闻...")
        enhanced = enhance_news_item(item, enable_all)
        enhanced_list.append(enhanced)

    if enable_all:
        enhanced_list.sort(key=lambda x: x.get("aiScore", 50), reverse=True)

    return enhanced_list
