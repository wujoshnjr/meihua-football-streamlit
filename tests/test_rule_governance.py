from knowledge_loader import load_calibration_rules


def test_single_case_rules_remain_zero_weight_hypotheses() -> None:
    rules = load_calibration_rules()
    single_case_rules = [
        rule
        for rule in rules
        if rule.get("source_case") not in {"多案例歸納", "五行體用通則", "剝、坤、艮、損、節等多案例歸納"}
    ]
    assert single_case_rules
    assert all(rule.get("status") == "hypothesis" for rule in single_case_rules)

