"""
tests/test_qa_eval_resume.py
======================================================================
思政问答系统 A/B 对比评估脚本（双裁判版 + 断点续跑）
======================================================================
特性：
  - 双裁判：qwen3.6-plus（阿里）+ deepseek-v3.2（深度求索）
  - 断点续跑：每题完成后立即保存，中断后可从断点继续
  - 自动跳过：启动时自动检测已完成的题目
  - 实时报告：随时可查看当前进度和中间结果

运行方式：
  python -m tests.test_qa_eval_resume                    # 全量50题（断点续跑）
  python -m tests.test_qa_eval_resume --reset            # 重置，重新开始
  python -m tests.test_qa_eval_resume --status           # 查看当前进度
  python -m tests.test_qa_eval_resume --report           # 生成当前进度报告
======================================================================
"""

import sys
import os
import json
import time
import argparse
import traceback
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from openai import OpenAI
from src.config import settings
from tests.eval_questions import EVAL_QUESTIONS

# ── 常量 ─────────────────────────────────────────────────────────────────────
BASELINE_MODEL = "qwen3-max"

JUDGE_CONFIGS = [
    {
        "id": "qwen36",
        "label": "qwen3.6-plus（阿里·异代）",
        "model": "qwen3.6-plus",
        "api_key": settings.api_key,
        "base_url": settings.base_url,
    },
    {
        "id": "deepseek",
        "label": "deepseek-v3.2（深度求索·异厂商）",
        "model": "deepseek-v3.2",
        "api_key": settings.api_key,
        "base_url": settings.base_url,
    },
]

OUTPUT_DIR = os.path.join(ROOT_DIR, "outputs", "eval_reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 断点续跑数据文件
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "eval_checkpoint.json")
CHECKPOINT_META_FILE = os.path.join(OUTPUT_DIR, "eval_checkpoint_meta.json")

DIMENSION_KEYS = [
    "D1_factual_accuracy",
    "D2_citation_quality",
    "D3_knowledge_depth",
    "D4_educational_value",
    "D5_political_stance",
]
DIMENSION_LABELS = {
    "D1_factual_accuracy":  "D1 事实准确性",
    "D2_citation_quality":  "D2 文献引用质量",
    "D3_knowledge_depth":   "D3 知识深度",
    "D4_educational_value": "D4 教育价值",
    "D5_political_stance":  "D5 政治立场",
}

main_client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)


# ═══════════════════════════════════════════════════════════════════════════════
# 断点续跑管理
# ═══════════════════════════════════════════════════════════════════════════════
class CheckpointManager:
    """管理断点续跑状态"""
    
    def __init__(self):
        self.completed_ids: Set[str] = set()
        self.records: List[Dict] = []
        self.start_time: Optional[str] = None
        self.load()
    
    def load(self):
        """加载断点数据"""
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
                self.completed_ids = {r["id"] for r in self.records if r.get("id")}
                print(f"[断点续跑] 已加载 {len(self.records)} 条记录，已完成题目: {sorted(self.completed_ids)}")
            except Exception as e:
                print(f"[警告] 加载断点文件失败: {e}，将重新开始")
                self.records = []
                self.completed_ids = set()
        
        if os.path.exists(CHECKPOINT_META_FILE):
            try:
                with open(CHECKPOINT_META_FILE, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self.start_time = meta.get("start_time")
            except Exception:
                pass
    
    def save(self):
        """保存断点数据"""
        try:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
            
            meta = {
                "start_time": self.start_time or datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "completed_count": len(self.completed_ids),
                "total_count": len(EVAL_QUESTIONS),
            }
            with open(CHECKPOINT_META_FILE, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存断点失败: {e}")
    
    def add_record(self, record: Dict):
        """添加一条记录（自动去重）"""
        qid = record.get("id")
        if not qid:
            return
        
        # 如果已存在，替换
        self.records = [r for r in self.records if r.get("id") != qid]
        self.records.append(record)
        self.completed_ids.add(qid)
        self.save()
    
    def is_completed(self, qid: str) -> bool:
        return qid in self.completed_ids
    
    def get_remaining(self) -> List[Dict]:
        """获取未完成的题目"""
        return [q for q in EVAL_QUESTIONS if q["id"] not in self.completed_ids]
    
    def reset(self):
        """重置断点"""
        self.records = []
        self.completed_ids = set()
        self.start_time = None
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        if os.path.exists(CHECKPOINT_META_FILE):
            os.remove(CHECKPOINT_META_FILE)
        print("[断点续跑] 已重置，将重新开始")
    
    def get_progress(self) -> Dict:
        """获取进度信息"""
        total = len(EVAL_QUESTIONS)
        completed = len(self.completed_ids)
        return {
            "total": total,
            "completed": completed,
            "remaining": total - completed,
            "progress_pct": round(completed / total * 100, 1),
            "completed_ids": sorted(self.completed_ids),
            "remaining_ids": [q["id"] for q in EVAL_QUESTIONS if q["id"] not in self.completed_ids],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Baseline 和 RAG 回答
# ═══════════════════════════════════════════════════════════════════════════════
BASELINE_SYS = "你是一位大学思政课教师。请根据你掌握的知识，直接回答学生的问题。要求内容准确、逻辑清晰、语言有教育温度。"

def get_baseline_answer(question: str) -> str:
    print(f"  [Baseline] 调用 {BASELINE_MODEL}...")
    try:
        resp = main_client.chat.completions.create(
            model=BASELINE_MODEL,
            messages=[
                {"role": "system", "content": BASELINE_SYS},
                {"role": "user", "content": question},
            ],
            temperature=0.7,
            stream=False,
        )
        answer = resp.choices[0].message.content or ""
        print(f"  [Baseline] 完成，{len(answer)} 字符")
        return answer
    except Exception as e:
        print(f"  [Baseline] 错误: {e}")
        return f"[Baseline调用失败: {e}]"


def get_rag_answer(question: str) -> Dict[str, Any]:
    print(f"  [RAG] 调用多智能体流水线...")
    try:
        from src.graph import app_graph
        from src.conversation import conversation_store

        conv_id = conversation_store.create_conversation()
        initial_state = {
            "current_query": question,
            "user_query": question,
            "conversation_id": conv_id,
            "turn_id": 1,
            "retry_count": 0,
            "is_terminated": False,
        }
        config = {"recursion_limit": 25}
        final_state = app_graph.invoke(initial_state, config=config)

        answer = final_state.get("generated_answer", "")
        theory_count = len(final_state.get("theory_docs", []))
        politics_count = len(final_state.get("politics_docs", []))
        strategy = final_state.get("retrieve_strategy", "unknown")
        audit_passed = final_state.get("audit_passed")

        print(f"  [RAG] 完成 | 策略={strategy} | 理论={theory_count} | 时政={politics_count} | 审核={audit_passed}")

        try:
            conversation_store.delete_conversation(conv_id)
        except Exception:
            pass

        return {
            "answer": answer,
            "retrieve_strategy": strategy,
            "theory_docs_count": theory_count,
            "politics_docs_count": politics_count,
            "audit_passed": audit_passed,
        }
    except Exception as e:
        print(f"  [RAG] 错误: {e}")
        traceback.print_exc()
        return {"answer": f"[RAG调用失败: {e}]", "retrieve_strategy": "error",
                "theory_docs_count": 0, "politics_docs_count": 0, "audit_passed": None}


# ═══════════════════════════════════════════════════════════════════════════════
# LLM-as-Judge 评分
# ═══════════════════════════════════════════════════════════════════════════════
JUDGE_SYS = "你是一位经验丰富的思政教育专家和AI评估裁判。你的任务是客观、公正地评估两个答案的质量，不偏向任何一方。"

JUDGE_TMPL = """请评估以下两个答案对同一问题的回答质量。

【问题】
{question}

【回答A】
{answer_a}

【回答B】
{answer_b}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请从以下5个维度分别对两个回答打分（0-10分，保留1位小数）：

D1 事实准确性（Factual Accuracy）：内容是否准确？理论表述是否正确？是否有政治性错误？
D2 文献引用质量（Citation Quality）：是否明确引用具体文献来源（书名/章节/报道名）？仅说"理论指出"等模糊表述不得高分。
D3 知识深度（Knowledge Depth）：理论深度如何？是否多角度分析？关联知识是否丰富？
D4 教育价值（Educational Value）：是否贴近学生实际？是否有教育温度和启发性？
D5 政治立场（Political Stance）：是否符合社会主义核心价值观？立场是否坚定而不刻板？

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
请严格按以下JSON格式输出，不输出任何其他内容：

{{
  "score_a": {{
    "D1_factual_accuracy": <0-10>,
    "D2_citation_quality": <0-10>,
    "D3_knowledge_depth": <0-10>,
    "D4_educational_value": <0-10>,
    "D5_political_stance": <0-10>
  }},
  "score_b": {{
    "D1_factual_accuracy": <0-10>,
    "D2_citation_quality": <0-10>,
    "D3_knowledge_depth": <0-10>,
    "D4_educational_value": <0-10>,
    "D5_political_stance": <0-10>
  }},
  "winner": "A" 或 "B" 或 "TIE",
  "key_difference": "<50字：A和B最核心的差异>",
  "brief_analysis": "<100字：综合评价及胜负原因>"
}}"""


def _call_one_judge(judge_cfg: Dict, question: str, answer_a: str, answer_b: str) -> Optional[Dict]:
    client = OpenAI(api_key=judge_cfg["api_key"], base_url=judge_cfg["base_url"])
    prompt = JUDGE_TMPL.format(question=question, answer_a=answer_a, answer_b=answer_b)
    try:
        resp = client.chat.completions.create(
            model=judge_cfg["model"],
            messages=[
                {"role": "system", "content": JUDGE_SYS},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            stream=False,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    [Judge:{judge_cfg['id']}] 解析失败: {e}")
        return None


def judge_multi(question: str, baseline_answer: str, rag_answer: str, judge_configs: List[Dict]) -> Dict:
    all_rounds: List[Dict] = []

    for jcfg in judge_configs:
        jlabel = jcfg["label"]

        print(f"  [Judge:{jcfg['id']}] 轮1（Baseline=A, RAG=B）...")
        r1 = _call_one_judge(jcfg, question, baseline_answer, rag_answer)
        time.sleep(1.0)

        print(f"  [Judge:{jcfg['id']}] 轮2（位置互换）...")
        r2_raw = _call_one_judge(jcfg, question, rag_answer, baseline_answer)
        time.sleep(1.0)

        if r2_raw:
            r2 = {
                "score_a": r2_raw.get("score_b", {}),
                "score_b": r2_raw.get("score_a", {}),
                "winner": (
                    "B" if r2_raw.get("winner") == "A"
                    else ("A" if r2_raw.get("winner") == "B" else "TIE")
                ),
                "key_difference": r2_raw.get("key_difference", ""),
                "brief_analysis": r2_raw.get("brief_analysis", ""),
                "judge_id": jcfg["id"],
                "judge_label": jlabel,
                "round": 2,
            }
        else:
            r2 = None

        if r1:
            r1["judge_id"] = jcfg["id"]
            r1["judge_label"] = jlabel
            r1["round"] = 1
            all_rounds.append(r1)
        if r2:
            all_rounds.append(r2)

    if not all_rounds:
        return None

    n = len(all_rounds)
    agg_baseline = {d: 0.0 for d in DIMENSION_KEYS}
    agg_rag = {d: 0.0 for d in DIMENSION_KEYS}
    wins = {"BASELINE": 0, "RAG": 0, "TIE": 0}

    for r in all_rounds:
        sb = r.get("score_a", {})
        sr = r.get("score_b", {})
        w = r.get("winner", "TIE")

        for d in DIMENSION_KEYS:
            agg_baseline[d] += sb.get(d, 5.0)
            agg_rag[d] += sr.get(d, 5.0)

        if w == "A":
            wins["BASELINE"] += 1
        elif w == "B":
            wins["RAG"] += 1
        else:
            wins["TIE"] += 1

    avg_baseline = {d: round(agg_baseline[d] / n, 2) for d in DIMENSION_KEYS}
    avg_rag = {d: round(agg_rag[d] / n, 2) for d in DIMENSION_KEYS}

    if wins["RAG"] > wins["BASELINE"] and wins["RAG"] > wins["TIE"]:
        final_winner = "RAG"
    elif wins["BASELINE"] > wins["RAG"] and wins["BASELINE"] > wins["TIE"]:
        final_winner = "BASELINE"
    else:
        final_winner = "TIE"

    first_round = all_rounds[0]
    return {
        "score_baseline": avg_baseline,
        "score_rag": avg_rag,
        "winner": final_winner,
        "wins_detail": wins,
        "total_rounds": n,
        "key_difference": first_round.get("key_difference", ""),
        "brief_analysis": first_round.get("brief_analysis", ""),
        "rounds_raw": all_rounds,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 单题评估
# ═══════════════════════════════════════════════════════════════════════════════
def evaluate_one(q: Dict, judge_configs: List[Dict], checkpoint: CheckpointManager) -> Dict:
    """评估单题（带断点保存）"""
    qid = q["id"]
    question = q["question"]
    
    print(f"\n{'='*62}")
    print(f"[{qid}] {q['label']}  |  {question[:40]}...")
    print(f"{'='*62}")

    t0 = time.time()
    baseline_answer = get_baseline_answer(question)
    baseline_time = round(time.time() - t0, 1)

    t0 = time.time()
    rag_result = get_rag_answer(question)
    rag_time = round(time.time() - t0, 1)

    print(f"  [Judge] 双裁判评分（{len(judge_configs)}位×2轮）...")
    judge_result = judge_multi(question, baseline_answer, rag_result["answer"], judge_configs)

    record = {
        "id": qid,
        "category": q["category"],
        "label": q["label"],
        "question": question,
        "baseline": {
            "answer": baseline_answer,
            "answer_len": len(baseline_answer),
            "elapsed_sec": baseline_time,
        },
        "rag": {
            "answer": rag_result["answer"],
            "answer_len": len(rag_result["answer"]),
            "elapsed_sec": rag_time,
            "retrieve_strategy": rag_result.get("retrieve_strategy"),
            "theory_docs_count": rag_result.get("theory_docs_count", 0),
            "politics_docs_count": rag_result.get("politics_docs_count", 0),
            "audit_passed": rag_result.get("audit_passed"),
        },
        "judge": judge_result,
        "timestamp": datetime.now().isoformat(),
    }

    # 立即保存断点
    checkpoint.add_record(record)

    if judge_result:
        sb = judge_result["score_baseline"]
        sr = judge_result["score_rag"]
        total_b = round(sum(sb.values()), 1)
        total_r = round(sum(sr.values()), 1)
        wins = judge_result["wins_detail"]
        print(f"\n  ┌─ 评分结果（{judge_result['total_rounds']}轮平均）────────────────────")
        print(f"  │  Baseline: {total_b}/50  |  RAG: {total_r}/50  |  胜者: {judge_result['winner']}")
        print(f"  │  票数: RAG={wins['RAG']} Baseline={wins['BASELINE']} TIE={wins['TIE']}")
        print(f"  └──────────────────────────────────────────────────────")

    return record


# ═══════════════════════════════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════════════════════════════
def generate_report(records: List[Dict], output_path: str, is_partial: bool = False) -> None:
    """生成报告"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    status = "（部分结果）" if is_partial else "（最终结果）"
    print(f"\n详细报告已保存: {output_path} {status}")

    valid = [r for r in records if r.get("judge")]
    if not valid:
        print("暂无有效评分数据。")
        return

    wins = {"RAG": 0, "BASELINE": 0, "TIE": 0}
    dim_sum_b = {d: 0.0 for d in DIMENSION_KEYS}
    dim_sum_r = {d: 0.0 for d in DIMENSION_KEYS}
    cat_wins: Dict = {}

    for r in valid:
        j = r["judge"]
        sb = j["score_baseline"]
        sr = j["score_rag"]
        w = j["winner"]
        wins[w] = wins.get(w, 0) + 1

        cat = r["label"]
        if cat not in cat_wins:
            cat_wins[cat] = {"RAG": 0, "BASELINE": 0, "TIE": 0}
        cat_wins[cat][w] = cat_wins[cat].get(w, 0) + 1

        for d in DIMENSION_KEYS:
            dim_sum_b[d] += sb.get(d, 0)
            dim_sum_r[d] += sr.get(d, 0)

    n = len(valid)
    total = len(EVAL_QUESTIONS)
    
    print("\n" + "="*64)
    print(f"  双裁判评估报告 {status}")
    print("="*64)
    print(f"  进度: {n}/{total} 题 ({round(n/total*100,1)}%)")
    print(f"  RAG 胜: {wins.get('RAG',0)}  |  Baseline 胜: {wins.get('BASELINE',0)}  |  平局: {wins.get('TIE',0)}")
    if n > 0:
        rag_win_rate = round(wins.get('RAG',0) / n * 100, 1)
        print(f"  RAG 胜率: {rag_win_rate}%")
    print()
    print(f"  ─ 分维度平均分（满分10分）──────────────────────────────────")
    print(f"  {'维度':<22}  {'Baseline':>10}  {'RAG':>10}  {'提升△':>8}")
    print(f"  {'─'*22}  {'─'*10}  {'─'*10}  {'─'*8}")
    for d in DIMENSION_KEYS:
        label = DIMENSION_LABELS[d]
        avg_b = round(dim_sum_b[d] / n, 2) if n else 0
        avg_r = round(dim_sum_r[d] / n, 2) if n else 0
        delta = round(avg_r - avg_b, 2)
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  {label:<22}  {avg_b:>10.2f}  {avg_r:>10.2f}  {arrow}{abs(delta):>6.2f}")

    if n > 0:
        total_b = round(sum(dim_sum_b[d] for d in DIMENSION_KEYS) / n, 2)
        total_r = round(sum(dim_sum_r[d] for d in DIMENSION_KEYS) / n, 2)
        delta_t = round(total_r - total_b, 2)
        arrow_t = "↑" if delta_t > 0 else ("↓" if delta_t < 0 else "=")
        print(f"  {'综合均分（/50）':<22}  {total_b:>10.2f}  {total_r:>10.2f}  {arrow_t}{abs(delta_t):>6.2f}")

    print()
    print(f"  ─ 分题型胜负统计 ────────────────────────────────────────────")
    for cat, cw in sorted(cat_wins.items()):
        total_cat = sum(cw.values())
        print(f"  {cat:<8}  RAG:{cw.get('RAG',0)}/{total_cat}  Baseline:{cw.get('BASELINE',0)}/{total_cat}  TIE:{cw.get('TIE',0)}/{total_cat}")
    print("="*64)


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="思政问答系统 A/B 评估（双裁判 + 断点续跑）")
    parser.add_argument("--reset", action="store_true", help="重置断点，重新开始")
    parser.add_argument("--status", action="store_true", help="查看当前进度")
    parser.add_argument("--report", action="store_true", help="生成当前进度报告")
    parser.add_argument("--continue", dest="cont", action="store_true", 
                        help="继续运行（默认行为，可省略）")
    args = parser.parse_args()

    checkpoint = CheckpointManager()

    # 查看状态
    if args.status:
        progress = checkpoint.get_progress()
        print("\n" + "="*50)
        print("  当前评估进度")
        print("="*50)
        print(f"  总题数: {progress['total']}")
        print(f"  已完成: {progress['completed']} ({progress['progress_pct']}%)")
        print(f"  待完成: {progress['remaining']}")
        print(f"\n  已完成题目: {progress['completed_ids']}")
        print(f"  待完成题目: {progress['remaining_ids']}")
        print("="*50)
        return

    # 生成报告
    if args.report:
        if not checkpoint.records:
            print("暂无评估数据，无法生成报告。")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(OUTPUT_DIR, f"eval_report_resume_{ts}.json")
        is_partial = len(checkpoint.completed_ids) < len(EVAL_QUESTIONS)
        generate_report(checkpoint.records, out_path, is_partial)
        return

    # 重置
    if args.reset:
        checkpoint.reset()

    # 获取待完成题目
    remaining = checkpoint.get_remaining()
    if not remaining:
        print("\n✅ 所有题目已完成！")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(OUTPUT_DIR, f"eval_report_final_{ts}.json")
        generate_report(checkpoint.records, out_path, is_partial=False)
        return

    # 显示启动信息
    progress = checkpoint.get_progress()
    print("\n" + "="*62)
    print("  思政问答系统 A/B 评估（双裁判 + 断点续跑）")
    print("="*62)
    print(f"  Baseline: {BASELINE_MODEL}（无RAG）")
    print(f"  RAG系统:  {BASELINE_MODEL} + 多智能体检索")
    print(f"  裁判1:    {JUDGE_CONFIGS[0]['label']}")
    print(f"  裁判2:    {JUDGE_CONFIGS[1]['label']}")
    print(f"  进度:     {progress['completed']}/{progress['total']} 题 ({progress['progress_pct']}%)")
    print(f"  待完成:   {progress['remaining']} 题")
    est_min = progress['remaining'] * 5  # 每题约5分钟
    print(f"  预计耗时: ~{est_min} 分钟（可随时Ctrl+C中断，下次自动继续）")
    print("="*62)

    # 主循环
    failed = []
    try:
        for i, q in enumerate(remaining, 1):
            overall_i = progress['completed'] + i
            print(f"\n>>> 总进度: {overall_i}/{progress['total']} | 本次: {i}/{len(remaining)}")
            
            try:
                record = evaluate_one(q, JUDGE_CONFIGS, checkpoint)
            except KeyboardInterrupt:
                print("\n\n[用户中断] 已保存当前进度，下次运行将自动继续...")
                break
            except Exception as e:
                print(f"\n[错误] 题目 {q['id']} 执行失败: {e}")
                traceback.print_exc()
                failed.append(q["id"])
                # 继续下一题
                continue

    except KeyboardInterrupt:
        print("\n\n[用户中断] 已保存当前进度，下次运行将自动继续...")

    # 生成报告
    print("\n" + "="*62)
    print("  评估会话结束")
    print("="*62)
    
    final_progress = checkpoint.get_progress()
    is_partial = final_progress['remaining'] > 0
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_partial" if is_partial else "_final"
    out_path = os.path.join(OUTPUT_DIR, f"eval_report_resume{suffix}_{ts}.json")
    
    generate_report(checkpoint.records, out_path, is_partial)
    
    if failed:
        print(f"\n[警告] 以下题目执行失败：{failed}")
    
    if is_partial:
        print(f"\n[提示] 还有 {final_progress['remaining']} 题未完成")
        print("[提示] 运行 `python -m tests.test_qa_eval_resume` 将继续评估")
    else:
        print("\n✅ 所有题目已完成！")


if __name__ == "__main__":
    main()
