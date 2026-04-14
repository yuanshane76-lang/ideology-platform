# tests/test_topic_agent.py
import pytest
from src.debate.topic_agent import TopicAnalysisAgent
from src.debate.models import StanceType

@pytest.fixture
def agent():
    return TopicAnalysisAgent()

def test_analyze_returns_topic_analysis(agent):
    result = agent.analyze("高薪工作和真正喜欢的方向，大学生应该先选哪个？")
    assert result.topic == "高薪工作和真正喜欢的方向，大学生应该先选哪个？"
    assert len(result.pro_position) > 0
    assert len(result.con_position) > 0

def test_analyze_marxism_aligned_topic(agent):
    result = agent.analyze("个人努力能否改变命运？")
    assert result.involves_marxism_stance == True
    assert result.stance_type in [StanceType.ALIGNED_PRO, StanceType.ALIGNED_CON]

def test_analyze_returns_theory_modules(agent):
    result = agent.analyze("实践是检验真理的唯一标准吗？")
    assert len(result.theory_modules) > 0

def test_analyze_returns_pro_con_positions(agent):
    result = agent.analyze("规则是在限制自由，还是在保护自由？")
    assert len(result.pro_position) > 0
    assert len(result.con_position) > 0
    assert len(result.core_concepts) > 0
