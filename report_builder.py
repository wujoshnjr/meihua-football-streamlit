from __future__ import annotations

from knowledge_loader import load_hexagrams, load_trigrams
from models import CastingInput, HexagramResult
from version import APP_VERSION, KNOWLEDGE_VERSION


def _modulo_text(value: int, divisor: int) -> str:
    return str(value) if value else f"0（按規則作{divisor}）"


def _hexagram_reference(label: str, name: str, moving_line: int | None = None) -> str:
    item = load_hexagrams()[name]
    lines = [
        f"### {label}：{item['unicode']} {name}",
        "",
        f"- 文王卦序：第 {item['sequence']} 卦",
        f"- 上卦：{item['upper']}｜下卦：{item['lower']}",
        f"- 六爻（自下而上）：`{item['binary_bottom_up']}`",
        f"- 卦義提要：{item['meaning_overview']}",
        f"- 卦辭：{item['judgment_text']}",
        f"- 彖傳：{item['tuan_text']}",
        f"- 大象：{item['great_image_text']}",
        "",
        "| 爻位 | 爻辭 | 小象 |",
        "|---:|---|---|",
    ]
    for line in item["lines"]:
        marker = " **（本次動爻）**" if moving_line == line["position"] else ""
        lines.append(
            f"| {line['position']}{marker} | {line['classic_text']} | {line['small_image_text']} |"
        )
    if item.get("special_line"):
        special = item["special_line"]
        lines.append(f"| 用爻 | {special['classic_text']} | {special['small_image_text']} |")
    return "\n".join(lines)


def build_markdown_report(casting: CastingInput, result: HexagramResult) -> str:
    trigrams = load_trigrams()
    body = trigrams[result.body_gua]
    use = trigrams[result.use_gua]
    line_rows = [
        "| 爻位（上至下顯示） | 本卦 | 動爻 | 變卦 | 所屬 |",
        "|---:|:---:|:---:|:---:|---|",
    ]
    for row in reversed(result.line_table):
        line_rows.append(
            f"| {row['position_name']}／{row['line_label']} | {row['original_symbol']} {row['original_type']} | "
            f"{row['moving_marker'] or ''} | {row['changed_symbol']} {row['changed_type']} | {row['layer']} |"
        )

    return f"""# {result.title}｜完整排卦紀錄

> 系統版本：{APP_VERSION}
> 知識庫版本：{KNOWLEDGE_VERSION}
> 範圍：只排卦，不解卦；不預測勝負、比分或任何結果。

## 一、起卦時間

- 起卦國曆時間：{result.casting_moment.gregorian_text}
- 起卦農曆時間：{result.casting_moment.lunar_text}
- 時區：{result.casting_moment.timezone}／{result.casting_moment.utc_offset}
- 使用規則：時間只作排盤紀錄，不參與三段文字取數

## 二、輸入角色

- 體方名稱：{result.body_name}
- 用方名稱：{result.use_name}
- 類別：{casting.category}
- 固定配置：體卦為下卦，用卦為上卦

## 三、取數計算

- 體方段落：{result.body_count} 數；{result.body_count} ÷ 8 餘 {_modulo_text(result.body_modulo, 8)} → {result.body_gua}（先天數 {result.body_number}、五行 {result.body_element}）
- 用方段落：{result.use_count} 數；{result.use_count} ÷ 8 餘 {_modulo_text(result.use_modulo, 8)} → {result.use_gua}（先天數 {result.use_number}、五行 {result.use_element}）
- 完整中性段落：{result.total_count} 數；{result.total_count} ÷ 6 餘 {_modulo_text(result.moving_modulo, 6)} → 第 {result.moving_line} 爻動（{result.moving_line_label}）

## 四、八卦資料

| 角色 | 卦 | 卦象 | 先天數 | 五行 | 三爻自下而上 | 陰陽結構 | 自然象 | 性質 |
|---|---|:---:|---:|---|---|---|---|---|
| 體／下卦 | {result.body_gua} | {body['unicode']} | {body['number']} | {body['element']} | `{body['lines_bottom_up']}` | {body['yin_yang']} | {body['natural_image']} | {body['core_nature']} |
| 用／上卦 | {result.use_gua} | {use['unicode']} | {use['number']} | {use['element']} | `{use['lines_bottom_up']}` | {use['yin_yang']} | {use['natural_image']} | {use['core_nature']} |

## 五、本卦六爻排盤

{chr(10).join(line_rows)}

## 六、本、互、動、變結構

- 本卦：{result.main_hexagram}｜六爻自下而上 `{result.main_lines_bottom_up}`
- 互卦：二三四爻成下卦 {result.mutual_lower_gua}；三四五爻成上卦 {result.mutual_upper_gua} → {result.mutual_hexagram}｜`{result.mutual_lines_bottom_up}`
- 動爻：第 {result.moving_line} 爻／{result.moving_line_label}／{result.moving_side}／{result.moving_layer}；{result.moving_original_type}變{result.moving_changed_type}
- 變卦：{result.changed_hexagram}｜六爻自下而上 `{result.changed_lines_bottom_up}`
- 體卦轉象：{result.body_transition}
- 用卦轉象：{result.use_transition}
- 本卦體用五行關係：{result.relation}
- 變卦體用五行關係：{result.changed_relation}

## 七、經文資料

> 以下只列資料庫經文與卦義提要，不把內容套用到本次事件。

{_hexagram_reference('本卦', result.main_hexagram, result.moving_line)}

{_hexagram_reference('互卦', result.mutual_hexagram)}

{_hexagram_reference('變卦', result.changed_hexagram)}

## 八、原始文字

### 體方段落

{casting.body_text}

### 用方段落

{casting.use_text}

### 完整中性段落

{casting.full_text}
"""


__all__ = ["build_markdown_report"]
