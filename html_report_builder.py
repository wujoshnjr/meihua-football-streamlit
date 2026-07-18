from __future__ import annotations

from html import escape
from typing import Any, Mapping, Sequence

from casting_structure import build_casting_structure
from input_protocol import (
    BODY_SECTION_LABEL,
    NEUTRAL_SECTION_LABEL,
    USE_SECTION_LABEL,
    build_input_protocol_audit,
)
from knowledge_loader import build_jiaoshi_yilin_reference, load_hexagrams
from models import CastingInput, HexagramResult
from version import APP_VERSION, KNOWLEDGE_VERSION


CLASSICAL_LABELS = {
    "core_theme": "核心主題", "structural_image": "卦象結構", "development_pattern": "發展模式",
    "constructive_expression": "正向表現", "shadow_expression": "受阻表現", "timing_and_action": "時機與行動",
}
FOOTBALL_LABELS = {
    "match_pattern": "比賽格局", "tempo": "節奏", "attack": "進攻", "defense": "防守",
    "transition": "攻守轉換", "scoring_environment": "進球環境", "body_use_context": "體用觀察",
    "late_phase": "末段走勢", "interpretation_caution": "使用提醒",
}


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    head = "".join(f"<th>{escape(str(item))}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<div class='table'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def _meaning_section(label: str, meaning: Mapping[str, Any]) -> str:
    item = load_hexagrams()[str(meaning["name"])]
    line_rows = [
        (line["position"], line["label"], line["classic_text"], line["small_image_text"])
        for line in reversed(item["lines"])
    ]
    classical = meaning["classical_meaning"]
    football = meaning["football_mapping"]
    return f"""
    <section><h2>{escape(label)}：{escape(str(meaning['unicode']))} {escape(str(meaning['name']))}</h2>
    <p><b>卦辭：</b>{escape(str(item['judgment_text']))}</p>
    <p><b>彖傳：</b>{escape(str(item['tuan_text']))}</p>
    <p><b>大象傳：</b>{escape(str(item['great_image_text']))}</p>
    <h3>完整卦義</h3>{_table(('欄位', '內容'), [(CLASSICAL_LABELS[k], classical[k]) for k in CLASSICAL_LABELS])}
    <h3>足球比賽應用層</h3>{_table(('欄位', '內容'), [(FOOTBALL_LABELS[k], football[k]) for k in FOOTBALL_LABELS])}
    <h3>六爻爻辭與小象</h3>{_table(('爻位', '爻名', '爻辭', '小象'), line_rows)}</section>
    """


def _conditional_path_section(path: Mapping[str, Any]) -> str:
    stages: list[str] = []
    for stage in path["stages"]:
        priority_rows = [
            (item["rank"], item["meaning"], item["rule_score"], item["football"])
            for item in stage["prioritized_meanings"]
        ]
        all_rows = [
            (item["name"], item["football"])
            for item in stage["possible_meanings"]
        ]
        matched_rows = [
            (
                item["priority"],
                item["condition"],
                "、".join(item["preferred_meanings"]),
                item["football_reading"],
            )
            for item in stage["matched_rules"]
        ] or [("—", "本次沒有命中特定條件", "保留全部義項", "不強行選義。")]
        stages.append(f"""
        <h3>{escape(str(stage['stage']))}：{escape(str(stage['trigram']))}｜優先義項：{escape(str(stage['primary_summary']))}</h3>
        {_table(('排序','優先義項','規則分','足球含義'), priority_rows)}
        <h4>全部可能含義</h4>{_table(('可能含義','足球含義'), all_rows)}
        <h4>本次命中條件</h4>{_table(('優先級','判斷條件','優先解為','足球判讀'), matched_rows)}
        <p><small>{escape(str(stage['rule_note']))}</small></p>
        """)
    return f"""
    <section><h2>{escape(str(path['party_name']))}／{escape(str(path['side']))}條件式卦義</h2>
    <p><b>卦線：</b>{escape(str(path['transition']))}｜<b>旺衰：</b>{escape(str(path['strength_before']))}→{escape(str(path['strength_after']))}｜
    <b>生克：</b>{escape(str(path['relation_before']))}→{escape(str(path['relation_after']))}</p>
    <p>六沖 {path['clash_count']} 組｜六合 {path['combination_count']} 組｜破門／突破訊號 {path['breakthrough_signal_count']} 個｜
    動爻旬空：{'是' if path['moving_line_void'] else '否'}｜動爻月破：{'是' if path['moving_line_month_broken'] else '否'}</p>
    {''.join(stages)}</section>
    """


def build_html_report(casting: CastingInput, result: HexagramResult) -> str:
    structure = build_casting_structure(result)
    najia = structure["najia_analysis"]
    day = najia["day_cycle"]
    void = najia["xun_void"]
    dynamics = structure["moving_line_dynamics"]
    moving = structure["moving_line_classics"]
    seasonal = structure["seasonal_strength"]
    conditional = structure["conditional_meanings"]
    input_audit = build_input_protocol_audit(
        casting.body_name,
        casting.use_name,
        casting.body_text,
        casting.use_text,
        casting.full_text,
    )
    yilin = build_jiaoshi_yilin_reference(result.main_hexagram, result.changed_hexagram)

    najia_sections = []
    for key, label in (("main_hexagram", "本卦"), ("mutual_hexagram", "互卦"), ("changed_hexagram", "變卦")):
        chart = najia[key]
        rows = []
        for line in reversed(chart["lines"]):
            rows.append((
                line["position_name"], line["line_label"], line["trigram"], line["gan_zhi"],
                line["branch_element"], "、".join(line["roles"]) or "—",
                line["six_relative_by_day_stem"], line["six_relative_by_palace"],
                line["void_status"], "是" if line["is_original_moving_position"] else "否",
            ))
        interactions = chart["branch_interactions"]
        relation_rows = [
            (x["relation"], f"第{x['first_line']}爻{x['first_branch']}", f"第{x['second_line']}爻{x['second_branch']}", x["football_note"])
            for x in interactions
        ] or [("—", "—", "—", "本卦未檢出爻間六沖或六合。")]
        najia_sections.append(f"""
        <section><h2>{label}納甲：{escape(chart['unicode'])} {escape(chart['name'])}</h2>
        <p>{escape(chart['palace'])}宮（{escape(chart['palace_element'])}）／{escape(chart['palace_stage'])}；
        世爻第 {chart['world_line']} 爻，應爻第 {chart['response_line']} 爻。</p>
        {_table(('爻位','陰陽爻名','經卦','納甲','支五行','世應','六親（日干法）','六親（卦宮法）','旬空','原動爻位'), rows)}
        <h3>地支六沖六合</h3>{_table(('關係','第一爻','第二爻','足球應用提醒'), relation_rows)}</section>
        """)

    meanings = structure["hexagram_meanings"]
    meaning_html = "".join(
        _meaning_section(label, meanings[key])
        for key, label in (("main_hexagram", "本卦"), ("mutual_hexagram", "互卦"), ("changed_hexagram", "變卦"))
    )
    workflow = _table(("步驟", "內容", "作用"), [(x["step"], x["content"], x["purpose"]) for x in najia["workflow"]])
    source_rows = (
        (BODY_SECTION_LABEL, casting.body_text),
        (USE_SECTION_LABEL, casting.use_text),
        (NEUTRAL_SECTION_LABEL, casting.full_text),
    )
    protocol_rows = [
        (
            section["label"],
            section["voice"],
            section["purpose"],
            f"{section['target_count'][0]}～{section['target_count'][1]}",
            section["actual_count"],
        )
        for section in input_audit["sections"].values()
    ]
    return f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><title>{escape(result.title)}完整排卦表</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Noto Sans TC',sans-serif;max-width:1200px;margin:32px auto;padding:0 22px;color:#202124;line-height:1.65}}h1,h2{{color:#5b351b}}section{{margin:28px 0;padding-top:8px;border-top:2px solid #d9c3a5}}.note{{padding:12px 16px;background:#fff7e8;border-left:4px solid #b2742e}}.table{{overflow:auto}}table{{width:100%;border-collapse:collapse;margin:10px 0 20px}}th,td{{border:1px solid #d7d7d7;padding:8px;text-align:left;vertical-align:top;white-space:pre-wrap}}th{{background:#f4eee5}}small{{color:#666}}</style></head><body>
<h1>☯ {escape(result.title)}｜完整排卦表</h1>
<p><small>系統 {APP_VERSION}｜知識庫 {KNOWLEDGE_VERSION}</small></p>
<p class='note'>本表完整呈現排卦、經傳、卦義與足球應用參考；不自動預測勝負或固定比分。足球欄位屬本專案應用層，不等同經典原文。</p>
<section><h2>v2 起象輸入規格</h2><p>{escape(input_audit['scope'])}</p>
{_table(('區塊','敘述人稱','排卦用途','固定範圍','本次計數'), protocol_rows)}
<p><small>{escape(input_audit['counting_note'])}</small></p></section>
<section><h2>起卦時間與旬空</h2>{_table(('項目','內容'), (
('國曆時間', result.casting_moment.gregorian_text), ('農曆時間', result.casting_moment.lunar_text),
('日辰', day['day_ganzhi']), ('日干五行', f"{day['day_stem']}／{day['day_stem_element']}"),
('月令', f"{day['month_branch']}月／{day['month_element']}"), ('旬', void['xun_name']), ('旬空', void['void_text'])))}</section>
<section><h2>本、互、動、變</h2>{_table(('項目','內容'), (
('體方／體卦', f"{result.body_name}／{result.body_gua}（{result.body_element}）"), ('用方／用卦', f"{result.use_name}／{result.use_gua}（{result.use_element}）"),
('本卦', result.main_hexagram), ('互卦', result.mutual_hexagram), ('動爻', f"第{result.moving_line}爻 {result.moving_line_label}"), ('變卦', result.changed_hexagram)))}</section>
<section><h2>動爻完整內容</h2>{_table(('項目','內容'), (
('爻辭', moving['line_text']), ('小象', moving['small_image_text']), ('當位', dynamics['position_status']), ('中位', dynamics['central_status']),
('相應', f"{dynamics['relation_to_corresponding_line']}（對應第{dynamics['corresponding_line']}爻）"), ('乘承比', dynamics['adjacent_relation'])))}</section>
<section><h2>月令旺衰</h2>{_table(('體用','變前','變後','轉勢'), (
('體方', seasonal['body_before'], seasonal['body_after'], seasonal['body_shift']), ('用方', seasonal['use_before'], seasonal['use_after'], seasonal['use_shift'])))}</section>
<section><h2>條件式卦義判斷原則</h2><p>{escape(conditional['whole_line_note'])}</p><p>{escape(conditional['evaluation_boundary'])}</p></section>
{_conditional_path_section(conditional['body_path'])}
{_conditional_path_section(conditional['use_path'])}
<p class='note'>六親主欄依你指定的「日干五行」算法；另列常見的「八宮卦宮五行」結果，兩種口徑不混用。旬空表示訊號暫受限制，不代表永久無效。</p>
{''.join(najia_sections)}
{meaning_html}
<section><h2>焦氏易林</h2><p><b>{escape(yilin['entry_key'])}：</b>{escape(yilin['text'])}</p><p><small>{escape(yilin['text_style'])}</small></p></section>
<section><h2>實戰操作步驟</h2>{workflow}</section>
<section><h2>本次起象原文</h2>{_table(('區塊','內容'), source_rows)}</section>
</body></html>"""


__all__ = ["build_html_report"]
