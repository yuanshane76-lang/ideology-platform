import json
from typing import Dict, Any
from dashscope import Generation
from .models import TopicAnalysis, StanceType
from ..config import settings


THEORY_MODULE_MAPPING = {
    "实践观": ["实践", "认识", "真理", "检验"],
    "唯物史观": ["社会存在", "社会意识", "生产力", "生产关系", "社会条件"],
    "认识论": ["认识", "真理", "实践检验", "客观"],
    "辩证法": ["矛盾", "质量互变", "否定之否定", "对立统一"],
    "剩余价值": ["劳动", "资本", "剥削", "价值"],
}


class TopicAnalysisAgent:
    def __init__(self):
        self.api_key = settings.api_key
        self.model = settings.llm_model
    
    def analyze(self, topic: str, description: str = "") -> TopicAnalysis:
        prompt = self._build_prompt(topic, description)
        response = self._call_llm(prompt)
        result = self._parse_response(response, topic)
        return result
    
    def _build_prompt(self, topic: str, description: str) -> str:
        return f"""你是一个马克思主义哲学专家，请分析以下辩题：

辩题：{topic}
描述：{description or '无'}

请以JSON格式输出分析结果，包含以下字段：
1. pro_position: 正方核心立场（一句话）
2. con_position: 反方核心立场（一句话）
3. marxism_side: 马克思主义支持哪方（"正方"/"反方"/"中立"）
4. marxism_reason: 马哲支持理由（一句话）
5. core_concepts: 核心概念列表（3-5个关键词）
6. debate_focus: 核心争议点（一句话）
7. involves_marxism_stance: 是否涉及马哲核心立场（true/false）
8. stance_type: 立场类型（"neutral"/"aligned_pro"/"aligned_con"）
9. theory_modules: 相关理论模块（从以下选择：实践观、唯物史观、认识论、辩证法、剩余价值）

判断标准：
- 涉及阶级斗争、唯物史观、剩余价值、社会存在决定社会意识等马哲核心概念 → involves_marxism_stance=true
- 中性话题（短视频、AI、就业选择等）→ involves_marxism_stance=false
- 马哲支持正方 → stance_type="aligned_pro"
- 马哲支持反方 → stance_type="aligned_con"  
- 马哲中立 → stance_type="neutral"

只输出JSON，不要其他内容。"""

    def _call_llm(self, prompt: str) -> str:
        response = Generation.call(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.api_key,
            result_format="message",
        )
        if response.status_code != 200:
            raise RuntimeError(f"LLM调用失败: {response.code} - {response.message}")
        return response.output.choices[0].message.content
    
    def _parse_response(self, response: str, topic: str) -> TopicAnalysis:
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str)
            
            stance_type = StanceType(data.get("stance_type", "neutral"))
            
            return TopicAnalysis(
                topic=topic,
                pro_position=data.get("pro_position", ""),
                con_position=data.get("con_position", ""),
                marxism_side=data.get("marxism_side", "中立"),
                marxism_reason=data.get("marxism_reason", ""),
                core_concepts=data.get("core_concepts", []),
                debate_focus=data.get("debate_focus", ""),
                involves_marxism_stance=data.get("involves_marxism_stance", False),
                stance_type=stance_type,
                theory_modules=data.get("theory_modules", [])
            )
        except Exception as e:
            return TopicAnalysis(
                topic=topic,
                pro_position="正方立场",
                con_position="反方立场",
                marxism_side="中立",
                marxism_reason="",
                core_concepts=[],
                debate_focus="",
                involves_marxism_stance=False,
                stance_type=StanceType.NEUTRAL,
                theory_modules=[]
            )
