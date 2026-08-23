from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YuanlingNumericStar:
    number: int
    color_name: str
    qimen_jieqi_alias: str
    beidou_alias: str | None
    normalized_element: str
    element_authority: str
    source_note: str


# This registry is intentionally NOT qimen.constants.STAR_BY_HOME.
# The transmitted Yuanling text uses a distinct 一白/二黑/... layer around 伏身,
# 數主 and 中宮值日九星.  Element labels are a project normalization of the
# standard Luoshu five-element associations; they are not presented as a direct
# quotation from the reviewed passage.
NUMERIC_STARS: tuple[YuanlingNumericStar, ...] = (
    YuanlingNumericStar(1, "一白", "太乙", "貪狼", "水", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：一白太乙號貪狼"),
    YuanlingNumericStar(2, "二黑", "攝提", "巨門", "土", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：巨門二黑；卷一數主例稱黑星"),
    YuanlingNumericStar(3, "三碧", "軒轅", "祿存", "木", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：祿存三碧"),
    YuanlingNumericStar(4, "四綠", "招搖", "文曲", "木", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：四綠文曲"),
    YuanlingNumericStar(5, "五黃", "天符", "廉貞", "土", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：五黃廉貞"),
    YuanlingNumericStar(6, "六白", "青龍", "武曲", "金", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：六白武曲"),
    YuanlingNumericStar(7, "七赤", "咸池", "破軍", "金", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：七赤破軍"),
    YuanlingNumericStar(8, "八白", "太陰", "左輔", "土", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：八白左輔是太陰"),
    YuanlingNumericStar(9, "九紫", "天乙", "右弼", "火", "LUOSHU_STANDARD__PROJECT_NORMALIZATION", "卷三：九紫右弼"),
)

_BY_NUMBER = {star.number: star for star in NUMERIC_STARS}
_BY_ALIAS = {
    alias: star
    for star in NUMERIC_STARS
    for alias in (star.color_name, star.qimen_jieqi_alias, star.beidou_alias)
    if alias
}


def numeric_star(number: int) -> YuanlingNumericStar:
    try:
        return _BY_NUMBER[number]
    except KeyError as exc:
        raise ValueError(f"元靈數術九星號碼必須為1..9：{number}") from exc


def numeric_star_by_alias(alias: str) -> YuanlingNumericStar:
    try:
        return _BY_ALIAS[alias]
    except KeyError as exc:
        raise ValueError(f"未知元靈數術星名：{alias}") from exc


def star_registry_audit() -> dict[str, object]:
    return {
        "kind": "YUANLING_NUMERIC_STAR_REGISTRY",
        "count": len(NUMERIC_STARS),
        "independent_from_shijia_qimen_star_registry": True,
        "authority": "SOURCE_NAMES_PLUS_PROJECT_NORMALIZED_ELEMENTS",
        "warning": (
            "一白/二黑等數術星不可靜默等同天蓬/天芮等時家奇門九星；"
            "演數『遁至本時之星』的完整飛遁算法仍需原典校勘。"
        ),
        "stars": [star.__dict__ for star in NUMERIC_STARS],
    }
