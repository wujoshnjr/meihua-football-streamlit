from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
import pandas as pd
import streamlit as st

from qimen.calendar import LocalTimeError, aware_local_datetime
from qimen.engine import cast_qimen
from qimen.football import interpret_football
from qimen.football_ontology import (
    compose_football_meaning,
    football_dimensions,
    football_ontology_stats,
    load_football_ontology,
    search_football_meanings,
)
from qimen.interpretation import (
    RELATION_TYPES,
    build_interpretation_guide,
    focus_topics,
    interpretation_stats,
    load_interpretation_knowledge,
    search_relation_readings,
)
from qimen.knowledge import knowledge_stats, load_knowledge, search_knowledge
from qimen.protocol import EvidenceItem, MatchInput
from qimen.reporting import build_bundle, render_html, render_markdown
from version import __version__


st.set_page_config(
    page_title="奇門遁甲足球賽前研究系統",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
      [data-testid="stMetricValue"] {font-size: 1.45rem;}
      .qimen-note {border-left: 4px solid #a56b2a; padding: .7rem 1rem; background: #faf6ed; border-radius: 0 8px 8px 0;}
      .small-muted {color: #6f6b63; font-size: .9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _evidence_from_state() -> list[EvidenceItem]:
    rows = st.session_state.get("evidence_rows", [])
    evidence: list[EvidenceItem] = []
    for row_number, row in enumerate(rows, 1):
        if not str(row.get("title", "")).strip():
            continue
        try:
            published = datetime.fromisoformat(str(row.get("published_at", "")))
            retrieved = datetime.fromisoformat(str(row.get("retrieved_at", "")))
        except ValueError as exc:
            raise ValueError(f"證據表第 {row_number} 列時間須為 ISO 8601，並包含時區偏移") from exc
        evidence.append(EvidenceItem(
            title=str(row.get("title", "")).strip(),
            url=str(row.get("url", "")).strip(),
            published_at=published,
            retrieved_at=retrieved,
            category=str(row.get("category", "other")),
            team=str(row.get("team", "neutral")),
            material_update=bool(row.get("material_update", False)),
            reliability=str(row.get("reliability", "中")),
        ))
    return evidence


def _build_match(event_at: datetime) -> MatchInput:
    return MatchInput(
        match_id=st.session_state.match_id.strip(),
        home_team=st.session_state.home_team.strip(),
        away_team=st.session_state.away_team.strip(),
        competition=st.session_state.competition.strip(),
        event_at=event_at,
        timezone_name=st.session_state.timezone_name.strip(),
        venue=st.session_state.venue.strip(),
        city=st.session_state.city.strip(),
        evidence=_evidence_from_state(),
        both_teams_refreshed_after_material_update=st.session_state.get("both_refreshed", False),
    )


def _palace_card(number: int) -> None:
    state = st.session_state.board.palaces[number]
    flags = []
    if state.is_void:
        flags.append("旬空")
    if state.is_horse:
        flags.append("驛馬")
    with st.container(border=True):
        st.markdown(f"#### {state.name} · {state.direction}")
        st.caption(f"{state.trigram}｜{state.element}｜{' · '.join(flags) if flags else '—'}")
        st.markdown(
            f"**神**　{state.deity or '—'}  \n"
            f"**星**　{'・'.join(state.stars) or '—'}  \n"
            f"**門**　{state.door or '—'}  \n"
            f"**天盤**　{'・'.join(state.heaven_stems) or '—'}  \n"
            f"**地盤**　{state.earth_stem}"
            f"{('（寄 ' + '・'.join(state.earth_hidden_stems) + '）') if state.earth_hidden_stems else ''}"
        )


def _require_board() -> bool:
    if "board" not in st.session_state:
        st.info("請先在左側填入事件所在地時間，按「建立／重建奇門盤」。")
        return False
    return True


def _render_football_meaning(meaning, *, reading_limit: int | None = None) -> None:
    layer_readings = meaning.layer_readings[:reading_limit] if reading_limit else meaning.layer_readings
    st.write("重點足球維度：" + "、".join(meaning.football_dimensions))
    st.markdown("**分層可能表現**")
    st.markdown("\n".join(f"- {item}" for item in layer_readings))
    left, right = st.columns(2)
    with left:
        st.markdown("**可觀察訊號**")
        st.markdown("\n".join(f"- {item}" for item in meaning.observable_signals))
    with right:
        st.markdown("**反證條件**")
        st.markdown("\n".join(f"- {item}" for item in meaning.counter_signals))
    if meaning.interactions:
        st.markdown("**五行層間關係**")
        st.markdown("\n".join(f"- {item}" for item in meaning.interactions))
    st.caption(f"可信度標籤：{meaning.confidence}｜{meaning.boundary}")


def _relation_rows(relations) -> list[dict[str, str]]:
    return [{
        "類型": item.relation_label,
        "組合": f"{item.first}（{item.first_element}）→ {item.second}（{item.second_element}）",
        "五行方向": item.element_relation,
        "古典格名": item.classical_pattern or "—",
        "摘要": item.summary,
        "權威層級": item.authority,
        "注意": item.caution,
        "來源": item.source_id,
    } for item in relations]


st.title("奇門遁甲足球賽前研究系統")
st.caption(f"時家奇門・轉盤・拆補法｜版本 {__version__}")
st.markdown(
    '<div class="qimen-note">本系統把古典奇門知識與足球應用規約分層。盤內索引只排序候選情境，不自動輸出勝率、固定比分、期望進球或投注建議。</div>',
    unsafe_allow_html=True,
)

if "evidence_rows" not in st.session_state:
    st.session_state.evidence_rows = []

with st.sidebar:
    st.header("事件資料")
    st.text_input("研究編號", value="QIMEN-DEMO-001", key="match_id")
    st.text_input("主隊", value="主隊", key="home_team")
    st.text_input("客隊", value="客隊", key="away_team")
    st.text_input("賽事", value="賽前研究", key="competition")
    event_date = st.date_input("開賽日期", value=date.today() + timedelta(days=1))
    event_time = st.time_input("開賽時間", value=time(20, 0), step=300)
    st.text_input("IANA 時區", value="Asia/Taipei", key="timezone_name", help="例如 Asia/Taipei、Europe/London")
    st.text_input("場館", value="待確認", key="venue")
    st.text_input("城市", value="Taipei", key="city")
    focus_items = focus_topics()
    focus_names = {item["id"]: item["name"] for item in focus_items}
    with st.expander("起局前鎖定", expanded=True):
        st.text_area(
            "固定問題",
            value=focus_items[0]["question_prompt"],
            key="question_input",
            help="問題與焦點會在按下建立盤面時封存；之後修改須重建盤面。",
        )
        st.selectbox(
            "解盤焦點",
            [item["id"] for item in focus_items],
            format_func=lambda item_id: focus_names[item_id],
            key="focus_id",
        )
    cast_button = st.button("建立／重建奇門盤", type="primary", use_container_width=True)

    if cast_button:
        try:
            local_event = aware_local_datetime(
                datetime.combine(event_date, event_time),
                st.session_state.timezone_name.strip(),
            )
            match = _build_match(local_event)
            errors = match.validate()
            locked_question = st.session_state.question_input.strip()
            if not locked_question:
                errors.append("固定問題不可空白")
            if errors:
                for error in errors:
                    st.error(error)
            else:
                with st.spinner("按固定方法起局…"):
                    board = cast_qimen(local_event, match.timezone_name)
                    reading = interpret_football(board)
                    locked_at = datetime.now(tz=local_event.tzinfo)
                    guide = build_interpretation_guide(
                        board,
                        question=locked_question,
                        focus_id=st.session_state.focus_id,
                        match=match,
                        locked_at=locked_at,
                        locked_before_cast=True,
                    )
                st.session_state.match = match
                st.session_state.board = board
                st.session_state.reading = reading
                st.session_state.interpretation_guide = guide
                st.session_state.question_locked_at = locked_at
                st.success("奇門盤與解盤問題已鎖定")
        except (ValueError, LocalTimeError, RuntimeError) as exc:
            st.error(str(exc))

    st.divider()
    st.caption("方法鎖定")
    st.write("時家｜轉盤｜拆補")
    st.write("中五寄坤二｜天禽隨天芮")
    st.write("主隊日干｜客隊時干")


tab_board, tab_guide, tab_reading, tab_football_knowledge, tab_knowledge, tab_protocol, tab_export = st.tabs(
    ["九宮排盤", "起局／解盤助手", "賽事研究", "足球義理庫", "奇門知識庫", "資料協議", "匯出與稽核"]
)

with tab_board:
    if _require_board():
        board = st.session_state.board
        match = st.session_state.match
        a, b, c, d, e = st.columns(5)
        a.metric("遁局", board.ju_label)
        b.metric("三元", board.yuan)
        c.metric("值符", f"{board.chief_star}・{board.chief_star_palace}宮")
        d.metric("值使", f"{board.chief_door}・{board.chief_door_palace}宮")
        e.metric("節氣", board.calendar.solar_term)
        st.caption(
            f"事件：{match.event_at.isoformat()}｜四柱：{board.calendar.year_ganzhi} "
            f"{board.calendar.month_ganzhi} {board.calendar.day_ganzhi} {board.calendar.hour_ganzhi}｜"
            f"時旬：{board.hour_xun}（{board.xun_head_instrument}）"
        )

        for row in ((4, 9, 2), (3, 5, 7), (8, 1, 6)):
            columns = st.columns(3)
            for column, palace_number in zip(columns, row):
                with column:
                    _palace_card(palace_number)

        st.subheader("自動命中的結構")
        if board.patterns:
            st.dataframe(pd.DataFrame([{
                "格局／狀態": hit.name,
                "類別": hit.category,
                "宮位": hit.palace or "全盤／時格",
                "成立條件": hit.condition,
                "判讀": hit.reading,
                "注意": hit.caution,
            } for hit in board.patterns]), hide_index=True, use_container_width=True)
        else:
            st.info("未命中目前方法版本可自動判定的格局；不代表盤中沒有可讀結構。")

        with st.expander("方法與可重現性"):
            st.json({"method": board.to_dict()["method"], "warnings": board.warnings})

with tab_guide:
    guide_stats = interpretation_stats()
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("盤前校驗", guide_stats["precast_checks"])
    g2.metric("逐層判讀", guide_stats["reading_layers"])
    g3.metric("足球焦點", guide_stats["focus_topics"])
    g4.metric("關係矩陣", guide_stats["total_relations"])
    g5.metric("天地盤干", guide_stats["relation_counts"]["stem_pair"])
    st.caption(guide_stats["claim_boundary"])

    if "interpretation_guide" in st.session_state:
        guide = st.session_state.interpretation_guide
        st.subheader("已鎖定的問題與盤前稽核")
        st.info(f"問題：{guide.question}\n\n焦點：{guide.focus_name}｜鎖定：{guide.locked_at}")
        if (
            st.session_state.question_input.strip() != guide.question
            or st.session_state.focus_id != guide.focus_id
        ):
            st.warning("側欄的問題或焦點已變更，但目前盤仍使用上次鎖定值；請重建盤面才會生效。")
        audit_rows = [{
            "狀態": item.status,
            "校驗": item.name,
            "內容": item.detail,
        } for item in guide.audit.checks]
        st.dataframe(pd.DataFrame(audit_rows), hide_index=True, use_container_width=True)
        if guide.audit.overall == "FAIL":
            st.error("盤前稽核有阻斷項：" + "；".join(guide.audit.blockers))
        elif guide.audit.overall == "WARN":
            st.warning("盤前稽核可繼續，但仍有警告；最常見原因是尚未加入外部賽前證據。")
        else:
            st.success("盤前稽核全部通過。")

        left, right = st.columns(2)
        with left:
            st.markdown("**焦點鏡頭（不取代雙方固定用神）**")
            st.write("主符號：" + "、".join(guide.focus["primary_symbols"]))
            st.write("第二層：" + "、".join(guide.focus["secondary_lenses"]))
            st.write("先驗證：" + guide.focus["observable"])
            st.write("反證：" + guide.focus["counterevidence"])
        with right:
            st.markdown("**全局訊號**")
            st.markdown("\n".join(f"- {item}" for item in guide.global_signals))
        with st.expander("十層解盤順序", expanded=True):
            st.markdown("\n".join(f"- {item}" for item in guide.reading_order))

        st.subheader("本盤逐宮關係")
        palace_labels = {
            item.palace_name: item for item in guide.palace_guides
        }
        selected_palace_guide = palace_labels[
            st.selectbox("選擇宮位", list(palace_labels), key="guide_palace")
        ]
        st.write(selected_palace_guide.stack)
        st.caption(
            "結構修飾："
            + ("、".join(selected_palace_guide.structural_modifiers) or "—")
        )
        if selected_palace_guide.relations:
            st.dataframe(
                pd.DataFrame(_relation_rows(selected_palace_guide.relations)),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("中五依本版寄坤二；本宮沒有獨立門、星、神關係，請查看坤二宮。")
        st.markdown("\n".join(f"- {item}" for item in selected_palace_guide.verification_questions))
    else:
        st.info("先在側欄固定問題與焦點並建立盤面；下方 306 組關係知識仍可先查詢。")

    st.subheader("完整關係矩陣查詢")
    rq1, rq2 = st.columns([2, 1])
    with rq1:
        relation_query = st.text_input(
            "搜尋組合、格名或五行方向",
            placeholder="例如：青龍返首、門迫、天沖、後生前",
            key="relation_query",
        )
    with rq2:
        relation_type_label = st.selectbox(
            "關係類型",
            ["全部", *RELATION_TYPES.values()],
            key="relation_type_filter",
        )
    relation_type = next(
        (key for key, label in RELATION_TYPES.items() if label == relation_type_label),
        None,
    )
    relation_results = search_relation_readings(relation_query, relation_type=relation_type)
    st.caption(f"找到 {len(relation_results)} 組；矩陣總覆蓋 306 組。")
    if relation_results:
        st.dataframe(
            pd.DataFrame(_relation_rows(relation_results)),
            hide_index=True,
            use_container_width=True,
        )

    interpretation_data = load_interpretation_knowledge()
    with st.expander("應期候選、時間基準與常見錯誤"):
        st.markdown("**應期候選（不自動指定日期或分鐘）**")
        st.dataframe(pd.DataFrame([{
            "名稱": item["name"],
            "規則": item["rule"],
            "狀態": item["automation"],
            "注意": item["caution"],
        } for item in interpretation_data["timing_rules"]]), hide_index=True, use_container_width=True)
        st.markdown("**時間基準版本**")
        st.dataframe(pd.DataFrame([{
            "名稱": item["name"],
            "定義": item["definition"],
            "狀態": item["status"],
            "必要欄位": "、".join(item["required_fields"]),
        } for item in interpretation_data["time_basis_options"]]), hide_index=True, use_container_width=True)
        st.markdown("**高風險錯誤**")
        st.dataframe(pd.DataFrame([{
            "錯誤": item["name"],
            "症狀": item["symptom"],
            "預防": item["prevention"],
        } for item in interpretation_data["error_traps"]]), hide_index=True, use_container_width=True)

with tab_reading:
    if _require_board():
        reading = st.session_state.reading
        left, right = st.columns(2)
        for column, label, team_name, profile in (
            (left, "主隊／日干", st.session_state.match.home_team, reading.home),
            (right, "客隊／時干", st.session_state.match.away_team, reading.away),
        ):
            with column:
                with st.container(border=True):
                    st.subheader(f"{label}：{team_name}")
                    st.metric("盤內排序索引", profile.signal_index)
                    st.write(f"用神：**{profile.stem}**｜{profile.palace_name}")
                    st.write(f"星門神：{'・'.join(profile.stars)}｜{profile.door or '—'}｜{profile.deity or '—'}")
                    st.write(f"季節狀態：{profile.seasonal_state}")
                    st.success("有利條件：" + ("、".join(profile.strengths) or "未標示"))
                    st.warning("風險條件：" + ("、".join(profile.risks) or "未標示"))
                    with st.expander("完整足球義、可觀察訊號與反證"):
                        _render_football_meaning(profile.football_meaning)

        st.subheader("候選情境排序")
        st.dataframe(pd.DataFrame([{
            "排序": item.rank,
            "候選情境": item.title,
            "盤內索引": item.signal_index,
            "依據": "；".join(item.basis),
            "邊界": item.boundary,
        } for item in reading.scenarios]), hide_index=True, use_container_width=True)
        st.warning(reading.disclaimer, icon="⚠️")
        st.caption("足球映射版本：" + reading.mapping_version + "。此層是本專案規約，不是古籍原有的足球公式。")

with tab_football_knowledge:
    ontology = load_football_ontology()
    ontology_stats = football_ontology_stats()
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("足球分析維度", ontology_stats["dimensions"])
    o2.metric("完整基礎語義", ontology_stats["atomic_units"])
    o3.metric("核心組合覆蓋", f"{ontology_stats['core_combinations']:,}")
    o4.metric("含天地盤干", f"{ontology_stats['visible_stem_extended_combinations']:,}")
    st.info(ontology_stats["claim_boundary"])

    st.subheader("按足球情境反查奇門義")
    dimension_options = {"全部維度": None, **{item["name"]: item["id"] for item in football_dimensions()}}
    section_options = {
        "全部符號": None,
        "九宮": "palaces",
        "八門": "doors",
        "九星": "stars",
        "八神": "deities",
        "天干": "stems",
        "地支": "branches",
        "旺衰": "seasonal_states",
        "結構狀態": "structural_states",
        "格局": "patterns",
    }
    fq1, fq2, fq3 = st.columns([2, 1, 1])
    with fq1:
        football_query = st.text_input(
            "搜尋足球義",
            placeholder="例如：高位逼搶、VAR、傷停、門將、定位球、反擊",
            key="football_meaning_query",
        )
    with fq2:
        dimension_label = st.selectbox("足球維度", list(dimension_options), key="football_dimension_filter")
    with fq3:
        football_section_label = st.selectbox("奇門層", list(section_options), key="football_section_filter")
    football_results = search_football_meanings(
        football_query,
        dimension=dimension_options[dimension_label],
        section=section_options[football_section_label],
    )
    st.caption(f"找到 {len(football_results)} 個基礎語義；每筆都含可觀察訊號與反證。")
    if football_results:
        st.dataframe(pd.DataFrame([{
            "符號": item["key"],
            "奇門層": item["section_label"],
            "足球維度": "、".join(item["dimension_names"]),
            "可能表現": "；".join(item["possible_meanings"]),
            "可觀察訊號": "；".join(item["observable_signals"]),
            "反證": "；".join(item["counter_signals"]),
        } for item in football_results]), hide_index=True, use_container_width=True)

    st.subheader("全組合解讀器")
    st.write("依固定層次把任意宮、門、星、神、天地盤干、旺衰與格局組合成足球候選情境。")
    mappings = ontology["mappings"]
    core1, core2, core3, core4 = st.columns(4)
    with core1:
        selected_palace = st.selectbox("宮位環境", [item["key"] for item in mappings["palaces"]], key="compose_palace")
    with core2:
        selected_door = st.selectbox("八門行動", [item["key"] for item in mappings["doors"]], key="compose_door")
    with core3:
        selected_star = st.selectbox("九星能力", [item["key"] for item in mappings["stars"]], key="compose_star")
    with core4:
        selected_deity = st.selectbox("八神表現", [item["key"] for item in mappings["deities"]], key="compose_deity")

    visible_stems = ["不指定", *list("戊己庚辛壬癸丁丙乙")]
    extra1, extra2, extra3 = st.columns(3)
    with extra1:
        selected_heaven_stem = st.selectbox("天盤干觸發", visible_stems, key="compose_heaven_stem")
    with extra2:
        selected_earth_stem = st.selectbox("地盤干底層", visible_stems, key="compose_earth_stem")
    with extra3:
        selected_season = st.selectbox(
            "旺衰",
            ["不指定", *[item["key"] for item in mappings["seasonal_states"]]],
            key="compose_season",
        )
    selected_states = st.multiselect(
        "結構狀態（可複選）",
        [item["key"] for item in mappings["structural_states"]],
        key="compose_states",
    )
    selected_patterns = st.multiselect(
        "格局（可複選）",
        [item["key"] for item in mappings["patterns"]],
        key="compose_patterns",
    )
    composed = compose_football_meaning(
        palace=selected_palace,
        door=selected_door,
        stars=(selected_star,),
        deity=selected_deity,
        heaven_stems=() if selected_heaven_stem == "不指定" else (selected_heaven_stem,),
        earth_stem=None if selected_earth_stem == "不指定" else selected_earth_stem,
        seasonal_state=None if selected_season == "不指定" else selected_season,
        states=selected_states,
        patterns=selected_patterns,
    )
    with st.container(border=True):
        _render_football_meaning(composed)
    with st.expander("映射來源、層次與版本"):
        st.markdown("\n".join(f"- {item}" for item in composed.provenance))
        st.json({
            "mapping_version": composed.mapping_version,
            "symbols": composed.symbols,
            "composition_order": ontology["composition_order"],
            "coverage_formula": ontology["coverage_contract"]["formula"],
        })

with tab_knowledge:
    stats = knowledge_stats()
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("知識條目", stats["total"])
    k2.metric("九宮／門星神干", sum(stats.get(k, 0) for k in ("palaces", "doors", "stars", "deities", "stems")))
    k3.metric("格局與狀態", stats.get("patterns", 0))
    k4.metric("節氣", stats.get("solar_terms", 0))
    k5.metric("足球義", football_ontology_stats()["atomic_units"])
    k6.metric("來源", stats.get("sources", 0))

    sections = sorted({row["_section"] for row in load_knowledge()["records"]})
    col_query, col_section = st.columns([2, 1])
    with col_query:
        query = st.text_input("搜尋知識庫", placeholder="例如：值符、三奇、門迫、拆補、驛馬")
    with col_section:
        section = st.selectbox("資料分類", ["全部", *sections])
    results = search_knowledge(query, section)
    st.caption(f"找到 {len(results)} 筆；以下最多顯示 200 筆。")
    if results:
        labels = [f"{row['_title']}｜{row['_section']}｜{index + 1}" for index, row in enumerate(results[:200])]
        selected_label = st.selectbox("選擇條目查看完整內容", labels)
        selected = results[labels.index(selected_label)]
        st.json({key: value for key, value in selected.items() if not key.startswith("_")}, expanded=True)
        st.dataframe(pd.DataFrame([{
            "名稱": row["_title"],
            "分類": row["_section"],
            "資料檔": row["_file"],
        } for row in results[:200]]), hide_index=True, use_container_width=True)

    with st.expander("來源與編纂政策"):
        source_data = load_knowledge()["files"]["sources.json"]
        for source in source_data["sources"]:
            st.markdown(f"- [{source['title']}]({source['url']})：{source['use']}")
        st.markdown("\n".join(f"- {policy}" for policy in source_data["source_policy"]))

with tab_protocol:
    st.subheader("賽前證據表")
    st.write("所有時間請填含偏移的 ISO 8601，例如 `2026-08-14T12:30:00+08:00`。空表仍可起局，但代表沒有外部賽事證據。")
    evidence_df = pd.DataFrame(st.session_state.evidence_rows, columns=[
        "title", "url", "published_at", "retrieved_at", "category", "team", "material_update", "reliability"
    ])
    edited = st.data_editor(
        evidence_df,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "title": st.column_config.TextColumn("標題"),
            "url": st.column_config.LinkColumn("URL"),
            "published_at": st.column_config.TextColumn("發布時間"),
            "retrieved_at": st.column_config.TextColumn("擷取時間"),
            "category": st.column_config.SelectboxColumn(
                "類別", options=["official_schedule", "official_lineup", "injury", "suspension", "team_form", "travel", "venue", "weather", "other"]
            ),
            "team": st.column_config.SelectboxColumn("隊伍", options=["home", "away", "neutral"]),
            "material_update": st.column_config.CheckboxColumn("重大更新"),
            "reliability": st.column_config.SelectboxColumn("可靠度", options=["高", "中", "低"]),
        },
        key="evidence_editor",
    )
    st.session_state.evidence_rows = edited.fillna("").to_dict("records")
    st.checkbox("freeze_at 後如有重大更新，已對兩隊同步刷新", key="both_refreshed")

    st.subheader("固定資料規約")
    st.markdown(
        """
        - `freeze_at = event_at - 6 hours`。
        - 僅可使用開賽前已發布、且開賽前已擷取的資料。
        - freeze_at 後只接受重大先發、傷病或停賽更新，並必須對兩隊同步刷新。
        - 結果口徑固定為 90 分鐘加補時，不含延長賽與點球。
        - 賽後資訊只能進評估層，不得回灌或重寫賽前研究。
        """
    )
    if "match" in st.session_state:
        match = st.session_state.match
        st.write(f"目前 freeze_at：`{match.freeze_at.isoformat()}`")
        st.json({"integrity": match.integrity_status(), "errors": match.validate()})
    st.info("更新證據表後，請按左側「建立／重建奇門盤」，讓完整性檢查重新執行。")

with tab_export:
    if _require_board():
        match = st.session_state.match
        board = st.session_state.board
        reading = st.session_state.reading
        guide = st.session_state.interpretation_guide
        markdown_report = render_markdown(match, board, reading, guide=guide)
        bundle = build_bundle(
            match,
            board,
            reading,
            guide=guide,
            locked_at=st.session_state.question_locked_at,
        )
        bundle_json = json.dumps(bundle, ensure_ascii=False, indent=2)
        html_report = render_html(markdown_report)

        st.subheader("可重現研究檔")
        st.code(f"SHA-256：{bundle['fingerprint_sha256']}", language=None)
        d1, d2, d3 = st.columns(3)
        d1.download_button("下載 JSON 稽核包", bundle_json, f"{match.match_id}-qimen.json", "application/json", use_container_width=True)
        d2.download_button("下載 Markdown 報告", markdown_report, f"{match.match_id}-qimen.md", "text/markdown", use_container_width=True)
        d3.download_button("下載 HTML 報告", html_report, f"{match.match_id}-qimen.html", "text/html", use_container_width=True)
        with st.expander("報告預覽"):
            st.markdown(markdown_report)
        with st.expander("原始 JSON"):
            st.json(bundle)

st.divider()
st.caption("研究／教育用途。奇門遁甲屬傳統術數；不得替代醫療、法律、財務或投注專業判斷。")
