from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from knowledge_loader import load_hexagrams
from models import HexagramResult, SimilarCase

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover - 部署缺少 sklearn 時仍可退回字串相似度
    TfidfVectorizer = None
    cosine_similarity = None


COLUMN_ALIASES: dict[str, list[str]] = {
    "case_id": ["案例ID", "case_id"],
    "match_name": ["比賽", "match_name"],
    "body_team": ["體方", "body_team"],
    "use_team": ["用方", "use_team"],
    "body_gua": ["體卦", "body_gua"],
    "use_gua": ["用卦", "use_gua"],
    "body_element": ["體卦五行", "體五行", "body_element"],
    "use_element": ["用卦五行", "用五行", "use_element"],
    "relation": ["體用生剋", "relation"],
    "relation_code": ["體用代碼", "relation_code"],
    "main_hexagram": ["本卦", "main_hexagram"],
    "mutual_hexagram": ["互卦", "mutual_hexagram"],
    "moving_line": ["動爻", "moving_line"],
    "moving_side": ["動爻位置", "moving_side"],
    "changed_hexagram": ["變卦", "changed_hexagram"],
    "body_transition": ["體方轉卦", "body_transition"],
    "use_transition": ["用方轉卦", "use_transition"],
    "structural_tags": ["結構標籤", "structural_tags"],
    "predicted_first": ["首選比分", "predicted_first"],
    "predicted_second": ["第二選比分", "predicted_second"],
    "predicted_third": ["第三選比分", "predicted_third"],
    "actual_score": ["實際比分", "actual_score"],
    "calibration_reason": ["校準原因", "calibration_reason"],
    "lesson_summary": ["校準摘要", "lesson_summary"],
    "prediction_reason": ["自動預測理由", "prediction_reason"],
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _first(row: pd.Series | dict[str, Any], logical_name: str) -> str:
    for column in COLUMN_ALIASES.get(logical_name, [logical_name]):
        if column in row:
            value = _clean(row[column])
            if value:
                return value
    return ""


def normalize_match_name(name: str) -> str:
    return re.sub(r"[\W_]+", "", (name or "").lower(), flags=re.UNICODE)


def infer_relation_code(text: str) -> str:
    text = text or ""
    if "體生用" in text:
        return "body_generates_use"
    if "用生體" in text:
        return "use_generates_body"
    if "體剋用" in text:
        return "body_controls_use"
    if "用剋體" in text:
        return "use_controls_body"
    if "比和" in text:
        return "equal"
    return ""


def split_tags(text: str) -> set[str]:
    return {part.strip() for part in re.split(r"[,，;；|\n]+", text or "") if part.strip()}


def result_document(result: HexagramResult) -> str:
    return " ".join(
        [
            result.match_name,
            f"體方{result.body_team}{result.body_gua}{result.body_element}",
            f"用方{result.use_team}{result.use_gua}{result.use_element}",
            result.relation,
            result.main_hexagram,
            result.mutual_hexagram,
            f"{result.moving_line}爻{result.moving_side}",
            result.changed_hexagram,
            result.body_transition,
            result.use_transition,
            " ".join(result.structural_tags),
        ]
    )


def case_document(row: pd.Series) -> str:
    parts = [
        _first(row, "match_name"),
        f"體方{_first(row, 'body_team')}{_first(row, 'body_gua')}{_first(row, 'body_element')}",
        f"用方{_first(row, 'use_team')}{_first(row, 'use_gua')}{_first(row, 'use_element')}",
        _first(row, "relation"),
        _first(row, "main_hexagram"),
        _first(row, "mutual_hexagram"),
        f"{_first(row, 'moving_line')}爻{_first(row, 'moving_side')}",
        _first(row, "changed_hexagram"),
        _first(row, "body_transition"),
        _first(row, "use_transition"),
        _first(row, "structural_tags"),
        _first(row, "calibration_reason"),
        _first(row, "lesson_summary"),
        _first(row, "prediction_reason"),
    ]
    return " ".join(x for x in parts if x)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _structural_similarity(result: HexagramResult, row: pd.Series) -> tuple[float, list[str], list[str]]:
    score = 0.0
    weight = 0.0
    common: list[str] = []
    differences: list[str] = []

    def compare(label: str, current: Any, old: Any, points: float) -> None:
        nonlocal score, weight
        old_text = _clean(old)
        current_text = _clean(current)
        if not old_text:
            return
        weight += points
        if current_text == old_text:
            score += points
            common.append(f"{label}相同：{current_text}")
        else:
            differences.append(f"{label}不同：本場{current_text}／舊例{old_text}")

    relation_code = _first(row, "relation_code") or infer_relation_code(_first(row, "relation"))
    compare("體用關係", result.relation_code, relation_code, 18)
    compare("動爻所在方", result.moving_side, _first(row, "moving_side"), 11)
    compare("動爻", result.moving_line, _first(row, "moving_line"), 5)
    compare("體卦", result.body_gua, _first(row, "body_gua"), 7)
    compare("用卦", result.use_gua, _first(row, "use_gua"), 7)
    compare("體五行", result.body_element, _first(row, "body_element"), 5)
    compare("用五行", result.use_element, _first(row, "use_element"), 5)
    compare("本卦", result.main_hexagram, _first(row, "main_hexagram"), 12)
    compare("互卦", result.mutual_hexagram, _first(row, "mutual_hexagram"), 8)
    compare("變卦", result.changed_hexagram, _first(row, "changed_hexagram"), 8)
    compare("體方轉象", result.body_transition, _first(row, "body_transition"), 5)
    compare("用方轉象", result.use_transition, _first(row, "use_transition"), 5)

    hexagrams = load_hexagrams()
    current_main_tags = set(hexagrams.get(result.main_hexagram, {}).get("tags", []))
    old_main = _first(row, "main_hexagram")
    old_main_tags = set(hexagrams.get(old_main, {}).get("tags", [])) if old_main else set()
    if old_main_tags:
        tag_score = _jaccard(current_main_tags, old_main_tags)
        score += 9 * tag_score
        weight += 9
        overlap = current_main_tags & old_main_tags
        if overlap:
            common.append("本卦核心象相近：" + "、".join(sorted(overlap)))

    current_tags = set(result.structural_tags)
    old_tags = split_tags(_first(row, "structural_tags"))
    if old_tags:
        tag_score = _jaccard(current_tags, old_tags)
        score += 10 * tag_score
        weight += 10
        overlap = current_tags & old_tags
        if overlap:
            common.append("結構標籤重疊：" + "、".join(sorted(list(overlap))[:5]))

    return (score / weight if weight else 0.0), common[:8], differences[:6]


def _text_similarities(current_doc: str, docs: list[str]) -> list[float]:
    if not docs:
        return []
    if TfidfVectorizer is not None and cosine_similarity is not None:
        try:
            # 字元 n-gram 對中文與卦名較穩，不依賴空格切詞。
            vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1, sublinear_tf=True)
            matrix = vectorizer.fit_transform([current_doc] + docs)
            values = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
            return [float(x) for x in values]
        except ValueError:
            pass
    return [SequenceMatcher(None, current_doc, doc).ratio() for doc in docs]


def retrieve_similar_cases(
    result: HexagramResult,
    casebook: pd.DataFrame,
    top_k: int = 5,
    max_rows: int = 500,
) -> list[SimilarCase]:
    if casebook is None or casebook.empty:
        return []

    current_name = normalize_match_name(result.match_name)
    candidates: list[tuple[pd.Series, float, list[str], list[str], str]] = []

    # 優先使用最近資料；同一場比賽一律排除，避免賽後結果洩漏回賽前預測。
    subset = casebook.tail(max_rows).copy()
    for _, row in subset.iterrows():
        match_name = _first(row, "match_name")
        if not match_name or normalize_match_name(match_name) == current_name:
            continue
        actual = _first(row, "actual_score")
        calibration = _first(row, "calibration_reason") or _first(row, "lesson_summary")
        if not actual and not calibration:
            continue
        structural, common, differences = _structural_similarity(result, row)
        doc = case_document(row)
        candidates.append((row, structural, common, differences, doc))

    if not candidates:
        return []

    current_doc = result_document(result)
    text_scores = _text_similarities(current_doc, [item[4] for item in candidates])
    output: list[SimilarCase] = []
    for index, (row, structural, common, differences, _) in enumerate(candidates):
        text_score = text_scores[index] if index < len(text_scores) else 0.0
        # 結構比文字更重要；文字主要幫助理解校準原因與象意描述。
        combined = 0.68 * structural + 0.32 * text_score
        case_id = _first(row, "case_id") or f"legacy-{index + 1:04d}"
        predictions = "/".join(
            x for x in [
                _first(row, "predicted_first"),
                _first(row, "predicted_second"),
                _first(row, "predicted_third"),
            ] if x
        )
        output.append(
            SimilarCase(
                case_id=case_id,
                match_name=_first(row, "match_name"),
                similarity=round(combined, 4),
                structural_similarity=round(structural, 4),
                text_similarity=round(text_score, 4),
                actual_score=_first(row, "actual_score"),
                predicted_scores=predictions,
                calibration_reason=_first(row, "calibration_reason"),
                lesson_summary=_first(row, "lesson_summary"),
                common_points=common,
                differences=differences,
                raw={str(k): _clean(v) for k, v in row.to_dict().items()},
            )
        )

    output.sort(key=lambda item: item.similarity, reverse=True)
    return output[: max(1, top_k)]
