import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "梅花易數足球自動預測系統 v1"
DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

CASES_CSV = DATA_DIR / "meihua_cases.csv"
CASES_XLSX = DATA_DIR / "meihua_cases.xlsx"

BAGUA_BY_REMAINDER = {1: "乾", 2: "兌", 3: "離", 4: "震", 5: "巽", 6: "坎", 7: "艮", 0: "坤"}
BAGUA_NUMBER = {"乾": 1, "兌": 2, "離": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
BAGUA_LINES = {"乾": "111", "兌": "110", "離": "101", "震": "100", "巽": "011", "坎": "010", "艮": "001", "坤": "000"}
LINES_TO_BAGUA = {v: k for k, v in BAGUA_LINES.items()}
ELEMENTS = {"乾": "金", "兌": "金", "離": "火", "震": "木", "巽": "木", "坎": "水", "艮": "土", "坤": "土"}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

HEXAGRAM_NAMES = {
    ("乾", "乾"): "乾為天", ("乾", "兌"): "天澤履", ("乾", "離"): "天火同人", ("乾", "震"): "天雷無妄", ("乾", "巽"): "天風姤", ("乾", "坎"): "天水訟", ("乾", "艮"): "天山遯", ("乾", "坤"): "天地否",
    ("兌", "乾"): "澤天夬", ("兌", "兌"): "兌為澤", ("兌", "離"): "澤火革", ("兌", "震"): "澤雷隨", ("兌", "巽"): "澤風大過", ("兌", "坎"): "澤水困", ("兌", "艮"): "澤山咸", ("兌", "坤"): "澤地萃",
    ("離", "乾"): "火天大有", ("離", "兌"): "火澤睽", ("離", "離"): "離為火", ("離", "震"): "火雷噬嗑", ("離", "巽"): "火風鼎", ("離", "坎"): "火水未濟", ("離", "艮"): "火山旅", ("離", "坤"): "火地晉",
    ("震", "乾"): "雷天大壯", ("震", "兌"): "雷澤歸妹", ("震", "離"): "雷火豐", ("震", "震"): "震為雷", ("震", "巽"): "雷風恆", ("震", "坎"): "雷水解", ("震", "艮"): "雷山小過", ("震", "坤"): "雷地豫",
    ("巽", "乾"): "風天小畜", ("巽", "兌"): "風澤中孚", ("巽", "離"): "風火家人", ("巽", "震"): "風雷益", ("巽", "巽"): "巽為風", ("巽", "坎"): "風水渙", ("巽", "艮"): "風山漸", ("巽", "坤"): "風地觀",
    ("坎", "乾"): "水天需", ("坎", "兌"): "水澤節", ("坎", "離"): "水火既濟", ("坎", "震"): "水雷屯", ("坎", "巽"): "水風井", ("坎", "坎"): "坎為水", ("坎", "艮"): "水山蹇", ("坎", "坤"): "水地比",
    ("艮", "乾"): "山天大畜", ("艮", "兌"): "山澤損", ("艮", "離"): "山火賁", ("艮", "震"): "山雷頤", ("艮", "巽"): "山風蠱", ("艮", "坎"): "山水蒙", ("艮", "艮"): "艮為山", ("艮", "坤"): "山地剝",
    ("坤", "乾"): "地天泰", ("坤", "兌"): "地澤臨", ("坤", "離"): "地火明夷", ("坤", "震"): "地雷復", ("坤", "巽"): "地風升", ("坤", "坎"): "地水師", ("坤", "艮"): "地山謙", ("坤", "坤"): "坤為地",
}

HEXAGRAM_KNOWLEDGE = {
    "乾為天": "剛健、強壓、主導、完成、硬度與領袖象。乾重接夬、大有、大壯時不可過度保守。",
    "坤為地": "厚、承受、集體、穩定、防守與壓實。強方坤可成整體厚勢，弱方坤可能被壓扁。",
    "水雷屯": "初始艱難、混亂中啟動、阻塞未開。開局不順但可能壓力中突然啟動。",
    "山水蒙": "不明、混沌、選擇不清、出路不明。常不利被壓方順暢解局。",
    "水天需": "等待、蓄勢、未急於完成。前段未必立刻進球，後段看是否打開。",
    "天水訟": "爭持、拉鋸、碰撞、節奏破碎。不可固定判低比分，需看後段是否裂口。",
    "地水師": "軍陣、紀律、防守結構、集體對抗。常見防守密度、反擊與組織壓制。",
    "水地比": "靠近、黏住、互相牽制。不一定比分接近，也可能弱方被壓在強方節奏裡。",
    "風天小畜": "小有積蓄、先蓄後放。不是固定小比分，可能強方先蓄後打開。",
    "天澤履": "謹慎前行、危險邊緣。乾力踩開兌口則能小勝。",
    "地天泰": "通達、攻防流通。強方能把優勢轉成進展。",
    "天地否": "閉塞、不通、銜接斷。通常先收斂，除非動爻破閉塞。",
    "天火同人": "同心、團隊共同目標。代表團隊意志、前場配合與壓迫一致。",
    "火天大有": "資源充足、主導權、場面掌握。強方有球有勢有機會，可上修。",
    "地山謙": "低姿態、收斂、藏鋒。常先守、低位、靠細節取利。",
    "雷地豫": "動員、情緒、聲勢。主場氣勢或開局節奏可被鼓起。",
    "澤雷隨": "順勢、被節奏帶動。可能是反擊順勢而來。",
    "山風蠱": "積弊、內部問題、修補。代表防線舊問題或中場失衡。",
    "地澤臨": "壓近、逼近。強方逐步壓到禁區前、靠近破門口。",
    "風地觀": "觀察、審視、等待時機。控節奏、找弱點、試探防線。",
    "火雷噬嗑": "咬合、突破阻隔、強行處理。離火震雷配合時進球機會明顯。",
    "山火賁": "技術亮點、表面光彩。不一定大比分，可能好看但效率有限。",
    "山地剝": "剝落、削弱、侵蝕。可剝防線，也可削薄雙方完成度。",
    "地雷復": "回來、反擊、重新啟動。被壓後重新起勢或守住後回轉。",
    "天雷無妄": "突發、非預期。意外進球、失誤、VAR或節奏驟變。",
    "山天大畜": "大蓄、積累力量、強力收束。可能取得優勢後控住。",
    "山雷頤": "口、供給、餵球、前場支點。重點是球能否餵到支點。",
    "澤風大過": "承載過重、壓力過量、結構臨界。從強攻卦來可放大，從困卦來可能只是壓力過重。",
    "坎為水": "重險、連續危機、水勢與門前險象。不是固定低分。",
    "離為火": "火力、明、暴露、前場亮度。若變艮則火勢受止。",
    "澤山咸": "感應、互動、彼此觸發。可能一方進球後帶動另一方回應。",
    "雷風恆": "持久、反覆、長時間維持。可能長時間施壓或拉鋸。",
    "天山遯": "退避、收縮、避鋒。代表退守、讓球權或被迫後撤。",
    "雷天大壯": "強勢壯大、衝擊、力量外放。進攻可猛，也可能過猛留反擊空間。",
    "火地晉": "推進、升進、逐步擴大優勢。常一步步打開。",
    "地火明夷": "光明受傷、能力被壓住。強點被限制、攻擊亮度被埋。",
    "風火家人": "組織、角色分工、前場供應鏈。能形成機會但不是必然大爆。",
    "火澤睽": "乖離、不合、節奏不順。有破口但不流暢。",
    "水山蹇": "阻難、推進受阻、空間被封。通常先收斂。",
    "雷水解": "解開、釋放、脫困。被卡局面可能被打開。",
    "山澤損": "削減、修剪、收斂。不只削弱方，也可能削體方。",
    "風雷益": "增益、加強。體用同氣時可能雙方都被帶動。",
    "澤天夬": "決裂、破口、破堤。乾重化夬時要注意大破口。",
    "天風姤": "突然遭遇、牽制、主動方遇阻。代表突發反擊或強方遇阻。",
    "澤地萃": "聚集、禁區混戰、二點球、角球。弱方也可能靠萃得到破口。",
    "地風升": "逐步推高、慢慢推進。看後續是否受阻。",
    "澤水困": "受困、空間不足、有險難釋放。要判斷是體方被困，還是兌口困不住坎水。",
    "水風井": "固定供給、定位球、固定支點或中路供應。",
    "澤火革": "變革、戰術調整、換人、局面翻轉。",
    "火風鼎": "重組、成形、資源配置。代表陣型與人員組合成熟。",
    "震為雷": "強烈啟動、連續衝擊。震數4常要保留。",
    "艮為山": "止、阻擋、防守、高點、收住。也可用高點製造機會。",
    "風山漸": "漸進、慢慢逼近。不是瞬間爆開。",
    "雷澤歸妹": "非常態結合、突發配合或位置錯位。混亂中的機會。",
    "雷火豐": "盛大、火雷俱發、機會多。若不收，比分可偏大。",
    "火山旅": "客旅、不安定、臨時應對。攻防連接不長久。",
    "巽為風": "滲透、邊路、傳導、逐步侵入。巽變艮常先開後收。",
    "兌為澤": "雙口、破門口、缺口。要看哪個口變進球，哪個口變防線缺口。",
    "風水渙": "風吹水散、防線渙散、節奏打開。用方巽在上常攪動體方坎水。",
    "水澤節": "節制、控制、有度。常把比分收住。",
    "風澤中孚": "真機會、可信連線、少數有效處理。通常不是亂戰大爆。",
    "雷山小過": "小幅越過、細節勝負。靠一次反擊、定位球或小破口。",
    "水火既濟": "完成、攻勢能落成。要看是誰完成。",
    "火水未濟": "未完成、差一步。威脅有但臨門差。",
}

BAGUA_KNOWLEDGE = {"乾": "剛健、硬度、完成、強攻、高點。", "兌": "口、缺口、破門、傳中。", "離": "火、明、暴露、前場亮度。", "震": "雷動、突發、啟動、衝擊。", "巽": "風、滲透、邊路、傳導。", "坎": "險、陷、水勢、門前險象。", "艮": "止、山、防守、阻擋。", "坤": "厚、承受、集體、壓實。"}

# 計數與起卦

def count_meihua_units(text: str) -> int:
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text or ""))
    token_pattern = r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ſƀ-ɏ0-9]+(?:[-'.’][A-Za-zÀ-ÖØ-öø-ÿĀ-ſƀ-ɏ0-9]+)*"
    foreign_count = len(re.findall(token_pattern, text or ""))
    return chinese_count + foreign_count


def number_to_bagua(number: int) -> str:
    return BAGUA_BY_REMAINDER[number % 8]


def moving_line_from_total(total: int) -> int:
    r = total % 6
    return 6 if r == 0 else r


def get_hexagram_name(upper: str, lower: str) -> str:
    return HEXAGRAM_NAMES[(upper, lower)]


def get_mutual_hexagram(upper: str, lower: str) -> dict:
    six = BAGUA_LINES[lower] + BAGUA_LINES[upper]
    lower_m = LINES_TO_BAGUA[six[1:4]]
    upper_m = LINES_TO_BAGUA[six[2:5]]
    return {"upper": upper_m, "lower": lower_m, "name": get_hexagram_name(upper_m, lower_m)}


def get_changed_hexagram(upper: str, lower: str, moving_line: int) -> dict:
    six = list(BAGUA_LINES[lower] + BAGUA_LINES[upper])
    idx = moving_line - 1
    six[idx] = "0" if six[idx] == "1" else "1"
    lower_c = LINES_TO_BAGUA["".join(six[:3])]
    upper_c = LINES_TO_BAGUA["".join(six[3:])]
    return {"upper": upper_c, "lower": lower_c, "name": get_hexagram_name(upper_c, lower_c)}


def body_use_relation(body_gua: str, use_gua: str) -> str:
    b = ELEMENTS[body_gua]
    u = ELEMENTS[use_gua]
    if b == u:
        return f"比和：體用同為{b}"
    if GENERATES[b] == u:
        return f"體生用：體方{b}生用方{u}"
    if GENERATES[u] == b:
        return f"用生體：用方{u}生體方{b}"
    if CONTROLS[b] == u:
        return f"體剋用：體方{b}剋用方{u}"
    if CONTROLS[u] == b:
        return f"用剋體：用方{u}剋體方{b}"
    return "未判定"


def calculate_match_hexagram(match_name, body_team, use_team, body_text, use_text, full_text) -> dict:
    body_count = count_meihua_units(body_text)
    use_count = count_meihua_units(use_text)
    total_count = count_meihua_units(full_text)
    body_gua = number_to_bagua(body_count)
    use_gua = number_to_bagua(use_count)
    mutual = get_mutual_hexagram(use_gua, body_gua)
    moving_line = moving_line_from_total(total_count)
    changed = get_changed_hexagram(use_gua, body_gua, moving_line)
    return {
        "match_name": match_name, "body_team": body_team, "use_team": use_team,
        "body_count": body_count, "use_count": use_count, "total_count": total_count,
        "body_gua": body_gua, "use_gua": use_gua,
        "body_number": BAGUA_NUMBER[body_gua], "use_number": BAGUA_NUMBER[use_gua],
        "main_hexagram": get_hexagram_name(use_gua, body_gua),
        "mutual_hexagram": mutual["name"],
        "moving_line": moving_line,
        "moving_side": "體方" if moving_line <= 3 else "用方",
        "changed_hexagram": changed["name"],
        "relation": body_use_relation(body_gua, use_gua),
    }

# 自動比分預測引擎

CALIBRATED_PATTERNS = {
    ("坎", "乾", "天水訟", "風火家人", 6, "用方", "澤水困"): {"scores": [(3, 1), (2, 1), (1, 1)], "reason": "用乾生體坎，六爻乾變兌，容易形成用方硬守到極點後裂口；體方坎水不可壓太低。"},
    ("坎", "巽", "風水渙", "山雷頤", 5, "用方", "山水蒙"): {"scores": [(0, 2), (0, 1), (1, 2)], "reason": "體坎生用巽，用方巽風在上形成風水渙，先吹散體方坎水；五爻巽變艮，打開後收住。"},
    ("坎", "兌", "澤水困", "風火家人", 3, "體方", "澤風大過"): {"scores": [(1, 1), (2, 1), (1, 0)], "reason": "澤水困為本卦時，體方坎水先受困；坎變巽多是解出一球，大過若從困局來，不宜直接大幅上修。"},
    ("兌", "兌", "兌為澤", "風火家人", 4, "用方", "水澤節"): {"scores": [(3, 0), (2, 0), (3, 1)], "reason": "兌為開口，家人使強方組織連線擴大破口；用方兌變坎時，常是自身防線坎險，水澤節收住比分。"},
    ("坤", "坤", "坤為地", "坤為地", 5, "用方", "水地比"): {"scores": [(4, 0), (3, 0), (4, 1)], "reason": "雙坤不一定低分；強方體坤可形成整體厚勢，用方坤變坎可能是防守核心位反覆坎險。"},
    ("坎", "坤", "地水師", "地雷復", 2, "體方", "坤為地"): {"scores": [(0, 2), (0, 1), (1, 2)], "reason": "用方坤土剋體坎，地水師代表軍陣壓制，體方坎變坤常被用方厚土吸收。"},
}

OPEN_HEXAGRAMS = {"乾為天", "離為火", "震為雷", "兌為澤", "雷火豐", "火天大有", "澤天夬", "雷天大壯", "火雷噬嗑", "雷水解", "風水渙", "澤地萃", "風雷益", "火地晉", "地天泰"}
TIGHT_HEXAGRAMS = {"天水訟", "澤水困", "水山蹇", "山水蒙", "艮為山", "地山謙", "水澤節", "山澤損", "火澤睽", "天地否", "天山遯", "風澤中孚"}
BODY_FAVOR_HEXAGRAMS = {"火天大有", "地天泰", "火地晉", "雷天大壯", "澤天夬", "雷水解", "風雷益"}
USE_FAVOR_HEXAGRAMS = {"風水渙", "天水訟", "澤水困", "山水蒙", "天地否"}
RELEASE_CHANGED = {"澤天夬", "雷水解", "風水渙", "震為雷", "離為火", "雷火豐", "火地晉"}
RESTRICT_CHANGED = {"水澤節", "山澤損", "艮為山", "山水蒙", "地山謙", "天地否", "天山遯"}


def clamp_goal(v: float) -> int:
    return int(round(max(0, min(6, v))))


def score_tuple_to_text(score):
    return f"{score[0]}-{score[1]}"


def prediction_key(result):
    return (result["body_gua"], result["use_gua"], result["main_hexagram"], result["mutual_hexagram"], result["moving_line"], result["moving_side"], result["changed_hexagram"])


def generic_predict_scores(result: dict) -> dict:
    body_gua = result["body_gua"]
    use_gua = result["use_gua"]
    main = result["main_hexagram"]
    mutual = result["mutual_hexagram"]
    changed = result["changed_hexagram"]
    relation = result["relation"]
    moving_side = result["moving_side"]
    moving_line = result["moving_line"]

    body = {"乾": 1.2, "兌": 1.3, "離": 1.6, "震": 1.8, "巽": 1.5, "坎": 1.4, "艮": 0.9, "坤": 1.0}[body_gua]
    use = {"乾": 1.1, "兌": 1.2, "離": 1.5, "震": 1.7, "巽": 1.5, "坎": 1.3, "艮": 0.9, "坤": 1.0}[use_gua]
    reasons = []

    if main in OPEN_HEXAGRAMS:
        body += 0.4; use += 0.25; reasons.append(f"本卦「{main}」偏開，雙方進球空間上修。")
    if main in TIGHT_HEXAGRAMS:
        body -= 0.25; use -= 0.25; reasons.append(f"本卦「{main}」偏收、偏困或偏拉鋸，原始卦數先折減。")
    if main in BODY_FAVOR_HEXAGRAMS:
        body += 0.35; reasons.append(f"本卦「{main}」對體方較有利，體方上修。")
    if main in USE_FAVOR_HEXAGRAMS:
        use += 0.25; reasons.append(f"本卦「{main}」較偏用方壓力，用方上修。")

    if relation.startswith("體生用"):
        body -= 0.2; use += 0.35; reasons.append("體生用：體方力量流向用方，用方得勢。")
    elif relation.startswith("用生體"):
        body += 0.45; use -= 0.1; reasons.append("用生體：用方力量生出體方機會，體方得勢。")
    elif relation.startswith("體剋用"):
        body += 0.25; use -= 0.15; reasons.append("體剋用：體方能壓制用方，但不直接等於多球。")
    elif relation.startswith("用剋體"):
        body -= 0.3; use += 0.25; reasons.append("用剋體：用方壓制體方，但仍需看是否轉成有效進球。")
    elif relation.startswith("比和"):
        body += 0.05; use += 0.05; reasons.append("體用比和：雙方節奏接近，需看本卦與變卦決定誰破局。")

    if mutual in {"風火家人", "山雷頤", "水火既濟", "火雷噬嗑", "雷水解"}:
        body += 0.2; use += 0.15; reasons.append(f"互卦「{mutual}」代表中段供應鏈或壓力釋放，雙方機會略增。")
    if mutual in {"山澤損", "山地剝", "水澤節", "水山蹇"}:
        body -= 0.2; use -= 0.15; reasons.append(f"互卦「{mutual}」削弱或限制中段完成度。")

    if moving_side == "體方":
        if changed in RELEASE_CHANGED:
            body += 0.45; reasons.append(f"動爻在體方且變卦「{changed}」偏打開，體方後段上修。")
        elif changed in RESTRICT_CHANGED:
            body -= 0.25; reasons.append(f"動爻在體方且變卦「{changed}」偏收束，體方後段折減。")
    else:
        if changed in RELEASE_CHANGED:
            use += 0.45; reasons.append(f"動爻在用方且變卦「{changed}」偏打開，用方後段上修。")
        elif changed in RESTRICT_CHANGED:
            use -= 0.2; reasons.append(f"動爻在用方且變卦「{changed}」偏收束，用方後段折減。")

    if moving_line == 6:
        reasons.append("六爻動代表後段極點，要注意硬守到極點後裂口或領先方收住。")
        if use_gua == "乾" and changed.startswith("澤"):
            body += 0.35; reasons.append("用方乾到六爻變兌，常見硬度到極點後露口，體方可上修。")
    if body_gua == "坎" and relation.startswith("用生體"):
        body += 0.35; reasons.append("體方坎水得用方生助時，不可把坎水壓太低。")
    if changed in {"水澤節", "山澤損", "艮為山"} and body + use > 3.2:
        body *= 0.88; use *= 0.88; reasons.append(f"變卦「{changed}」有節制或削減，總進球略收。")

    first = (clamp_goal(body), clamp_goal(use))
    candidates = [first]
    second = (max(0, first[0] - 1), first[1]) if first[0] >= first[1] else (first[0], max(0, first[1] - 1))
    candidates.append(second)
    if first[0] > first[1]:
        third = (first[0], min(3, first[1] + 1))
    elif first[1] > first[0]:
        third = (min(3, first[0] + 1), first[1])
    else:
        third = (first[0] + 1, first[1]) if body >= use else (first[0], first[1] + 1)
    candidates.append(third)

    cleaned = []
    for s in candidates:
        s = (max(0, min(6, s[0])), max(0, min(6, s[1])))
        if s not in cleaned:
            cleaned.append(s)
    while len(cleaned) < 3:
        a, b = cleaned[-1]
        cleaned.append((min(6, a + 1), b) if a <= b else (a, min(6, b + 1)))
    return {"scores": cleaned[:3], "reason": "；".join(reasons) or "依一般卦勢權重折算。", "method": "general_rules"}


def predict_scores(result: dict) -> dict:
    key = prediction_key(result)
    if key in CALIBRATED_PATTERNS:
        p = CALIBRATED_PATTERNS[key]
        return {"scores": p["scores"], "reason": p["reason"], "method": "calibrated_pattern"}
    return generic_predict_scores(result)

# 輸出、儲存、統計

def normalize_score(score: str) -> str:
    score = str(score or "").strip()
    if not score:
        return ""
    m = re.search(r"(\d+)\s*[-:：比]\s*(\d+)", score)
    return f"{int(m.group(1))}-{int(m.group(2))}" if m else score


def parse_score(score: str):
    score = normalize_score(score)
    m = re.search(r"^(\d+)-(\d+)$", score)
    return (int(m.group(1)), int(m.group(2))) if m else None


def score_outcome(score: str) -> str:
    p = parse_score(score)
    if not p:
        return ""
    return "體勝" if p[0] > p[1] else "用勝" if p[0] < p[1] else "平"


def total_goals(score: str):
    p = parse_score(score)
    return p[0] + p[1] if p else None


def score_result(first, second, third, actual):
    first, second, third, actual = map(normalize_score, [first, second, third, actual])
    fo, ao = score_outcome(first), score_outcome(actual)
    tg_first, tg_actual = total_goals(first), total_goals(actual)
    return {
        "首選命中": "是" if first and actual and first == actual else "否",
        "第二選命中": "是" if second and actual and second == actual else "否",
        "第三選命中": "是" if third and actual and third == actual else "否",
        "三選一命中": "是" if actual and actual in [first, second, third] else "否",
        "首選勝平負": fo,
        "實際勝平負": ao,
        "首選勝平負命中": "是" if fo and ao and fo == ao else "否",
        "首選總進球誤差": abs(tg_first - tg_actual) if tg_first is not None and tg_actual is not None else "",
    }


def build_markdown_report(result, prediction, actual_score="", review=""):
    first, second, third = [score_tuple_to_text(s) for s in prediction["scores"]]
    actual = normalize_score(actual_score)
    return f"""# {result['match_name']}

## 一、體用設定

- 體方：{result['body_team']}
- 用方：{result['use_team']}
- 判斷範圍：90 分鐘，不含延長賽與 PK

---

## 二、起卦取數

| 取數項目 | 字數 | 對應卦 | 卦數 |
|---|---:|---|---:|
| {result['body_team']}段 | {result['body_count']} | {result['body_gua']} | {result['body_number']} |
| {result['use_team']}段 | {result['use_count']} | {result['use_gua']} | {result['use_number']} |
| 全段總數 | {result['total_count']} | {result['moving_line']}爻動 | - |

---

## 三、卦象結果

- 體卦：{result['body_team']} = {result['body_gua']}：{BAGUA_KNOWLEDGE.get(result['body_gua'], '')}
- 用卦：{result['use_team']} = {result['use_gua']}：{BAGUA_KNOWLEDGE.get(result['use_gua'], '')}
- 本卦：{result['main_hexagram']}
- 互卦：{result['mutual_hexagram']}
- 動爻：{result['moving_line']}爻動，在{result['moving_side']}
- 變卦：{result['changed_hexagram']}
- 體用生剋：{result['relation']}

---

## 四、卦象提示

### 本卦：{result['main_hexagram']}

{HEXAGRAM_KNOWLEDGE.get(result['main_hexagram'], '')}

### 互卦：{result['mutual_hexagram']}

{HEXAGRAM_KNOWLEDGE.get(result['mutual_hexagram'], '')}

### 變卦：{result['changed_hexagram']}

{HEXAGRAM_KNOWLEDGE.get(result['changed_hexagram'], '')}

---

## 五、自動整體卦勢鏈

**{result['main_hexagram']} → {result['mutual_hexagram']} → {result['moving_line']}爻動在{result['moving_side']} → {result['changed_hexagram']}**

自動判斷理由：

{prediction['reason']}

預測模式：{prediction['method']}

---

## 六、自動比分預測

- 首選：{first}
- 第二選：{second}
- 第三選：{third}

---

## 七、賽後校準

- 實際比分：{actual}
- 校準原因：{review}
"""


def save_report(result, report):
    safe_name = re.sub(r"[\\/:*?\"<>|]", "_", result["match_name"]).strip() or "match"
    path = REPORT_DIR / f"{safe_name}.md"
    path.write_text(report, encoding="utf-8")
    return str(path)


def load_cases():
    return pd.read_csv(CASES_CSV) if CASES_CSV.exists() else pd.DataFrame()


def save_cases(df):
    df.to_csv(CASES_CSV, index=False, encoding="utf-8-sig")
    df.to_excel(CASES_XLSX, index=False)


def make_case_row(result, prediction, actual_score, review, report_path):
    first, second, third = [score_tuple_to_text(s) for s in prediction["scores"]]
    actual = normalize_score(actual_score)
    hit = score_result(first, second, third, actual)
    return {
        "建立時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "比賽": result["match_name"], "體方": result["body_team"], "用方": result["use_team"],
        "體方段字數": result["body_count"], "用方段字數": result["use_count"], "全段總字數": result["total_count"],
        "體卦": result["body_gua"], "體卦數": result["body_number"], "用卦": result["use_gua"], "用卦數": result["use_number"],
        "本卦": result["main_hexagram"], "互卦": result["mutual_hexagram"], "動爻": result["moving_line"], "動爻位置": result["moving_side"], "變卦": result["changed_hexagram"],
        "體用生剋": result["relation"], "預測模式": prediction["method"], "首選比分": first, "第二選比分": second, "第三選比分": third, "實際比分": actual,
        "首選命中": hit["首選命中"], "第二選命中": hit["第二選命中"], "第三選命中": hit["第三選命中"], "三選一命中": hit["三選一命中"],
        "首選勝平負": hit["首選勝平負"], "實際勝平負": hit["實際勝平負"], "首選勝平負命中": hit["首選勝平負命中"], "首選總進球誤差": hit["首選總進球誤差"],
        "自動預測理由": prediction["reason"], "校準原因": review, "報告檔案": report_path,
    }


def upsert_case(row, mode):
    df = load_cases()
    if df.empty:
        df = pd.DataFrame([row]); save_cases(df); return df, "新增"
    key_cols = ["比賽", "體方", "用方", "本卦", "互卦", "動爻", "動爻位置", "變卦"]
    for c in key_cols:
        if c not in df.columns:
            df[c] = ""
    mask = pd.Series([True] * len(df))
    for c in key_cols:
        mask = mask & (df[c].astype(str).str.strip() == str(row[c]).strip())
    idxs = list(df[mask].index)
    if mode == "強制新增" or not idxs:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True); action = "新增"
    else:
        idx = idxs[-1]
        for k, v in row.items():
            df.at[idx, k] = v
        action = "更新"
    save_cases(df)
    return df, action

# Streamlit UI

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("輸入賽前段落後，系統會自動起卦、自動折算首選 / 第二選 / 第三選比分，並輸出報告。")

with st.sidebar:
    st.header("輸入比賽資料")
    match_name = st.text_input("比賽名稱", value="剛果民主共和國 vs 烏茲別克")
    body_team = st.text_input("體方", value="剛果民主共和國")
    use_team = st.text_input("用方", value="烏茲別克")
    st.info("無特定支持：先寫隊伍為體，後寫隊伍為用。若你賽前支持某隊，支持隊為體。")
    save_mode = st.radio("案例儲存模式", ["自動更新", "強制新增"], index=0)
    actual_score = st.text_input("實際比分，賽前可空白", value="")
    review = st.text_area("校準原因，賽後再填", value="", height=120)

body_text = st.text_area("體方段落", height=150, placeholder="貼上賽前中性介紹裡描述體方的段落。")
use_text = st.text_area("用方段落", height=150, placeholder="貼上賽前中性介紹裡描述用方的段落。")
full_text = st.text_area("完整賽前中性介紹段落，用來算動爻", height=220, placeholder="貼上完整賽前中性介紹段落。")

if st.button("自動起卦並預測比分", type="primary"):
    missing = [label for label, value in [("比賽名稱", match_name), ("體方", body_team), ("用方", use_team), ("體方段落", body_text), ("用方段落", use_text), ("完整賽前中性介紹段落", full_text)] if not value.strip()]
    if missing:
        st.error("請先補齊：" + "、".join(missing))
    else:
        result = calculate_match_hexagram(match_name, body_team, use_team, body_text, use_text, full_text)
        prediction = predict_scores(result)
        report = build_markdown_report(result, prediction, actual_score, review)
        report_path = save_report(result, report)
        st.session_state["last_result"] = result
        st.session_state["last_prediction"] = prediction
        st.session_state["last_report"] = report
        st.session_state["last_report_path"] = report_path

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    prediction = st.session_state["last_prediction"]
    report = st.session_state["last_report"]
    report_path = st.session_state["last_report_path"]
    first, second, third = [score_tuple_to_text(s) for s in prediction["scores"]]

    st.subheader("自動比分預測")
    c1, c2, c3 = st.columns(3)
    c1.metric("首選", first)
    c2.metric("第二選", second)
    c3.metric("第三選", third)
    st.write("**預測理由：**")
    st.write(prediction["reason"])

    st.subheader("起卦結果")
    result_df = pd.DataFrame([
        {"項目": "體卦", "內容": f"{result['body_team']} = {result['body_gua']}，數 {result['body_number']}"},
        {"項目": "用卦", "內容": f"{result['use_team']} = {result['use_gua']}，數 {result['use_number']}"},
        {"項目": "本卦", "內容": result["main_hexagram"]},
        {"項目": "互卦", "內容": result["mutual_hexagram"]},
        {"項目": "動爻", "內容": f"{result['moving_line']}爻動，在{result['moving_side']}"},
        {"項目": "變卦", "內容": result["changed_hexagram"]},
        {"項目": "體用生剋", "內容": result["relation"]},
    ])
    st.dataframe(result_df, use_container_width=True)

    st.subheader("卦象提示")
    st.markdown(f"**本卦 {result['main_hexagram']}：** {HEXAGRAM_KNOWLEDGE.get(result['main_hexagram'], '')}")
    st.markdown(f"**互卦 {result['mutual_hexagram']}：** {HEXAGRAM_KNOWLEDGE.get(result['mutual_hexagram'], '')}")
    st.markdown(f"**變卦 {result['changed_hexagram']}：** {HEXAGRAM_KNOWLEDGE.get(result['changed_hexagram'], '')}")

    safe_download_name = re.sub(r"[\\/:*?\"<>|]", "_", result["match_name"])
    st.download_button("下載 Markdown 報告", data=report, file_name=f"{safe_download_name}.md", mime="text/markdown")
    with st.expander("查看完整 Markdown 報告"):
        st.markdown(report)

    if st.button("儲存或更新案例庫"):
        row = make_case_row(result, prediction, actual_score, review, report_path)
        df, action = upsert_case(row, save_mode)
        st.success(f"案例庫已{action}。目前共 {len(df)} 筆。")

if CASES_CSV.exists():
    st.subheader("案例庫")
    df = load_cases()
    st.dataframe(df.tail(20), use_container_width=True)
    st.download_button("下載 CSV 案例庫", data=CASES_CSV.read_bytes(), file_name="meihua_cases.csv", mime="text/csv")
    if CASES_XLSX.exists():
        st.download_button("下載 Excel 案例庫", data=CASES_XLSX.read_bytes(), file_name="meihua_cases.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
