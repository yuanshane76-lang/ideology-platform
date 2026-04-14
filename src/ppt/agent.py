import os
import json
import uuid
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .html_generator import HTMLSlideGenerator
from .html_to_ppt import HTMLToPPTConverter
from .outline_generator import OutlineGenerator
from .themes import get_theme, THEME_REGISTRY

logger = logging.getLogger(__name__)

CACHE_EXPIRY_SECONDS = 3600  # 缓存过期时间：1小时


class PPTAgent:
    def __init__(self):
        self.html_generator = HTMLSlideGenerator()
        self.html_to_ppt = HTMLToPPTConverter()
        self.outline_generator = OutlineGenerator()
        
        self.html_slides_cache: Dict[str, Dict] = {}
        self.ppt_cache: Dict[str, Dict] = {}
        
        self.download_dir = "downloads"
        self.cache_dir = "cache/sessions"
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self._load_cached_sessions()
    
    def _get_session_cache_path(self, session_id: str) -> str:
        return os.path.join(self.cache_dir, f"{session_id}.json")
    
    def _save_session_to_cache(self, session_id: str, data: Dict):
        cache_data = {
            "data": data,
            "created_at": time.time()
        }
        cache_path = self._get_session_cache_path(session_id)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Session {session_id} saved to cache")
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
    
    def _load_session_from_cache(self, session_id: str) -> Optional[Dict]:
        cache_path = self._get_session_cache_path(session_id)
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            created_at = cache_data.get("created_at", 0)
            if time.time() - created_at > CACHE_EXPIRY_SECONDS:
                logger.info(f"Session {session_id} expired, removing")
                os.remove(cache_path)
                return None
            
            return cache_data.get("data")
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def _load_cached_sessions(self):
        if not os.path.exists(self.cache_dir):
            return
        
        current_time = time.time()
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                cache_path = os.path.join(self.cache_dir, filename)
                
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    created_at = cache_data.get("created_at", 0)
                    if current_time - created_at > CACHE_EXPIRY_SECONDS:
                        os.remove(cache_path)
                        logger.info(f"Removed expired session: {session_id}")
                    else:
                        self.html_slides_cache[session_id] = cache_data.get("data")
                        logger.info(f"Loaded session: {session_id}")
                except Exception as e:
                    logger.error(f"Failed to load cached session {session_id}: {e}")
    
    def get_template_list(self) -> Dict:
        return {
            "success": True,
            "templates": [
                {"id": "party_red", "name": "党建红", "preview": "/static/templates/party_red.png"},
                {"id": "tech_blue", "name": "科技蓝", "preview": "/static/templates/tech_blue.png"},
            ]
        }
    
    def get_html_themes(self) -> Dict:
        themes = []
        for theme_id, theme in THEME_REGISTRY.items():
            themes.append({
                "id": theme_id,
                "name": theme.name,
                "primary_color": theme.primary_color,
                "secondary_color": theme.secondary_color
            })
        return {"success": True, "themes": themes}
    
    def generate_outline(self, query: str) -> Dict:
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            outline = None
            async def collect_outline():
                nonlocal outline
                async for event in self.outline_generator.generate_outline_stream(query):
                    if event.get("type") == "done":
                        outline = event.get("outline")
            
            loop.run_until_complete(collect_outline())
            loop.close()
            
            if outline:
                return {"success": True, "outline": outline}
            else:
                return {"success": False, "error": "生成大纲失败"}
        except Exception as e:
            logger.error(f"生成大纲失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_outline_stream(self, query: str):
        async for event in self.outline_generator.generate_outline_stream(query):
            yield event
    
    def generate_html_slides(self, outline: Dict, theme_name: str) -> Dict:
        try:
            session_id = str(uuid.uuid4())[:8]
            slide_results = self.html_generator.generate_slides(outline, theme_name)
            slides = [s["html"] for s in slide_results]
            
            cache_data = {
                "slides": slides,
                "outline": outline,
                "theme": theme_name
            }
            
            self.html_slides_cache[session_id] = cache_data
            self._save_session_to_cache(session_id, cache_data)
            
            return {
                "success": True,
                "session_id": session_id,
                "total_slides": len(slides)
            }
        except Exception as e:
            logger.error(f"生成HTML幻灯片失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_session_data(self, session_id: str) -> Optional[Dict]:
        cache = self.html_slides_cache.get(session_id)
        if cache:
            return cache
        
        cache = self._load_session_from_cache(session_id)
        if cache:
            self.html_slides_cache[session_id] = cache
            return cache
        
        return None
    
    def get_html_slide(self, session_id: str, slide_index: int) -> Dict:
        cache = self._get_session_data(session_id)
        if not cache:
            return {"success": False, "error": "会话已过期或不存在，请重新生成预览"}
        
        slides = cache.get("slides", [])
        if slide_index < 0 or slide_index >= len(slides):
            return {"success": False, "error": "幻灯片索引超出范围"}
        
        return {
            "success": True,
            "html": slides[slide_index],
            "index": slide_index,
            "total": len(slides)
        }
    
    def convert_html_to_ppt(self, session_id: str) -> Dict:
        cache = self._get_session_data(session_id)
        if not cache:
            return {"success": False, "error": "会话已过期或不存在，请重新生成预览"}
        
        try:
            import re

            slides = cache.get("slides", [])
            outline = cache.get("outline", {})
            title = outline.get("title", "PPT")
            
            ppt_id = str(uuid.uuid4())[:8]
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip() or "PPT"
            output_path = os.path.join(self.download_dir, f"{ppt_id}_{safe_title}.pptx")
            
            self.html_to_ppt.save_ppt(slides, output_path, title)
            
            self.ppt_cache[ppt_id] = {
                "path": output_path,
                "filepath": output_path,
                "filename": os.path.basename(output_path),
                "outline": outline,
                "title": title
            }
            
            return {
                "success": True,
                "ppt_id": ppt_id,
                "download_url": f"/api/ppt/download/{ppt_id}"
            }
        except Exception as e:
            logger.error(f"转换PPT失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_ppt_from_outline(
        self, 
        query: str, 
        outline: Dict, 
        template_name: str = None,
        use_ai_background: bool = True
    ) -> Dict:
        theme_name = template_name or "party_red"
        
        html_result = self.generate_html_slides(outline, theme_name)
        if not html_result.get("success"):
            return html_result
        
        session_id = html_result["session_id"]
        return self.convert_html_to_ppt(session_id)
    
    def get_ppt_file(self, ppt_id: str) -> Optional[Dict]:
        return self.ppt_cache.get(ppt_id)
