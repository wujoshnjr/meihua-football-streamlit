import pandas as pd

from case_memory import retrieve_similar_cases
from meihua_engine import calculate_match_hexagram
from models import MatchInput


def test_retriever_finds_structurally_related_case_and_excludes_same_match():
    current = MatchInput(
        match_name="新比賽",
        body_team="甲",
        use_team="乙",
        body_text="甲乙丙丁戊",
        use_text="甲乙丙",
        full_text="甲乙丙丁戊己庚辛壬癸子",
    )
    result = calculate_match_hexagram(current)
    df = pd.DataFrame([
        {
            "案例ID": "CASE-OLD",
            "比賽": "舊比賽",
            "體方": "丙",
            "用方": "丁",
            "體卦": result.body_gua,
            "用卦": result.use_gua,
            "體卦五行": result.body_element,
            "用卦五行": result.use_element,
            "體用代碼": result.relation_code,
            "本卦": result.main_hexagram,
            "互卦": result.mutual_hexagram,
            "動爻": result.moving_line,
            "動爻位置": result.moving_side,
            "變卦": result.changed_hexagram,
            "實際比分": "2-1",
            "校準原因": "體生用時要提高用方反擊一球的風險。",
        },
        {
            "案例ID": "CASE-SAME",
            "比賽": "新比賽",
            "實際比分": "9-9",
            "校準原因": "這一筆不應被讀取。",
        },
    ])
    cases = retrieve_similar_cases(result, df, top_k=5)
    assert cases
    assert cases[0].case_id == "CASE-OLD"
    assert all(case.case_id != "CASE-SAME" for case in cases)
