import asyncio
from typing import Dict, List, Any, AsyncGenerator
from .chapter_builders import ChapterBuilderFactory, FlexibleChapterTitleGenerator
from ..retriever import search_theory, search_moment
from ..clients import openai_client
from ..config import settings
import json
import re

class OutlineGenerator:
    def __init__(self):
        pass
    
    def extract_topic(self, query: str) -> str:
        clean_query = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、]', '', query)
        
        patterns = [
            r'关于(.+?)的',
            r'做一个(.+?)(?:的)?PPT',
            r'做一个(.+?)(?:的)?演示',
            r'做一个(.+?)(?:的)?课件',
            r'(.+?)的PPT',
            r'(.+?)PPT',
            r'(.+?)演示文稿',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_query)
            if match:
                topic = match.group(1).strip()
                if topic and len(topic) >= 2 and len(topic) <= 30:
                    return topic
        
        prompt = f"""请从用户的PPT需求中提取核心主题，只返回主题名称，不要其他内容。

用户需求：{query}

示例：
- 用户需求："帮我做一个关于文化自信的PPT" → 返回："文化自信"
- 用户需求："做一个关于新质生产力的演示文稿" → 返回："新质生产力"
- 用户需求："生态文明建设的PPT" → 返回："生态文明建设"
- 用户需求："帮我做一个关于生态文明建设方面的PPT" → 返回："生态文明建设"

请直接返回提取的主题（2-10个字）："""
        
        try:
            response = openai_client.chat.completions.create(
                model=settings.fast_model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens=20
            )
            
            topic = response.choices[0].message.content or ""
            topic = topic.strip().strip('"').strip("'").strip("。").strip("，")
            
            if topic and 2 <= len(topic) <= 30:
                return topic
        except Exception as e:
            print(f"[WARNING] extract_topic LLM failed: {e}")
        
        words = re.findall(r'[\u4e00-\u9fff]+', query)
        if words:
            for word in words:
                if 2 <= len(word) <= 10:
                    return word
        
        return query[:20] if len(query) > 20 else query
    
    async def retrieve_materials(
        self,
        queries: List[str],
        collection: str,
        top_k: int
    ) -> List[Dict]:
        results = []
        for query in queries:
            if collection == "theory":
                items = search_theory(query, [], top_k=top_k)
            else:
                items = search_moment(query, [], top_k=top_k)
            results.extend(items)
        return results[:top_k]
    
    async def generate_chapter_slides(
        self,
        chapter_spec,
        materials: List[Dict],
        topic: str
    ) -> List[Dict]:
        materials_text = "\n".join([
            f"- {m.get('content', '')[:200]}"
            for m in materials[:5]
        ])
        
        prompt = f"""你是一个专业的PPT内容设计师。请为以下章节生成幻灯片内容。

主题：{topic}
章节：{chapter_spec.chapter_title}
章节职责：{chapter_spec.description}
期望幻灯片数量：{chapter_spec.slide_count}

参考材料：
{materials_text}

请生成 {chapter_spec.slide_count} 张幻灯片，每张幻灯片包含：
- title: 标题
- bullets: 3-5个要点
- content_type: 内容类型，可选值：
  - "list": 列表形式（多个并列要点）
  - "hierarchy": 层级结构（有总分关系，第一个是总论点，其他是分论点）
  - "two_column": 两栏对比（适合对比内容）
  - "stat_highlight": 数据强调（适合关键数据）
  - "timeline": 时间线（适合历程、流程）
- layout_hint: 布局建议（可选）
  - "card_grid": 卡片网格（3-6个要点）
  - "icon_list": 图标列表（带视觉图标）
- visual_elements: 视觉元素建议（可选）
  - icons: ["chart", "growth", "target"]  # 建议的图标类型
  - highlight_first: true  # 是否强调第一个要点

返回 JSON 格式：
{{
  "slides": [
    {{
      "title": "...",
      "bullets": ["...", "...", "..."],
      "content_type": "hierarchy",
      "layout_hint": "card_grid",
      "visual_elements": {{
        "icons": ["chart", "growth"],
        "highlight_first": true
      }}
    }}
  ]
}}
"""
        
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model=settings.fast_model,
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        
        response_text = response.choices[0].message.content or ""
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        try:
            result = json.loads(response_text)
            return result.get("slides", [])
        except:
            return []
    
    async def generate_outline(self, topic: str) -> Dict[str, Any]:
        extracted_topic = self.extract_topic(topic)
        
        generated_titles = FlexibleChapterTitleGenerator.generate_titles(extracted_topic)
        
        chapters = []
        for chapter_index in range(1, 7):
            builder = ChapterBuilderFactory.get_builder(chapter_index)
            if not builder:
                continue
            
            spec = builder.get_spec(extracted_topic)
            flexible_title = generated_titles.get(chapter_index, spec.chapter_title)
            
            from dataclasses import replace
            spec = replace(spec, chapter_title=flexible_title)
            
            theory_results = []
            politics_results = []
            
            if spec.theory_weight > 0:
                theory_results = await self.retrieve_materials(
                    queries=spec.retrieval_queries,
                    collection="theory",
                    top_k=max(1, int(5 * spec.theory_weight))
                )
            
            if spec.politics_weight > 0:
                politics_results = await self.retrieve_materials(
                    queries=spec.retrieval_queries,
                    collection="politics",
                    top_k=max(1, int(5 * spec.politics_weight))
                )
            
            all_materials = theory_results + politics_results
            
            slides = await self.generate_chapter_slides(
                chapter_spec=spec,
                materials=all_materials,
                topic=extracted_topic
            )
            
            chapters.append({
                "chapter_index": chapter_index,
                "chapter_title": flexible_title,
                "slides": slides
            })
        
        outline = {
            "title": extracted_topic,
            "original_query": topic,
            "chapters": chapters
        }
        
        return outline
    
    async def generate_outline_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        extracted_topic = self.extract_topic(query)
        
        print(f"[INFO] Extracted topic: '{extracted_topic}' from query: '{query}'")
        
        yield {"type": "start", "topic": extracted_topic}
        
        # 生成灵活的章节标题
        yield {"type": "status", "message": "正在生成章节结构..."}
        generated_titles = FlexibleChapterTitleGenerator.generate_titles(extracted_topic)
        print(f"[INFO] Generated titles: {generated_titles}")
        
        chapters = []
        
        for chapter_index in range(1, 7):
            builder = ChapterBuilderFactory.get_builder(chapter_index)
            if not builder:
                continue
            
            spec = builder.get_spec(extracted_topic)
            # 使用生成的灵活标题替换默认标题
            flexible_title = generated_titles.get(chapter_index, spec.chapter_title)
            
            # 创建新的spec，使用灵活标题
            from dataclasses import replace
            spec = replace(spec, chapter_title=flexible_title)
            
            yield {
                "type": "chapter_start",
                "chapter_index": chapter_index,
                "chapter_title": flexible_title
            }
            
            theory_results = []
            politics_results = []
            
            if spec.theory_weight > 0:
                theory_results = await self.retrieve_materials(
                    queries=spec.retrieval_queries,
                    collection="theory",
                    top_k=max(1, int(5 * spec.theory_weight))
                )
            
            if spec.politics_weight > 0:
                politics_results = await self.retrieve_materials(
                    queries=spec.retrieval_queries,
                    collection="politics",
                    top_k=max(1, int(5 * spec.politics_weight))
                )
            
            all_materials = theory_results + politics_results
            
            slides = await self.generate_chapter_slides(
                chapter_spec=spec,
                materials=all_materials,
                topic=extracted_topic
            )
            
            chapter_result = {
                "chapter_index": chapter_index,
                "chapter_title": flexible_title,
                "slides": slides
            }
            
            chapters.append(chapter_result)
            
            yield {
                "type": "chapter_done",
                "chapter": chapter_result
            }
        
        outline = {
            "title": extracted_topic,
            "original_query": query,
            "chapters": chapters
        }
        
        yield {"type": "done", "outline": outline}
