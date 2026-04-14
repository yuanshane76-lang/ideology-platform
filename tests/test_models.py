# tests/test_models.py
from src.debate.models import TopicAnalysis, DebateSession, StanceType

def test_stance_type_enum():
    assert StanceType.NEUTRAL == "neutral"
    assert StanceType.ALIGNED_PRO == "aligned_pro"
    assert StanceType.ALIGNED_CON == "aligned_con"

def test_topic_analysis_creation():
    analysis = TopicAnalysis(
        topic="个人努力能否改变命运",
        pro_position="个人努力是改变命运的关键",
        con_position="社会条件决定命运，努力作用有限",
        marxism_side="反方",
        marxism_reason="马克思主义认为社会存在决定社会意识",
        core_concepts=["个人奋斗", "社会结构", "唯物史观"],
        debate_focus="个人努力与社会条件的辩证关系",
        involves_marxism_stance=True,
        stance_type=StanceType.ALIGNED_CON,
        theory_modules=["唯物史观", "实践观"]
    )
    assert analysis.topic == "个人努力能否改变命运"
    assert analysis.stance_type == StanceType.ALIGNED_CON

def test_debate_session_creation():
    session = DebateSession(
        session_id="test-123",
        topic_analysis=None,
        current_round=0,
        max_rounds=3,
        protagonist_messages=[],
        antagonist_messages=[],
        judge_summary=None,
        status="initialized"
    )
    assert session.session_id == "test-123"
    assert session.max_rounds == 3
