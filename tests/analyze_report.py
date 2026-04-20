#!/usr/bin/env python3
"""分析评估报告并生成统计"""
import json
import sys
from collections import defaultdict

REPORT_FILE = "outputs/eval_reports/eval_report_resume_final_20260416_111355.json"

DIMS = ['D1_factual_accuracy', 'D2_citation_quality', 'D3_knowledge_depth', 
        'D4_educational_value', 'D5_political_stance']
DIM_LABELS = {
    'D1_factual_accuracy': '事实准确性',
    'D2_citation_quality': '文献引用质量', 
    'D3_knowledge_depth': '知识深度',
    'D4_educational_value': '教育价值',
    'D5_political_stance': '政治立场'
}

def main():
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    wins = {'RAG': 0, 'BASELINE': 0, 'TIE': 0}
    cat_wins = defaultdict(lambda: {'RAG': 0, 'BASELINE': 0, 'TIE': 0})
    dim_sum_b = {d: 0.0 for d in DIMS}
    dim_sum_r = {d: 0.0 for d in DIMS}
    
    # 找典型案例
    high_citation_rag = []  # RAG引用质量高的
    high_citation_base = []  # Baseline引用质量高的
    close_cases = []  # 分数接近的
    
    for r in data:
        if not r.get('judge'):
            continue
        j = r['judge']
        wins[j['winner']] += 1
        
        cat = r['label']
        cat_wins[cat][j['winner']] += 1
        
        for d in DIMS:
            dim_sum_b[d] += j['score_baseline'][d]
            dim_sum_r[d] += j['score_rag'][d]
        
        # 典型案例筛选
        sb = j['score_baseline']
        sr = j['score_rag']
        
        if sr['D2_citation_quality'] >= 9.0 and sb['D2_citation_quality'] < 8.0:
            high_citation_rag.append((r['id'], r['question'][:40], sr['D2_citation_quality'], sb['D2_citation_quality']))
        elif sb['D2_citation_quality'] >= 8.5 and sr['D2_citation_quality'] < 8.5:
            high_citation_base.append((r['id'], r['question'][:40], sb['D2_citation_quality'], sr['D2_citation_quality']))
        
        total_b = sum(sb.values())
        total_r = sum(sr.values())
        if abs(total_r - total_b) < 2.0:
            close_cases.append((r['id'], r['question'][:40], total_r, total_b, j['winner']))
    
    n = len([r for r in data if r.get('judge')])
    
    print("=" * 60)
    print("思政问答系统A/B评估统计报告")
    print("=" * 60)
    print(f"\n总体结果 (n={n}):")
    print(f"  RAG胜: {wins['RAG']} ({wins['RAG']/n*100:.1f}%)")
    print(f"  Baseline胜: {wins['BASELINE']} ({wins['BASELINE']/n*100:.1f}%)")
    print(f"  平局: {wins['TIE']} ({wins['TIE']/n*100:.1f}%)")
    
    print(f"\n分维度平均分 (满分10分):")
    print(f"  {'维度':<16} {'Baseline':>10} {'RAG':>10} {'提升':>10}")
    print("  " + "-" * 50)
    for d in DIMS:
        avg_b = dim_sum_b[d] / n
        avg_r = dim_sum_r[d] / n
        delta = avg_r - avg_b
        print(f"  {DIM_LABELS[d]:<16} {avg_b:>10.2f} {avg_r:>10.2f} {delta:>+10.2f}")
    
    total_b = sum(dim_sum_b[d] for d in DIMS) / n
    total_r = sum(dim_sum_r[d] for d in DIMS) / n
    print("  " + "-" * 50)
    print(f"  {'综合均分(/50)':<16} {total_b:>10.2f} {total_r:>10.2f} {total_r-total_b:>+10.2f}")
    
    print(f"\n分题型统计:")
    for cat in ['纯理论', '时政', '混合', '应用']:
        if cat in cat_wins:
            cw = cat_wins[cat]
            total = sum(cw.values())
            print(f"  {cat}: RAG={cw['RAG']}/{total}, Baseline={cw['BASELINE']}/{total}, TIE={cw['TIE']}/{total}")
    
    print("\n" + "=" * 60)
    print("典型案例")
    print("=" * 60)
    
    print("\n【RAG文献引用质量显著优于Baseline的案例】")
    for item in high_citation_rag[:5]:
        print(f"  {item[0]}: {item[1]}... (RAG={item[2]:.1f}, Baseline={item[3]:.1f})")
    
    print("\n【Baseline文献引用质量较好的案例】")
    for item in high_citation_base[:3]:
        print(f"  {item[0]}: {item[1]}... (Baseline={item[2]:.1f}, RAG={item[3]:.1f})")
    
    print("\n【分数接近的案例(差距<2分)】")
    for item in close_cases[:5]:
        print(f"  {item[0]}: {item[1]}... (RAG={item[2]:.1f}, Baseline={item[3]:.1f}, 胜者={item[4]})")

if __name__ == '__main__':
    main()
