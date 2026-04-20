"""
tests/test_qa_eval.py
======================================================================
思政问答系统 A/B 对比评估脚本（双裁判版）
----------------------------------------------------------------------
方法论参考：
  - MT-Bench / Chatbot Arena：LLM-as-Judge Pairwise Comparison
    (Zheng et al., 2023, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena")
  - RAGAS：Reference-free RAG pipeline evaluation
    (Es et al., 2023, "RAGAS: Automated Evaluation of Retrieval Augmented Generation")

评估设计：
  A 组（Baseline） ：qwen3-max 裸调用，无任何 RAG 检索增强
  B 组（RAG System）：完整多智能体 RAG 流水线
  裁判1：qwen3.6-plus（阿里，同厂商不同代）
  裁判2：deepseek-v3.2（深度求索，完全异厂商）
  两裁判同 DASHSCOPE_API_KEY，无需额外配置
  最终分 = 每位裁判两轮（位置互换）→ 4次评分取平均

评分五维度（每维 0-10 分）：
  D1 事实准确性、D2 文献引用质量、D3 知识深度、D4 教育价值、D5 政治立场
======================================================================
"""

import sys
import os
import json
import time
import argparse
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

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
# 1. Baseline 回答
# ═══════════════════════════════════════════════════════════════════════════════
BASELINE_SYS = "你是一位大学思政课教师。请根据你掌握的知识，直接回答学生的问题。要求内容准确、逻辑清晰、语言有教育温度。"

def get_baseline_answer(question: str) -> str:
    print(f"  [Baseline] 调用 {BASELINE_MODEL}（无RAG）...")
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
        print(f"  [Baseline] 完成，长度 {len(answer)} 字符")
        return answer
    except Exception as e:
        print(f"  [Baseline] 错误: {e}")
        return f"[Baseline调用失败: {e}]"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RAG 系统回答
# ═══════════════════════════════════════════════════════════════════════════════
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

        print(f"  [RAG] 完成 | 策略={strategy} | 理论={theory_count} | 时政={politics_count} | 审核={audit_passed} | 长度={len(answer)}")

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
# 3. LLM-as-Judge 评分
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
        time.sleep(1.2)

        print(f"  [Judge:{jcfg['id']}] 轮2（位置互换）...")
        r2_raw = _call_one_judge(jcfg, question, rag_answer, baseline_answer)
        time.sleep(1.2)

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
# 4. 单题完整评估
# ═══════════════════════════════════════════════════════════════════════════════
def evaluate_question(q: Dict, judge_configs: List[Dict]) -> Dict:
    qid = q["id"]
    question = q["question"]
    print(f"\n{'='*62}")
    print(f"[{qid}] {q['label']}  |  {question[:45]}...")
    print(f"{'='*62}")

    t0 = time.time()
    baseline_answer = get_baseline_answer(question)
    baseline_time = round(time.time() - t0, 1)

    t0 = time.time()
    rag_result = get_rag_answer(question)
    rag_time = round(time.time() - t0, 1)

    print(f"  [Judge] 开始多裁判评分（{len(judge_configs)}位裁判，每位2轮）...")
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

    if judge_result:
        sb = judge_result["score_baseline"]
        sr = judge_result["score_rag"]
        total_b = round(sum(sb.values()), 1)
        total_r = round(sum(sr.values()), 1)
        wins = judge_result["wins_detail"]
        print(f"\n  ┌─ 评分汇总（{judge_result['total_rounds']}轮平均）─────────────────────────")
        print(f"  │  Baseline 总分: {total_b}/50  |  RAG 总分: {total_r}/50")
        print(f"  │  各轮胜负: RAG={wins['RAG']} Baseline={wins['BASELINE']} TIE={wins['TIE']}")
        print(f"  │  最终胜者: {judge_result['winner']}")
        print(f"  │  关键差异: {judge_result['key_difference']}")
        print(f"  └──────────────────────────────────────────────────────")

    return record


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 报告生成
# ═══════════════════════════════════════════════════════════════════════════════
def generate_report(records: List[Dict], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存至: {output_path}")

    valid = [r for r in records if r.get("judge")]
    if not valid:
        print("没有有效的评分数据。")
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
    print("\n" + "="*64)
    print("  双裁判评估总结报告")
    print("="*64)
    print(f"  评估题目总数: {n}")
    print(f"  RAG 系统胜: {wins.get('RAG',0)}  |  Baseline 胜: {wins.get('BASELINE',0)}  |  平局: {wins.get('TIE',0)}")
    rag_win_rate = round(wins.get('RAG',0) / n * 100, 1) if n else 0
    print(f"  RAG 胜率: {rag_win_rate}%")
    print()
    print(f"  ─ 分维度平均分（满分10分）──────────────────────────────────")
    print(f"  {'维度':<22}  {'Baseline':>10}  {'RAG':>10}  {'提升△':>8}")
    print(f"  {'─'*22}  {'─'*10}  {'─'*10}  {'─'*8}")
    for d in DIMENSION_KEYS:
        label = DIMENSION_LABELS[d]
        avg_b = round(dim_sum_b[d] / n, 2)
        avg_r = round(dim_sum_r[d] / n, 2)
        delta = round(avg_r - avg_b, 2)
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  {label:<22}  {avg_b:>10.2f}  {avg_r:>10.2f}  {arrow}{abs(delta):>6.2f}")

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
# 6. 主入口
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="思政问答系统 A/B 对比评估（双裁判版）")
    parser.add_argument("--quick", action="store_true", help="快速模式：仅前3题")
    parser.add_argument("--id", nargs="+", metavar="QID", help="指定题目 ID，如 TH-01 HY-02")
    parser.add_argument("--single-judge", action="store_true",
                        help="单裁判模式：只用 qwen3.6-plus（更快）")
    args = parser.parse_args()

    active_judges = JUDGE_CONFIGS[:1] if args.single_judge else JUDGE_CONFIGS
    judge_names = " + ".join(j["label"] for j in active_judges)

    if args.id:
        questions = [q for q in EVAL_QUESTIONS if q["id"] in args.id]
        if not questions:
            print(f"未找到指定题目 ID: {args.id}")
            sys.exit(1)
    elif args.quick:
        questions = EVAL_QUESTIONS[:3]
        print("[快速模式] 仅运行前 3 道题")
    else:
        questions = EVAL_QUESTIONS

    n_rounds_per_q = len(active_judges) * 2
    est_min = len(questions) * (3 + n_rounds_per_q * 0.5)

    print(f"\n思政问答系统 A/B 对比评估（双裁判版）")
    print(f"Baseline 模型 : {BASELINE_MODEL}（无RAG）")
    print(f"RAG 系统      : {BASELINE_MODEL} + 多智能体检索增强")
    print(f"裁判配置      : {judge_names}")
    print(f"每题评分轮次  : {n_rounds_per_q} 轮（{len(active_judges)}位裁判×2轮）")
    print(f"评估题目总数  : {len(questions)}")
    print(f"预计耗时      : ~{int(est_min)} 分钟")

    records = []
    failed = []

    for i, q in enumerate(questions, 1):
        print(f"\n进度: {i}/{len(questions)}")
        try:
            record = evaluate_question(q, active_judges)
            records.append(record)
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            tmp = os.path.join(OUTPUT_DIR, f"eval_partial_{ts}.json")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except KeyboardInterrupt:
            print("\n用户中断，保存已完成数据...")
            break
        except Exception as e:
            print(f"  [ERROR] 题目 {q['id']} 执行失败: {e}")
            traceback.print_exc()
            failed.append(q["id"])

    if not records:
        print("没有成功完成任何评估，退出。")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_single_judge" if args.single_judge else "_dual_judge"
    out_path = os.path.join(OUTPUT_DIR, f"eval_report{suffix}_{ts}.json")
    generate_report(records, out_path)

    if failed:
        print(f"\n[警告] 以下题目执行失败：{failed}")

    print("\n评估完成！")


if __name__ == "__main__":
    main()
