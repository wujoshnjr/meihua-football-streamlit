from ai_reasoner_v33 import _parse_json_object


def test_parse_json_fenced_content():
    payload = _parse_json_object('```json\n{"result_direction":"體方勝"}\n```')
    assert payload["result_direction"] == "體方勝"
