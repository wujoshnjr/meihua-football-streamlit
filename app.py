from __future__ import annotations

import html
import json
from typing import Any, Mapping, Sequence

import streamlit as st

from config import load_config
from knowledge_loader import (
    knowledge_completeness,
    load_classics,
    load_hexagrams,
    load_jiaoshi_yilin,
    load_meihua_principles,
    load_trigrams,
)
from meihua_engine import calculate_casting
from models import CastingInput, HexagramResult
from report_builder import build_markdown_report
from storage import CastingStore, build_casting_row, save_report
from version import APP_TITLE, KNOWLEDGE_VERSION


def _secrets() -> dict[str, Any]:
    try:
        return dict(st.secrets)
    except (FileNotFoundError, RuntimeError):
        return {}


def _modulo(value: int, divisor: int) -> str:
    return str(value) if value else f"0 → 作{divisor}"


def _normalize_parties(body_name: str, use_name: str) -> tuple[str, str, str]:
    """Return cleaned party names and the single canonical event title."""

    body = body_name.strip()
    use = use_name.strip()
    if not body or not use:
        raise ValueError("請輸入體方名稱與用方名稱。")
    return body, use, f"{body} vs {use}"


def _render_html_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    """Render tabular text without importing pandas/NumPy/PyArrow at app startup."""

    cell_style = (
        "border-bottom:1px solid rgba(128,128,128,.25);padding:.55rem .7rem;"
        "text-align:left;vertical-align:top;white-space:pre-wrap;"
    )
    header = "".join(
        f'<th style="{cell_style}font-weight:700;position:sticky;top:0;'
        f'background:var(--background-color);">{html.escape(str(column))}</th>'
        for column in columns
    )
    body = "".join(
        "<tr>"
        + "".join(
            f'<td style="{cell_style}">{html.escape(str(row.get(column, "")))}</td>'
            for column in columns
        )
        + "</tr>"
        for row in rows
    )
    st.markdown(
        '<div style="overflow:auto;max-height:34rem;border:1px solid '
        'rgba(128,128,128,.22);border-radius:.5rem;">'
        '<table style="width:100%;border-collapse:collapse;font-size:.92rem;">'
        f"<thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_line_table(result: HexagramResult) -> None:
    rows = []
    for row in reversed(result.line_table):
        rows.append(
            {
                "爻位": f"{row['position_name']}／{row['line_label']}",
                "本卦爻": f"{row['original_symbol']} {row['original_type']}",
                "動爻": row["moving_marker"],
                "變卦爻": f"{row['changed_symbol']} {row['changed_type']}",
                "所屬": row["layer"],
            }
        )
    _render_html_table(rows, ["爻位", "本卦爻", "動爻", "變卦爻", "所屬"])
    st.caption("畫面由上爻往初爻顯示；程式計算與資料庫一律自下而上儲存。○＝陽爻動，×＝陰爻動。")


def _render_hexagram_reference(label: str, name: str, moving_line: int | None = None) -> None:
    item = load_hexagrams()[name]
    st.markdown(f"#### {label}：{item['unicode']} {name}（第 {item['sequence']} 卦）")
    st.caption(
        f"上卦 {item['upper']}｜下卦 {item['lower']}｜六爻自下而上 {item['binary_bottom_up']}｜"
        f"互卦 {item['related_hexagrams']['nuclear']}｜錯卦 {item['related_hexagrams']['opposite']}｜"
        f"綜卦 {item['related_hexagrams']['reversed']}"
    )
    st.write(f"**卦義提要（資料庫索引）**：{item['meaning_overview']}")
    st.write(f"**卦辭**：{item['judgment_text']}")
    with st.expander("彖傳與大象", expanded=(label == "本卦")):
        st.write(f"**彖傳**：{item['tuan_text']}")
        st.write(f"**大象**：{item['great_image_text']}")
    line_rows = []
    for line in item["lines"]:
        position = f"第{line['position']}爻"
        if moving_line == line["position"]:
            position += "（本次動爻）"
        line_rows.append(
            {
                "爻位": position,
                "爻辭": line["classic_text"],
                "小象": line["small_image_text"],
            }
        )
    special = item.get("special_line")
    if special:
        line_rows.append({"爻位": "用爻", "爻辭": special["classic_text"], "小象": special["small_image_text"]})
    _render_html_table(line_rows, ["爻位", "爻辭", "小象"])
    if item.get("wenyan_text"):
        with st.expander("文言全文"):
            st.write(item["wenyan_text"])


def _render_jiaoshi_reference(main_name: str, changed_name: str) -> None:
    hexagrams = load_hexagrams()
    yilin = load_jiaoshi_yilin()
    main = hexagrams[main_name]
    changed = hexagrams[changed_name]
    main_short = str(main["short_name"])
    changed_short = str(changed["short_name"])
    st.markdown(
        f"#### {main['unicode']} {main_name} 之 {changed['unicode']} {changed_name}"
    )
    st.caption(
        f"《焦氏易林》{main_short}之{changed_short}｜"
        f"本卦第 {main['sequence']} 卦，之卦第 {changed['sequence']} 卦"
    )
    st.write(yilin["entries"][main_short][changed_short])
    st.caption("只顯示《焦氏易林》原典林辭，不自動解釋，也不參與本次文字取數。")


def _render_casting_result(config: Any, store: CastingStore) -> None:
    casting: CastingInput | None = st.session_state.get("casting_input")
    result: HexagramResult | None = st.session_state.get("casting_result")
    if casting is None or result is None:
        st.info("填入三段內容後按「完整排卦」，這裡會顯示本卦、互卦、動爻與變卦。")
        return

    st.subheader("排卦結果")
    st.info(
        f"**起卦國曆時間**：{result.casting_moment.gregorian_text} "
        f"（{result.casting_moment.timezone}／{result.casting_moment.utc_offset}）  \n"
        f"**起卦農曆時間**：{result.casting_moment.lunar_text}"
    )
    st.caption("起卦時間在按下排卦時固定保存，只作排盤紀錄，不參與文字取數。")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("體卦／下卦", f"{result.body_gua} {result.body_number}")
    c2.metric("用卦／上卦", f"{result.use_gua} {result.use_number}")
    c3.metric("本卦", result.main_hexagram)
    c4.metric("動爻", f"{result.moving_line_label}（第{result.moving_line}爻）")

    h1, h2, h3 = st.columns(3)
    h1.metric("本卦", result.main_hexagram)
    h2.metric("互卦", result.mutual_hexagram)
    h3.metric("變卦", result.changed_hexagram)

    st.markdown("### 取數明細")
    st.markdown(
        "\n".join(
            [
                "| 輸入 | 計數 | 取餘 | 排卦結果 |",
                "|---|---:|---:|---|",
                f"| 體方段落 | {result.body_count} | ÷8 餘 {_modulo(result.body_modulo, 8)} | {result.body_gua}，先天數{result.body_number}，{result.body_element} |",
                f"| 用方段落 | {result.use_count} | ÷8 餘 {_modulo(result.use_modulo, 8)} | {result.use_gua}，先天數{result.use_number}，{result.use_element} |",
                f"| 完整中性段落 | {result.total_count} | ÷6 餘 {_modulo(result.moving_modulo, 6)} | 第{result.moving_line}爻動，{result.moving_line_label} |",
            ]
        )
    )

    st.markdown("### 六爻排盤")
    _render_line_table(result)

    st.markdown("### 本、互、動、變完整結構")
    st.markdown(
        "\n".join(
            [
                "| 項目 | 結構資料 |",
                "|---|---|",
                f"| 體卦 | {result.body_name}＝{result.body_gua}，數{result.body_number}，{result.body_element}，下卦 |",
                f"| 用卦 | {result.use_name}＝{result.use_gua}，數{result.use_number}，{result.use_element}，上卦 |",
                f"| 本卦 | {result.main_hexagram}，六爻自下而上 `{result.main_lines_bottom_up}` |",
                f"| 互卦 | 二三四爻成{result.mutual_lower_gua}，三四五爻成{result.mutual_upper_gua} → {result.mutual_hexagram} |",
                f"| 動爻 | 第{result.moving_line}爻，{result.moving_line_label}，{result.moving_original_type}變{result.moving_changed_type}，在{result.moving_side}／{result.moving_layer} |",
                f"| 體卦轉象 | {result.body_transition} |",
                f"| 用卦轉象 | {result.use_transition} |",
                f"| 變卦 | {result.changed_hexagram}，六爻自下而上 `{result.changed_lines_bottom_up}` |",
                f"| 本卦五行關係 | {result.relation} |",
                f"| 變卦五行關係 | {result.changed_relation} |",
            ]
        )
    )
    st.warning("以上只陳列排卦結構，不對球隊、勝負、比分、吉凶或事件發展作解讀。")

    st.markdown("### 本次涉及的經文資料")
    tabs = st.tabs(["本卦", "互卦", "變卦"])
    with tabs[0]:
        _render_hexagram_reference("本卦", result.main_hexagram, result.moving_line)
    with tabs[1]:
        _render_hexagram_reference("互卦", result.mutual_hexagram)
    with tabs[2]:
        _render_hexagram_reference("變卦", result.changed_hexagram)

    st.markdown("### 焦氏易林原典")
    _render_jiaoshi_reference(result.main_hexagram, result.changed_hexagram)

    report = build_markdown_report(casting, result)
    payload = json.dumps(
        {"input": casting.to_dict(), "casting": result.to_dict()},
        ensure_ascii=False,
        indent=2,
    )
    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "下載完整排盤 JSON",
        payload,
        file_name=f"{result.title or 'casting'}.json",
        mime="application/json",
        width="stretch",
    )
    d2.download_button(
        "下載完整排盤 Markdown",
        report,
        file_name=f"{result.title or 'casting'}.md",
        mime="text/markdown",
        width="stretch",
    )
    if d3.button("儲存本次排卦", width="stretch"):
        row = build_casting_row(casting, result)
        report_path = save_report(config, row, report)
        row["報告檔案"] = report_path
        _, action = store.upsert(row)
        st.success(f"{action}完成：{row['排卦ID']}")


def _render_database() -> None:
    trigrams = load_trigrams()
    hexagrams = load_hexagrams()
    yilin = load_jiaoshi_yilin()
    trigram_tab, hexagram_tab, yilin_tab = st.tabs(
        ["八卦資料", "六十四卦與三百八十四爻", "焦氏易林 4096 林辭"]
    )
    with trigram_tab:
        selected = st.selectbox("選擇經卦", list(trigrams), key="database_trigram")
        item = trigrams[selected]
        st.subheader(f"{item['unicode']} {selected}｜先天數 {item['number']}")
        st.json(item, expanded=True)
    with hexagram_tab:
        ordered = sorted(hexagrams, key=lambda name: int(hexagrams[name]["sequence"]))
        selected = st.selectbox(
            "選擇六十四卦",
            ordered,
            format_func=lambda name: f"{int(hexagrams[name]['sequence']):02d} {hexagrams[name]['unicode']} {name}",
            key="database_hexagram",
        )
        _render_hexagram_reference("資料庫", selected)
    with yilin_tab:
        ordered = sorted(hexagrams, key=lambda name: int(hexagrams[name]["sequence"]))
        main_col, changed_col = st.columns(2)
        main_name = main_col.selectbox(
            "本卦",
            ordered,
            format_func=lambda name: (
                f"{int(hexagrams[name]['sequence']):02d} {hexagrams[name]['unicode']} {name}"
            ),
            key="yilin_main_hexagram",
        )
        changed_name = changed_col.selectbox(
            "之卦",
            ordered,
            format_func=lambda name: (
                f"{int(hexagrams[name]['sequence']):02d} {hexagrams[name]['unicode']} {name}"
            ),
            key="yilin_changed_hexagram",
        )
        st.caption(
            f"已完整收錄 {yilin['entry_count']:,} 條林辭；可查任一「本卦 → 之卦」組合。"
        )
        _render_jiaoshi_reference(main_name, changed_name)
        with st.expander("版本、來源與標題校正紀錄"):
            st.write(f"版本：{yilin['edition']}｜作者標示：{yilin['author']}")
            st.json(yilin["source"], expanded=False)
            st.json(yilin["source_label_corrections"], expanded=False)


def _render_classic_content(payload: Any) -> None:
    if isinstance(payload, str):
        st.write(payload)
    elif isinstance(payload, list):
        for item in payload:
            _render_classic_content(item)
    elif isinstance(payload, dict):
        if payload.get("title"):
            st.subheader(str(payload["title"]))
        if payload.get("subtitle"):
            st.markdown(f"#### {payload['subtitle']}")
        if "content" in payload:
            _render_classic_content(payload["content"])
        else:
            st.json(payload, expanded=False)


def _render_classics() -> None:
    classics = load_classics()
    selected = st.selectbox("選擇易傳資料", list(classics), key="classic_document")
    st.caption("這些是獨立經典資料，不會自動套用到本次排卦，也不產生事件解讀。")
    _render_classic_content(classics[selected])


def _render_records(store: CastingStore) -> None:
    try:
        rows = store.load()
    except Exception as exc:
        st.error(f"讀取排卦紀錄失敗：{exc}")
        return
    if not rows:
        st.info("尚無已儲存的排卦紀錄。")
        return
    columns = [
        "排卦ID", "建立時間", "起卦農曆時間", "標題", "體方名稱", "用方名稱",
        "本卦", "互卦", "動爻爻名", "變卦",
    ]
    _render_html_table(rows, columns)
    st.download_button(
        "下載排卦紀錄 CSV",
        store.csv_bytes(rows),
        file_name="meihua_castings.csv",
        mime="text/csv",
    )


def _render_method() -> None:
    completeness = knowledge_completeness()
    st.subheader("知識庫完整性")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("八卦", f"{completeness['trigrams']}/8")
    m2.metric("六十四卦", f"{completeness['hexagrams']}/64")
    m3.metric("六爻資料", f"{completeness['line_records']}/384")
    m4.metric("易傳附錄", completeness["classic_appendices"])
    m5.metric("焦氏易林", f"{completeness['yilin_entries']}/4096")
    if completeness["is_complete"]:
        st.success("卦辭、彖傳、大象、384 條爻辭與小象，以及 4,096 條焦氏易林林辭全部通過完整性檢查。")
    st.subheader("固定排卦方法")
    st.json(load_meihua_principles(), expanded=True)


def run_app() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="☯", layout="wide")
    config = load_config(_secrets())
    store = CastingStore(config)

    st.title(APP_TITLE)
    st.caption(
        "輸入賽前文字後，只做可重現的文字取數與完整排卦。已移除 AI 解卦、足球實力、勝負方向、比分候選及賽後校準。"
    )
    st.sidebar.markdown("### 系統範圍")
    st.sidebar.success("只排卦，不解卦")
    st.sidebar.write("本卦、互卦、動爻、變卦、體用與完整經文資料")
    st.sidebar.caption(f"知識庫：{KNOWLEDGE_VERSION}")
    st.sidebar.write("儲存位置：" + ("GitHub 後台" if config.use_github_backend else "本機資料夾"))

    casting_tab, database_tab, classics_tab, records_tab, method_tab = st.tabs(
        ["完整排卦", "卦象資料庫", "易傳資料庫", "排卦紀錄", "方法與完整性"]
    )
    with casting_tab:
        with st.form("casting_form", clear_on_submit=False):
            st.markdown("#### 事件／比賽名稱")
            body_col, versus_col, use_col = st.columns([10, 1.5, 10])
            body_name = body_col.text_input(
                "體方名稱（vs 前）", placeholder="例如：A隊", key="body_name"
            )
            versus_col.markdown(
                '<div style="text-align:center;padding-top:2.35rem;'
                'font-weight:700;font-size:1rem;">vs</div>',
                unsafe_allow_html=True,
            )
            use_name = use_col.text_input(
                "用方名稱（vs 後）", placeholder="例如：B隊", key="use_name"
            )
            st.caption("事件名稱會自動組合為「體方名稱 vs 用方名稱」，不需要重複輸入。")
            category = st.text_input("內容類別", value="足球賽前內容")
            body_text = st.text_area("體方段落（用來取體卦／下卦）", height=150)
            use_text = st.text_area("用方段落（用來取用卦／上卦）", height=150)
            full_text = st.text_area("完整賽前中性段落（用來取動爻）", height=190)
            submitted = st.form_submit_button("完整排卦（不解卦）", type="primary", width="stretch")
        if submitted:
            try:
                body_name, use_name, title = _normalize_parties(body_name, use_name)
                casting = CastingInput(
                    title=title,
                    body_name=body_name,
                    use_name=use_name,
                    body_text=body_text,
                    use_text=use_text,
                    full_text=full_text,
                    category=category.strip() or "未分類",
                )
                result = calculate_casting(casting)
                st.session_state["casting_input"] = casting
                st.session_state["casting_result"] = result
                st.success(
                    f"排卦完成：本卦 {result.main_hexagram}｜互卦 {result.mutual_hexagram}｜"
                    f"{result.moving_line_label}動｜變卦 {result.changed_hexagram}"
                )
            except ValueError as exc:
                st.error(str(exc))
        _render_casting_result(config, store)
    with database_tab:
        _render_database()
    with classics_tab:
        _render_classics()
    with records_tab:
        _render_records(store)
    with method_tab:
        _render_method()


run_app()
