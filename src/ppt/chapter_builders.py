from dataclasses import dataclass
from typing import List, Dict
from abc import ABC, abstractmethod
from ..clients import openai_client
from ..config import settings

@dataclass
class ChapterSpec:
    chapter_index: int
    chapter_title: str
    retrieval_queries: List[str]
    theory_weight: float
    politics_weight: float
    slide_count: int
    description: str

class ChapterBuilder(ABC):
    @abstractmethod
    def get_spec(self, topic: str) -> ChapterSpec:
        pass

class CoverChapterBuilder(ChapterBuilder):
    def get_spec(self, topic: str) -> ChapterSpec:
        return ChapterSpec(
            chapter_index=1,
            chapter_title="封面",
            retrieval_queries=[topic, "核心提法", "根本范畴"],
            theory_weight=0.5,
            politics_weight=0.5,
            slide_count=1,
            description="封面页：凝练主题，生成主标题和副标题"
        )

class BackgroundChapterBuilder(ChapterBuilder):
    def get_spec(self, topic: str) -> ChapterSpec:
        return ChapterSpec(
            chapter_index=2,
            chapter_title="背景与问题提出",
            retrieval_queries=[f"{topic} 时代背景", f"{topic} 现实挑战", f"{topic} 政策脉络"],
            theory_weight=0.3,
            politics_weight=0.7,
            slide_count=2,
            description="阐述'为什么现在要谈这个'，侧重时政库"
        )

class TheoryChapterBuilder(ChapterBuilder):
    def get_spec(self, topic: str) -> ChapterSpec:
        return ChapterSpec(
            chapter_index=3,
            chapter_title="核心要义与理论阐释",
            retrieval_queries=[f"{topic} 经典论述", f"{topic} 权威定义", f"{topic} 核心概念"],
            theory_weight=0.8,
            politics_weight=0.2,
            slide_count=3,
            description="学术化、理论化定义和分解，侧重理论库"
        )

class PracticeChapterBuilder(ChapterBuilder):
    def get_spec(self, topic: str) -> ChapterSpec:
        return ChapterSpec(
            chapter_index=4,
            chapter_title="实践案例与时代印证",
            retrieval_queries=[f"{topic} 典型案例", f"{topic} 数据", f"{topic} 政策成效"],
            theory_weight=0.2,
            politics_weight=0.8,
            slide_count=3,
            description="用近两年具体案例证明理论，侧重时政库"
        )

class SummaryChapterBuilder(ChapterBuilder):
    def get_spec(self, topic: str) -> ChapterSpec:
        return ChapterSpec(
            chapter_index=5,
            chapter_title="总结与展望",
            retrieval_queries=[f"{topic} 规律总结", f"{topic} 方法论", f"{topic} 未来规划"],
            theory_weight=0.6,
            politics_weight=0.4,
            slide_count=2,
            description="归纳核心观点，强调意义，指向未来方向"
        )

class AcknowledgmentChapterBuilder(ChapterBuilder):
    def get_spec(self, topic: str) -> ChapterSpec:
        return ChapterSpec(
            chapter_index=6,
            chapter_title="致谢",
            retrieval_queries=[],
            theory_weight=0.0,
            politics_weight=0.0,
            slide_count=1,
            description="致谢页"
        )

class ChapterBuilderFactory:
    @staticmethod
    def get_builder(chapter_index: int) -> ChapterBuilder:
        builders = {
            1: CoverChapterBuilder(),
            2: BackgroundChapterBuilder(),
            3: TheoryChapterBuilder(),
            4: PracticeChapterBuilder(),
            5: SummaryChapterBuilder(),
            6: AcknowledgmentChapterBuilder()
        }
        return builders.get(chapter_index)


class FlexibleChapterTitleGenerator:
    """使用大模型生成灵活的章节标题"""
    
    # 章节职责描述，用于指导大模型生成标题
    CHAPTER_ROLES = {
        1: {"default": "封面", "description": "PPT封面，展示主题"},
        2: {"default": "背景与问题提出", "description": "阐述时代背景、现实挑战、政策脉络"},
        3: {"default": "核心要义与理论阐释", "description": "理论定义、核心概念、学术阐释"},
        4: {"default": "实践案例与时代印证", "description": "典型案例、数据支撑、政策成效"},
        5: {"default": "总结与展望", "description": "规律总结、方法论、未来方向"},
        6: {"default": "致谢", "description": "结束致谢"}
    }
    
    @classmethod
    def generate_titles(cls, topic: str) -> Dict[int, str]:
        """为所有章节生成灵活的标题"""
        prompt = f"""请为主题"{topic}"的PPT生成6个章节的标题。

章节职责：
1. 封面章节：PPT封面，展示主题
2. 背景章节：阐述时代背景、现实挑战、政策脉络
3. 理论章节：理论定义、核心概念、学术阐释
4. 实践章节：典型案例、数据支撑、政策成效
5. 总结章节：规律总结、方法论、未来方向
6. 致谢章节：结束致谢

要求：
- 标题要简洁有力，2-8个字
- 要与主题"{topic}"紧密结合
- 避免使用"封面"、"第一章"等过于通用的名称
- 第1章（封面）可以用主题相关的概括性词语，如"引言"、"导论"、主题本身等
- 第6章（致谢）可以用"结语"、"展望"、"谢谢"等

返回JSON格式：
{{
  "titles": {{
    "1": "章节1标题",
    "2": "章节2标题",
    "3": "章节3标题",
    "4": "章节4标题",
    "5": "章节5标题",
    "6": "章节6标题"
  }}
}}

示例（主题：文化自信）：
{{
  "titles": {{
    "1": "文化自信",
    "2": "时代呼唤",
    "3": "理论根基",
    "4": "实践路径",
    "5": "未来展望",
    "6": "谢谢"
  }}
}}

请直接返回JSON："""
        
        try:
            response = openai_client.chat.completions.create(
                model=settings.fast_model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens=200
            )
            
            response_text = response.choices[0].message.content or ""
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            import json
            result = json.loads(response_text)
            titles = result.get("titles", {})
            
            # 转换为整数键
            return {int(k): v for k, v in titles.items()}
            
        except Exception as e:
            print(f"[WARNING] 生成章节标题失败: {e}")
            # 返回默认标题
            return {i: cls.CHAPTER_ROLES[i]["default"] for i in range(1, 7)}
    
    @classmethod
    def get_title(cls, chapter_index: int, topic: str, generated_titles: Dict[int, str] = None) -> str:
        """获取章节标题"""
        if generated_titles and chapter_index in generated_titles:
            return generated_titles[chapter_index]
        return cls.CHAPTER_ROLES.get(chapter_index, {}).get("default", f"第{chapter_index}章")
