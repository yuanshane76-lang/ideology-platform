from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class StanceType(str, Enum):
    NEUTRAL = "neutral"
    ALIGNED_PRO = "aligned_pro"
    ALIGNED_CON = "aligned_con"


@dataclass
class TopicAnalysis:
    topic: str
    pro_position: str
    con_position: str
    marxism_side: str
    marxism_reason: str
    core_concepts: List[str]
    debate_focus: str
    involves_marxism_stance: bool
    stance_type: StanceType
    theory_modules: List[str] = field(default_factory=list)


@dataclass
class DebateSession:
    session_id: str
    topic_analysis: Optional[TopicAnalysis]
    current_round: int = 0
    max_rounds: int = 3
    protagonist_messages: List[str] = field(default_factory=list)
    antagonist_messages: List[str] = field(default_factory=list)
    judge_summary: Optional[str] = None
    status: str = "initialized"
