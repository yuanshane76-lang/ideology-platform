"""
HTML幻灯片生成器 - 使用AI生成美观的HTML幻灯片
"""
import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from .themes.html_themes import ThemeManager, Theme
from ..config import settings


class HTMLSlideGenerator:
    """
    HTML幻灯片生成器
    
    核心功能:
    - 根据大纲和主题生成HTML幻灯片
    - 支持多种主题风格
    - 生成适合1920x1080分辨率的幻灯片
    """
    
    SLIDE_WIDTH = 1920
    SLIDE_HEIGHT = 1080
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.client = OpenAI(
            api_key=api_key or settings.api_key,
            base_url=base_url or settings.base_url
        )
        self.theme_manager = ThemeManager()
    
    def generate_slides(
        self, 
        outline: Dict, 
        theme_name: str = "party_red"
    ) -> List[Dict[str, str]]:
        """
        根据大纲生成所有幻灯片的HTML
        
        Args:
            outline: PPT大纲
            theme_name: 主题名称
            
        Returns:
            List of {"slide_index": int, "title": str, "html": str}
        """
        theme = self.theme_manager.get_theme(theme_name)
        slides = self._outline_to_slide_data(outline)
        
        results = []
        for i, slide_data in enumerate(slides):
            html = self._generate_single_slide(slide_data, theme, i, len(slides))
            results.append({
                "slide_index": i,
                "title": slide_data.get("title", f"幻灯片 {i+1}"),
                "html": html
            })
        
        return results
    
    def get_slide_data_list(self, outline: Dict) -> List[Dict]:
        """将大纲转换为幻灯片数据列表（公开方法，用于流式生成）"""
        return self._outline_to_slide_data(outline)
    
    def generate_single_slide_html(
        self, 
        slide_data: Dict, 
        theme_name: str, 
        index: int, 
        total: int
    ) -> str:
        """生成单个幻灯片的HTML（公开方法，用于流式生成）"""
        theme = self.theme_manager.get_theme(theme_name)
        return self._generate_single_slide(slide_data, theme, index, total)
    
    def _outline_to_slide_data(self, outline: Dict) -> List[Dict]:
        """将大纲转换为幻灯片数据列表"""
        slides = []
        
        title = outline.get("title", "演示文稿")
        subtitle = outline.get("subtitle", outline.get("subTitle", ""))
        
        slides.append({
            "type": "cover",
            "title": title,
            "subtitle": subtitle
        })
        
        chapters = outline.get("chapters", [])
        for chapter_idx, chapter in enumerate(chapters, 1):
            chapter_title = chapter.get("chapterTitle", chapter.get("chapter_title", ""))
            
            slides.append({
                "type": "chapter",
                "title": chapter_title,
                "chapter_number": chapter_idx
            })
            
            contents = chapter.get("chapterContents", chapter.get("slides", []))
            for content in contents:
                content_title = content.get("chapterTitle", content.get("title", ""))
                content_items = content.get("items", content.get("bullets", []))
                
                if content_items:
                    slides.append({
                        "type": "content",
                        "title": content_title,
                        "items": content_items
                    })
                else:
                    slides.append({
                        "type": "simple",
                        "title": content_title
                    })
        
        slides.append({
            "type": "end",
            "title": "谢谢",
            "subtitle": "Thank You"
        })
        
        return slides
    
    def _generate_single_slide(
        self, 
        slide_data: Dict, 
        theme: Theme, 
        index: int, 
        total: int
    ) -> str:
        """使用AI生成单个幻灯片的HTML"""
        
        prompt = self._build_prompt(slide_data, theme, index, total)
        
        try:
            response = self.client.chat.completions.create(
                model=settings.coder_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(theme)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            html = response.choices[0].message.content
            html = self._extract_html(html)
            html = self._ensure_full_html(html, theme)
            
            return html
            
        except Exception as e:
            print(f"AI生成失败: {e}")
            return self._generate_fallback_html(slide_data, theme)
    
    def _get_system_prompt(self, theme: Theme) -> str:
        """获取系统提示词"""
        return f"""你是一个专业的PPT HTML设计师。你需要生成单页幻灯片的HTML代码。

## 设计要求
1. 幻灯片尺寸: {self.SLIDE_WIDTH}x{self.SLIDE_HEIGHT}像素 (16:9比例)
2. 主题风格: {theme.name}
3. 主色调: {theme.primary_color}
4. 辅助色: {theme.secondary_color}
5. 背景样式: {theme.background_style}
6. 字体: 使用系统字体，中文优先使用"微软雅黑"、"PingFang SC"

## 代码要求（重要！必须严格遵守）
1. 只输出HTML代码，不要解释
2. 所有样式必须内联在style标签中
3. **布局方式**：使用绝对定位(position:absolute)进行精确布局，避免使用flex/grid导致的不可控换行
4. **容器设置**：body必须设置 width:1920px; height:1080px; overflow:hidden; position:relative;
5. **安全边距**：内容区域必须在100px-1820px(水平)和100px-980px(垂直)范围内，即四边各留100px边距
6. **可用区域**：1720x880像素（这是你能使用的最大区域）
7. **字号限制**：
   - 封面/章节页标题：56-72px
   - 内容页标题：48-56px
   - 正文/要点：20-28px
   - 禁止使用过大的字号
8. **元素定位**：每个元素必须使用绝对定位，明确指定top/left/width/height，不要使用百分比
9. **溢出控制**：所有容器必须设置overflow:hidden，确保内容不会溢出

## 布局策略（模板骨架 + AI填充文案，必须遵守）
- 你只能在以下模板中选择，不可自由发散新结构。
- 内容页优先使用固定模板，降低结构漂移。
- 允许在不改变模板坐标骨架的前提下做视觉变化（配色层次、卡片样式、分隔线、图标风格、标题装饰）。

### 封面页布局
```
body (1920x1080)
├── 背景装饰层 (绝对定位，几何图形)
├── 标题 (top: 400px, left: 50%, transform: translateX(-50%), font-size: 72px)
└── 副标题 (top: 520px, left: 50%, transform: translateX(-50%), font-size: 32px)
```

### 章节页布局
```
body (1920x1080)
├── 背景装饰层
├── 章节编号 (top: 300px, left: 50%, transform: translateX(-50%), font-size: 200px, opacity: 0.2)
└── 章节标题 (top: 500px, left: 50%, transform: translateX(-50%), font-size: 64px)
```

### 内容页布局选项

**选项A：2x2卡片网格（推荐，最稳定）**
```
body (1920x1080)
├── 标题 (top: 80px, left: 100px, width: 1720px, font-size: 48px)
├── 卡片1 (top: 200px, left: 100px, width: 830px, height: 380px)
├── 卡片2 (top: 200px, left: 990px, width: 830px, height: 380px)
├── 卡片3 (top: 600px, left: 100px, width: 830px, height: 280px)
└── 卡片4 (top: 600px, left: 990px, width: 830px, height: 280px)
```

**选项B：左侧标题+右侧内容**
```
body (1920x1080)
├── 标题区 (top: 100px, left: 100px, width: 400px, height: 880px)
└── 内容区 (top: 100px, left: 540px, width: 1280px, height: 880px)
```

## 重要约束
1. **绝对定位**：所有可见元素必须使用position:absolute
2. **固定尺寸**：所有元素必须明确指定width和height（像素值）
3. **边界检查**：确保所有元素的right = left + width ≤ 1820，bottom = top + height ≤ 980
4. **内容精简**：每页最多4个要点，每个要点文字控制在30字以内
5. **禁止事项**：
   - 禁止使用CSS动画（animation）
   - 禁止使用CSS过渡效果（transition）
   - 禁止使用JavaScript
   - 禁止使用:hover等交互效果
   - 禁止在背景装饰中使用任何汉字、生僻字、古文字
   - 禁止使用百分比布局
   - 禁止使用flex/grid布局（容易导致不可控的换行和溢出）

## 文字要求
- 使用规范简体汉字
- 禁止使用生僻字、异体字、古汉字
- 只使用常用字表中的汉字"""
    
    def _build_prompt(
        self, 
        slide_data: Dict, 
        theme: Theme, 
        index: int, 
        total: int
    ) -> str:
        """构建用户提示词"""
        slide_type = slide_data.get("type", "content")
        
        prompt = f"请生成第{index+1}页幻灯片（共{total}页）的HTML代码。\n\n"
        prompt += f"幻灯片类型: {slide_type}\n"
        
        if slide_type == "cover":
            prompt += f"标题: {slide_data.get('title', '')}\n"
            prompt += f"副标题: {slide_data.get('subtitle', '')}\n"
            prompt += "\n要求: 设计一个吸引人的封面页，标题突出（字号60-72px）。"
            prompt += "\n背景装饰要求: 只使用几何图形（圆形、矩形、线条、点）、色块渐变、抽象图案作为背景装饰。"
            prompt += "\n**重要：禁止在背景中使用任何汉字、生僻字、古文字、异体字作为装饰元素。只允许使用几何图形。**"
            prompt += "\n高度限制: 所有内容总高度不超过800px，确保在1080px高度内完整显示。"
            prompt += "\n文字要求: 使用规范简体汉字，禁止使用生僻字、异体字。只使用常用汉字。"
            
        elif slide_type == "chapter":
            prompt += f"章节编号: {slide_data.get('chapter_number', 1)}\n"
            prompt += f"章节标题: {slide_data.get('title', '')}\n"
            prompt += "\n要求: 设计章节过渡页，突出章节编号和标题（字号56-64px）。"
            prompt += "\n背景装饰要求: 只使用几何图形、色块渐变作为背景装饰。"
            prompt += "\n**重要：禁止在背景中使用任何汉字、生僻字、古文字作为装饰。只允许使用几何图形和色块。**"
            prompt += "\n高度限制: 所有内容总高度不超过800px。"
            prompt += "\n文字要求: 使用规范简体汉字，禁止使用生僻字、异体字。只使用常用汉字。"
            
        elif slide_type == "content":
            prompt += f"标题: {slide_data.get('title', '')}\n"
            prompt += f"要点:\n"
            items = slide_data.get("items", [])
            # 限制要点数量，避免内容过多
            display_items = items[:4] if len(items) > 4 else items
            for i, item in enumerate(display_items, 1):
                if isinstance(item, dict):
                    prompt += f"  {i}. {item.get('text', item.get('content', str(item)))}\n"
                else:
                    prompt += f"  {i}. {item}\n"
            
            # 固定模板骨架 + 受控多样化（避免死板，同时不失控）
            content_count = len(display_items)
            if content_count <= 2:
                template_choice = "选项B（左右分栏）"
            elif content_count == 3:
                template_choice = "选项B（左右分栏）" if index % 2 == 0 else "选项A（2x2卡片网格）"
            else:
                template_choice = "选项A（2x2卡片网格）"

            style_packs = [
                "商务简洁：细边框卡片 + 轻阴影 + 细分隔线",
                "强调重点：首要点高亮色块 + 其余卡片弱化",
                "学术信息：标题下信息条 + 编号圆点 + 规整留白",
                "叙事风格：标题装饰线 + 卡片角标 + 层级色阶",
            ]
            style_hint = style_packs[index % len(style_packs)]

            prompt += f"\n布局要求: 内容页必须从固定模板中选择，本页优先使用{template_choice}。"
            prompt += "\n模板约束: 严格沿用系统提示词中的模板骨架坐标范围，不要修改为flex/grid流式布局。"
            prompt += f"\n风格变化: 在模板不变前提下采用“{style_hint}”视觉方案，确保不同页风格有区分。"
            prompt += "\n设计要点: 可以变化色彩层次、卡片边框/阴影、图标样式、标题装饰，但不得改变模板主结构。"
            prompt += "\n边界要求: 所有内容必须严格在1920x1080范围内，不要有任何元素超出边界。"
            prompt += "\n高度限制: 内容区域总高度严格控制在800px以内（留出上下边距），如果要点过多请精简到3-4个。"
            prompt += "\n文字要求: 使用规范简体汉字，禁止使用生僻字、异体字。只使用常用汉字（如：的、是、在、有、我、他、这、中等常用字）。"
            
        elif slide_type == "end":
            prompt += f"主标题: {slide_data.get('title', '谢谢')}\n"
            prompt += f"副标题: {slide_data.get('subtitle', 'Thank You')}\n"
            prompt += "\n要求: 设计结束页，感谢语居中，简洁优雅。"
            
        else:
            prompt += f"标题: {slide_data.get('title', '')}\n"
            prompt += "\n要求: 设计简洁的标题页。"
        
        return prompt
    
    def _extract_html(self, content: str) -> str:
        """从AI响应中提取HTML代码"""
        if "<!DOCTYPE" in content or "<html" in content:
            start = content.find("<!DOCTYPE") if "<!DOCTYPE" in content else content.find("<html")
            end = content.rfind("</html>") + 7
            if end > start:
                return content[start:end]
        
        if "<body" in content:
            start = content.find("<body")
            end = content.rfind("</body>") + 7
            if end > start:
                body_content = content[start:end]
                return f"<div>{body_content}</div>"
        
        if "<div" in content or "<section" in content:
            return content
        
        return f"<div>{content}</div>"
    
    def _ensure_full_html(self, html: str, theme: Theme) -> str:
        """确保HTML是完整的文档"""
        # 强制添加的CSS：仅保留安全网，不覆盖布局语义
        force_css = f"""
        <style id="force-restrictions">
            * {{ box-sizing: border-box; }}
            html, body {{ 
                width: {self.SLIDE_WIDTH}px; 
                height: {self.SLIDE_HEIGHT}px; 
                overflow: hidden !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            body {{
                position: relative !important;
            }}
            /* 仅做安全约束，不干预排版结构 */
            *, *::before, *::after {{ 
                animation: none !important; 
                transition: none !important;
            }}
        </style>
        """
        
        if "<!DOCTYPE" in html:
            # 如果已经有DOCTYPE，在</head>前添加强制CSS
            if "</head>" in html:
                html = html.replace("</head>", f"{force_css}</head>")
            else:
                # 如果没有</head>，在<body>前添加
                html = html.replace("<body>", f"{force_css}<body>")
            return html
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: {self.SLIDE_WIDTH}px;
            height: {self.SLIDE_HEIGHT}px;
            overflow: hidden;
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
        }}
        body {{
            position: relative;
        }}
        /* 仅保留安全网约束，避免覆盖模型布局语义 */
        *, *::before, *::after {{
            animation: none !important;
            transition: none !important;
            animation-duration: 0s !important;
            animation-delay: 0s !important;
            transition-duration: 0s !important;
            transition-delay: 0s !important;
        }}
        {theme.get_css_variables()}
    </style>
</head>
<body>
{html}
</body>
</html>"""
    
    def _generate_fallback_html(self, slide_data: Dict, theme: Theme) -> str:
        """生成降级HTML（AI失败时使用）"""
        slide_type = slide_data.get("type", "content")
        title = slide_data.get("title", "")
        subtitle = slide_data.get("subtitle", "")
        items = slide_data.get("items", [])
        
        items_html = ""
        if items:
            items_html = "<ul style='list-style: none; padding: 0; margin-top: 40px;'>"
            for item in items[:5]:
                text = item.get("text", item.get("content", str(item))) if isinstance(item, dict) else item
                items_html += f"<li style='font-size: 28px; margin: 20px 0; color: {theme.text_color};'>• {text}</li>"
            items_html += "</ul>"
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: {self.SLIDE_WIDTH}px;
            height: {self.SLIDE_HEIGHT}px;
            overflow: hidden;
            font-family: "Microsoft YaHei", sans-serif;
            background: {theme.background_style};
        }}
        .container {{
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 80px;
        }}
        .title {{
            font-size: 64px;
            font-weight: bold;
            color: {theme.primary_color};
            text-align: center;
            margin-bottom: 20px;
        }}
        .subtitle {{
            font-size: 32px;
            color: {theme.secondary_color};
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">{title}</h1>
        {f'<p class="subtitle">{subtitle}</p>' if subtitle else ''}
        {items_html}
    </div>
</body>
</html>"""
    
    def get_available_themes(self) -> List[Dict[str, str]]:
        """获取所有可用主题"""
        return self.theme_manager.list_themes()
