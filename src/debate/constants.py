from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DebateTopic:
    title: str
    description: str
    difficulty: str
    tags: List[str]


SAMPLE_TOPICS: List[DebateTopic] = [
    DebateTopic(
        title="努力就一定能改变命运吗？",
        description="讨论个人奋斗与社会条件的关系：努力重要，但是否足以决定结果？",
        difficulty="基础级",
        tags=["奋斗", "成长", "公平"],
    ),
    DebateTopic(
        title="短视频让大学生更容易学习，还是更难深度思考？",
        description="讨论碎片化信息与系统化学习之间的张力。",
        difficulty="基础级",
        tags=["短视频", "学习效率", "深度思考"],
    ),
    DebateTopic(
        title="规则是在限制自由，还是在保护自由？",
        description="讨论规则与自由的边界：没有规则的自由是否会伤害他人自由。",
        difficulty="基础级",
        tags=["规则", "自由", "秩序"],
    ),
    DebateTopic(
        title="AI 会帮助人进步，还是让人越来越依赖？",
        description="讨论 AI 工具在学习与工作中的增益与惰性风险。",
        difficulty="进阶级",
        tags=["人工智能", "工具依赖", "主体性"],
    ),
    DebateTopic(
        title="高薪工作和真正喜欢的方向，大学生应该先选哪个？",
        description="讨论现实压力与长期价值追求之间如何平衡。",
        difficulty="进阶级",
        tags=["就业", "价值选择", "人生规划"],
    ),
]


ANTAGONIST_TYPES = [
    {
        "type": "反方",
        "representative": "观点挑战者",
        "description": "专注抓取论证漏洞，推动观点澄清",
        "avatar": "🔵",
    },
]
