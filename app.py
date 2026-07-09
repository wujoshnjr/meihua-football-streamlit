import os
import re
import io
import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

APP_TITLE = "梅花易數足球自動預測系統：完整卦象知識庫版 v2"
DATA_DIR = Path("data")
REPORT_DIR = Path("reports")
DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

CASES_CSV = DATA_DIR / "meihua_cases.csv"
CASES_XLSX = DATA_DIR / "meihua_cases.xlsx"

# Streamlit Cloud Secrets：
# GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH, GITHUB_CASES_PATH, GITHUB_REPORTS_DIR

def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default

GITHUB_TOKEN = get_secret("GITHUB_TOKEN")
GITHUB_REPO = get_secret("GITHUB_REPO")
GITHUB_BRANCH = get_secret("GITHUB_BRANCH", "main")
GITHUB_CASES_PATH = get_secret("GITHUB_CASES_PATH", "data/meihua_cases.csv")
GITHUB_REPORTS_DIR = get_secret("GITHUB_REPORTS_DIR", "reports")
USE_GITHUB_BACKEND = bool(GITHUB_TOKEN and GITHUB_REPO)


def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_content_url(path: str) -> str:
    clean_path = path.strip("/")
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{clean_path}"


def github_get_file(path: str):
    if not USE_GITHUB_BACKEND:
        return None, None
    response = requests.get(
        github_content_url(path),
        headers=github_headers(),
        params={"ref": GITHUB_BRANCH},
        timeout=30,
    )
    if response.status_code == 404:
        return None, None
    response.raise_for_status()
    payload = response.json()
    content = base64.b64decode(payload["content"]).decode("utf-8-sig")
    return content, payload.get("sha")


def github_put_file(path: str, text: str, message: str):
    if not USE_GITHUB_BACKEND:
        return None
    _, sha = github_get_file(path)
    body = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8-sig")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha
    response = requests.put(
        github_content_url(path),
        headers=github_headers(),
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

# -----------------------------------------------------------------------------
# 一、基礎八卦、五行、六十四卦結構
# -----------------------------------------------------------------------------

BAGUA_BY_REMAINDER = {1: "乾", 2: "兌", 3: "離", 4: "震", 5: "巽", 6: "坎", 7: "艮", 0: "坤"}
BAGUA_NUMBER = {"乾": 1, "兌": 2, "離": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
BAGUA_LINES = {"乾": "111", "兌": "110", "離": "101", "震": "100", "巽": "011", "坎": "010", "艮": "001", "坤": "000"}
LINES_TO_BAGUA = {v: k for k, v in BAGUA_LINES.items()}
ELEMENTS = {"乾": "金", "兌": "金", "離": "火", "震": "木", "巽": "木", "坎": "水", "艮": "土", "坤": "土"}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

TRIGRAM_KNOWLEDGE = {
    "乾": {
        "number": 1, "element": "金", "yin_yang": "陽", "lines": "111", "nature": "天、剛健、主導、強壓、完成", "direction": "西北", "season_hint": "秋末冬初之金氣",
        "football": "高位壓迫、硬度、領袖核心、強勢控場、高點或遠射威脅。",
        "attack": "得生扶時可上修；遇夬、大有、大壯時容易形成強行破口。",
        "defense": "若受剋或六爻變兌，硬度到極點後可能露出缺口。",
        "score_rule": "乾數一不是只能一球；它代表主導硬度。若與開局卦相連，可放大為二至三球；若被收束，常只剩壓力。",
    },
    "兌": {
        "number": 2, "element": "金", "yin_yang": "陰", "lines": "110", "nature": "澤、口、缺口、悅、交換", "direction": "西", "season_hint": "秋金之氣",
        "football": "破門口、禁區缺口、傳中、二點球、臨門一腳。",
        "attack": "兌口得家人、萃、夬時容易化成真破口。",
        "defense": "兌也可代表自身後防開口，尤其用方兌變坎時要防防線坎險。",
        "score_rule": "兌數二可作兩個口，但需看口是進攻口還是防守缺口。",
    },
    "離": {
        "number": 3, "element": "火", "yin_yang": "陰中有陽", "lines": "101", "nature": "火、明、附麗、暴露、亮點", "direction": "南", "season_hint": "夏火之氣",
        "football": "射門亮點、明星球員、反擊火點、空間被照亮。",
        "attack": "離火被木生時容易燒旺；用方離火得體方巽木生時，弱方也可能上修到兩球。",
        "defense": "離被坎水剋時亮點受壓；離變艮時火勢被止。",
        "score_rule": "離數三具高亮度，若接震、豐、夬可偏高；若接艮、節、損則回收。",
    },
    "震": {
        "number": 4, "element": "木", "yin_yang": "陽", "lines": "100", "nature": "雷、啟動、突發、衝擊、驚動", "direction": "東", "season_hint": "春木初動",
        "football": "開局衝擊、速度、反搶、突然起腳、連續攻勢。",
        "attack": "震為雷、雷火豐、震下復起時，進球數不可自動壓低。",
        "defense": "震變坤代表衝擊後轉承受；若互卦蹇阻，對方可能被阻到零球。",
        "score_rule": "震數四常是爆發潛力；是否真到四球，要看蹇、節、艮、坤是否強收。",
    },
    "巽": {
        "number": 5, "element": "木", "yin_yang": "陰", "lines": "011", "nature": "風、入、滲透、傳導、邊路", "direction": "東南", "season_hint": "春末夏初木氣",
        "football": "邊路滲透、短傳傳導、拉扯、慢慢侵入防線。",
        "attack": "巽配離、家人、鼎時代表組織鏈；配渙時可吹散對手防線。",
        "defense": "巽變艮常是先動後止，打開後收住。",
        "score_rule": "巽數五不直接等於五球，多代表傳導深度；受火引動時可餵大對方火點。",
    },
    "坎": {
        "number": 6, "element": "水", "yin_yang": "陽陷陰中", "lines": "010", "nature": "水、險、陷、反覆、門前危機", "direction": "北", "season_hint": "冬水之氣",
        "football": "門前險象、失誤、反覆受壓、反擊暗流、被困中流動。",
        "attack": "坎得金生或由困轉大過、訟轉裂口時，不可把坎水壓成零。",
        "defense": "坎被土剋時容易被軍陣、厚土吸收。",
        "score_rule": "坎數六高但多為險，不必硬轉六球；若得生扶且後段破口，可上修到二至三球。",
    },
    "艮": {
        "number": 7, "element": "土", "yin_yang": "陽止於上", "lines": "001", "nature": "山、止、守、門將、高點、界線", "direction": "東北", "season_hint": "冬末春初土氣",
        "football": "低位防守、門將、後防高點、阻擋、拖慢節奏。",
        "attack": "艮也可代表定位球高點，但通常先看收束。",
        "defense": "艮在用方或互變中強時，弱隊能把比賽拖入低比分、延長或點球。",
        "score_rule": "艮數七常是強阻力，不應直接轉高球；剝、坤、艮土重時 0-0 要提前。",
    },
    "坤": {
        "number": 8, "element": "土", "yin_yang": "陰", "lines": "000", "nature": "地、厚、承受、集體、包容、消耗", "direction": "西南", "season_hint": "長夏土氣",
        "football": "整體防線、集體厚度、拖局、承受、慢節奏消耗。",
        "attack": "強方坤可代表全隊厚勢壓上，不一定小比分。",
        "defense": "弱方坤常是被壓扁、被吸收；坤配艮、剝則強收。",
        "score_rule": "坤數八不直接等於八球。看它是強方厚勢，還是弱方承受；土重收束時總進球下修。",
    },
}

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

HEXAGRAM_SEQUENCE = {
    "乾為天": 1, "坤為地": 2, "水雷屯": 3, "山水蒙": 4, "水天需": 5, "天水訟": 6, "地水師": 7, "水地比": 8,
    "風天小畜": 9, "天澤履": 10, "地天泰": 11, "天地否": 12, "天火同人": 13, "火天大有": 14, "地山謙": 15, "雷地豫": 16,
    "澤雷隨": 17, "山風蠱": 18, "地澤臨": 19, "風地觀": 20, "火雷噬嗑": 21, "山火賁": 22, "山地剝": 23, "地雷復": 24,
    "天雷無妄": 25, "山天大畜": 26, "山雷頤": 27, "澤風大過": 28, "坎為水": 29, "離為火": 30, "澤山咸": 31, "雷風恆": 32,
    "天山遯": 33, "雷天大壯": 34, "火地晉": 35, "地火明夷": 36, "風火家人": 37, "火澤睽": 38, "水山蹇": 39, "雷水解": 40,
    "山澤損": 41, "風雷益": 42, "澤天夬": 43, "天風姤": 44, "澤地萃": 45, "地風升": 46, "澤水困": 47, "水風井": 48,
    "澤火革": 49, "火風鼎": 50, "震為雷": 51, "艮為山": 52, "風山漸": 53, "雷澤歸妹": 54, "雷火豐": 55, "火山旅": 56,
    "巽為風": 57, "兌為澤": 58, "風水渙": 59, "水澤節": 60, "風澤中孚": 61, "雷山小過": 62, "水火既濟": 63, "火水未濟": 64,
}

# 周易原始卦名/卦辭只作短引；足球象與比分規則是本系統自定義轉換。
HEXAGRAM_KNOWLEDGE = {
    "乾為天": {"core": "剛健、主導、強壓、完成。", "football": "強方掌控、壓迫、高點與硬度。", "score": "得生扶或接夬、大有、大壯時可上修；若被剋則只剩場面壓力。", "mistake": "不要因乾數一就硬判一球，乾重在硬度與主導。"},
    "坤為地": {"core": "厚、承受、集體、穩定、防守與包容。", "football": "整體陣型、拖局、承受壓力、慢節奏消耗。", "score": "強方坤可厚勢壓出多球；弱方坤多被壓縮。", "mistake": "雙坤不必然小，重點是誰是強方、誰在承受。"},
    "水雷屯": {"core": "初始艱難、阻塞中啟動。", "football": "開局不順、節奏斷裂，但有突然啟動。", "score": "多先低後動，常見 1-0、1-1、2-1。", "mistake": "不能只看屯難就判無球，要看震動是否解開坎險。"},
    "山水蒙": {"core": "蒙昧、不明、路線不清。", "football": "進攻選擇不清，推進被阻，容易失誤。", "score": "偏低或單方被鎖，0-0、1-0、0-1 要列入。", "mistake": "蒙不是弱隊必敗，也可能是強隊攻勢迷失。"},
    "水天需": {"core": "等待、蓄勢、未急於完成。", "football": "前段試探，機會需要等。", "score": "前低後升，1-0、1-1、2-1 較常見。", "mistake": "不要把需卦早段低迷誤解成全場無變化。"},
    "天水訟": {"core": "爭持、拉鋸、碰撞。", "football": "攻防對抗強、節奏破碎、判罰與爭議感重。", "score": "可低可裂，需看六爻或變卦；坎得生可上修到三球。", "mistake": "訟不是固定 1-1；若硬守裂口，比分可突然拉開。"},
    "地水師": {"core": "軍陣、紀律、集體作戰。", "football": "防守站位、壓制、反擊、集體執行力。", "score": "用方土剋體坎時，體方易被吸收；常見 0-1、0-2、1-2。", "mistake": "不要只看師為軍就判體方強，需看體用誰被軍陣壓制。"},
    "水地比": {"core": "靠近、比附、黏住。", "football": "節奏被黏住，雙方互相牽制。", "score": "可低比分，也可強方把弱方黏在半場壓制。", "mistake": "比不一定代表平手，要看坎水在誰一邊。"},
    "風天小畜": {"core": "小蓄、積累、未大放。", "football": "控球蓄勢，機會逐步堆疊。", "score": "多是先蓄後放，1-0、2-0、2-1。", "mistake": "小畜不一定只能小比分，若後段接開卦可釋放。"},
    "天澤履": {"core": "謹慎踩線、危中前行。", "football": "強方壓迫但需避反擊，禁區邊緣感重。", "score": "小勝、險勝、1-0、2-1。", "mistake": "履卦危，不宜把強方優勢判得太輕鬆。"},
    "地天泰": {"core": "通達、上下流通。", "football": "攻防轉換順，強方優勢容易落地。", "score": "體方若得勢可 2-0、2-1、3-1。", "mistake": "泰雖通，但若變卦收束仍要降總進球。"},
    "天地否": {"core": "閉塞、不通。", "football": "銜接斷、攻勢進不去。", "score": "偏 0-0、1-0、0-1。", "mistake": "不要用紙面強弱硬破否卦；需有動爻破閉塞。"},
    "天火同人": {"core": "同心、共同目標、合力。", "football": "團隊意志一致、壓迫配合。", "score": "配離火可有亮點，2-1、2-0。", "mistake": "同人重合力，不是單點爆發。"},
    "火天大有": {"core": "資源充足、掌握主導。", "football": "強方有球有勢，機會品質高。", "score": "體方得勢可上修 2-0、3-1。", "mistake": "若體方被生洩或變卦損節，不能只看大有硬大。"},
    "地山謙": {"core": "低姿態、藏鋒、收斂。", "football": "低位、謹慎、靠細節。", "score": "0-0、1-0、1-1。", "mistake": "謙不是無力，而是把節奏壓低。"},
    "雷地豫": {"core": "動員、聲勢、預備而動。", "football": "情緒與主場氣勢帶動，前段啟動。", "score": "若震得勢可 2-0、2-1。", "mistake": "豫有聲勢但也可能只是氣勢，需看是否有兌口或離火完成。"},
    "澤雷隨": {"core": "順勢、跟隨節奏。", "football": "反擊順勢、二波進攻跟上。", "score": "1-1、1-2、2-1。", "mistake": "隨代表被節奏帶走，需看誰帶誰。"},
    "山風蠱": {"core": "積弊、修補、內部問題。", "football": "防線舊傷、中場結構問題、需要調整。", "score": "常有失誤或被針對，1-2、1-1。", "mistake": "蠱不是必敗，而是問題待修。"},
    "地澤臨": {"core": "逼近、壓臨。", "football": "強方逐漸壓到禁區，距離破門近。", "score": "1-0、2-0、2-1。", "mistake": "臨是靠近，不一定已完成。"},
    "風地觀": {"core": "觀察、審視、試探。", "football": "控節奏、找弱點、前段慢。", "score": "1-0、1-1、2-0。", "mistake": "觀卦前段慢，不代表沒有後段破口。"},
    "火雷噬嗑": {"core": "咬合、破阻、強行處理。", "football": "前場壓迫咬住對手，突破障礙。", "score": "離震相應可 2-1、3-1。", "mistake": "若互變收束，咬合可能變成犯規與拉鋸。"},
    "山火賁": {"core": "文飾、亮點、表面光彩。", "football": "技術好看、局部亮點多。", "score": "常見 1-0、1-1、2-1。", "mistake": "賁有光彩但不等於效率高。"},
    "山地剝": {"core": "剝落、削弱、攻勢被層層削薄。", "football": "節奏被壓慢，進攻被消耗。", "score": "0-0、1-0、1-1 必須提前，土重時首看 0-0。", "mistake": "剝坤艮鏈不可硬給強方一球。"},
    "地雷復": {"core": "回來、復起、重新啟動。", "football": "被壓後回轉、守住後再反擊。", "score": "若體方在下震，體方可後段復起，2-0、3-0、2-1。", "mistake": "復卦看誰復，不是雙方都復。"},
    "天雷無妄": {"core": "突發、非預期、無妄之動。", "football": "意外進球、失誤、判罰、突發節奏。", "score": "1-0、2-1、1-1。", "mistake": "無妄不可過度線性推演。"},
    "山天大畜": {"core": "大蓄、積累後收束。", "football": "強力控住、蓄勢待發，也可能領先後管控。", "score": "2-0、2-1、1-0。", "mistake": "大畜不是純大，是蓄與控。"},
    "山雷頤": {"core": "口、供給、支點。", "football": "前場餵球、支點、傳中供應。", "score": "若供應鏈順，1-0、2-1；若口被封則低。", "mistake": "頤看球是否餵到，不等於自動進球。"},
    "澤風大過": {"core": "承載過重、壓力臨界。", "football": "結構壓力太大、攻勢或防線過載。", "score": "從開卦來可大，從困卦來多是壓力過重，1-1、2-1。", "mistake": "大過不能一律解大比分。"},
    "坎為水": {"core": "重險、連續危機。", "football": "門前風險反覆，失誤與反擊暗流。", "score": "得生扶可上修，受土剋則收；1-1、2-1、1-2。", "mistake": "坎不等於弱，也不等於低。"},
    "離為火": {"core": "火力、明亮、暴露。", "football": "射門亮點、明星球員、空間被照亮。", "score": "接震豐可偏高，接艮節則回收；2-1、3-1。", "mistake": "離火也會暴露防線。"},
    "澤山咸": {"core": "感應、互動、相互觸發。", "football": "一方進球後可能引發另一方回應。", "score": "1-1、2-1、1-2。", "mistake": "咸重互動，不宜只判單邊壓制。"},
    "雷風恆": {"core": "持久、反覆、長時間維持。", "football": "長時間施壓或拉鋸，後段仍有持續性。", "score": "若前有夬或離震，2-1、3-2、2-2 要入列。", "mistake": "恆不是不變，而是壓力持續。"},
    "天山遯": {"core": "退避、收縮、避鋒。", "football": "退守、讓球權、被迫後撤。", "score": "0-1、1-1、1-0。", "mistake": "遯有時是戰術退避，不是崩盤。"},
    "雷天大壯": {"core": "壯大、強烈外放。", "football": "衝擊力強、壓迫猛。", "score": "2-0、3-1、2-1。", "mistake": "過猛也可能留反擊空間。"},
    "火地晉": {"core": "推進、升進、逐步擴大。", "football": "一步步推進，後段明點出現。", "score": "若前面剝坤艮重，晉可代表拖到點球後晉級，不必然90分鐘進球。", "mistake": "晉不可硬解體方90分鐘破門。"},
    "地火明夷": {"core": "光明受傷、亮點被埋。", "football": "核心被限制，進攻亮度受壓。", "score": "偏 0-0、1-0、0-1。", "mistake": "明夷不代表沒有火，而是火被藏或受傷。"},
    "風火家人": {"core": "組織、分工、供應鏈。", "football": "前場連線、角色清楚、配合有序。", "score": "能創造機會，常見 2-1、2-0、1-1。", "mistake": "家人有組織但不等於大爆。"},
    "火澤睽": {"core": "乖離、不合、節奏不順。", "football": "有破口但進攻銜接不順。", "score": "1-0、1-1、2-1。", "mistake": "睽有火口但不順，不能只看離兌就判大。"},
    "水山蹇": {"core": "阻難、推進受阻。", "football": "空間被封、推進卡住、轉身困難。", "score": "0-0、1-0、0-1；若阻住用方，體方零封機率高。", "mistake": "蹇在互卦時常影響中段完成度。"},
    "雷水解": {"core": "解開、釋放、脫困。", "football": "卡局被打開，壓力釋放。", "score": "1-1、2-1、2-2。", "mistake": "解開後可能雙方都動，不只單邊。"},
    "山澤損": {"core": "削減、修剪、收斂。", "football": "攻勢被削、體能下降、效率降低。", "score": "0-0、1-0、1-1。", "mistake": "損會削雙方，不只削弱方。"},
    "風雷益": {"core": "增益、加強、互相推動。", "football": "雙方節奏被帶起，攻勢加強。", "score": "1-1、2-1、2-2；若接剝則回收。", "mistake": "益不一定單方大勝，可能雙方都有球。"},
    "澤天夬": {"core": "決斷、破口、破堤。", "football": "中後段關鍵破門、強行切開。", "score": "若連離震，3-2、2-1、2-2 要入列。", "mistake": "夬是破口，不是誰強誰必定零封。"},
    "天風姤": {"core": "突然遭遇、牽制。", "football": "強方遇突發反擊或不熟悉對位。", "score": "1-1、2-1、1-2。", "mistake": "姤有意外，不可只看乾在上。"},
    "澤地萃": {"core": "聚集、匯聚、混戰。", "football": "禁區混戰、角球、二點球。", "score": "1-0、2-1、1-1。", "mistake": "萃聚可讓弱方靠定位球得口。"},
    "地風升": {"core": "逐步上升、慢慢推高。", "football": "攻勢逐步推高，後段壓力增加。", "score": "1-0、2-0、2-1。", "mistake": "升要時間，不宜早段直接判大。"},
    "澤水困": {"core": "受困、空間不足。", "football": "一方被困，或禁區口被限制。", "score": "常低，但若體坎解困，可 1-1、2-1。", "mistake": "困卦若體方坎變巽，多解出一球，不宜盲目高修。"},
    "水風井": {"core": "井、固定供給、穩定源頭。", "football": "固定套路、定位球、中路供應。", "score": "1-0、1-1、2-1。", "mistake": "井重供給，不等於射門效率。"},
    "澤火革": {"core": "改革、變局、換面。", "football": "換人、戰術調整、局勢翻轉。", "score": "1-1、2-1、1-2。", "mistake": "革可能翻盤，也可能只是調整後止血。"},
    "火風鼎": {"core": "鼎立、烹煮、資源配置成形。", "football": "陣型組織、人才配置，慢慢煮開。", "score": "體巽生用離且用方離變震時，用方可上修到二；2-1、3-2、2-2。", "mistake": "不能只看體方組織破局，也要防餵大對方火點。"},
    "震為雷": {"core": "雷動、強烈啟動、連續衝擊。", "football": "速度、反搶、突發進攻。", "score": "雙震若互蹇、用震變坤，優先體方 3-0、2-0。", "mistake": "雙震不等於雙方都有球。"},
    "艮為山": {"core": "止、阻擋、守住。", "football": "防線、門將、高點、拖局。", "score": "0-0、1-0、0-1。", "mistake": "艮數七不是高球，先看阻力。"},
    "風山漸": {"core": "漸進、慢慢逼近。", "football": "逐步滲透，耐心找空間。", "score": "1-0、2-0、1-1。", "mistake": "漸不是瞬間打爆。"},
    "雷澤歸妹": {"core": "非常態結合、位置錯配。", "football": "亂戰、錯位、非常態配合。", "score": "1-1、2-1、2-2。", "mistake": "歸妹多變，不宜單純保守。"},
    "雷火豐": {"core": "豐盛、火雷俱發。", "football": "機會多，攻勢明顯，節奏亮。", "score": "2-1、3-1、3-2。", "mistake": "若變節損仍需收，不可見豐必大。"},
    "火山旅": {"core": "旅、不安定、臨時應對。", "football": "客場漂移、連線不穩、短暫亮點。", "score": "1-0、1-1、2-1。", "mistake": "旅火亮但不長久。"},
    "巽為風": {"core": "入、滲透、順勢而行。", "football": "邊路傳導、拉扯、慢慢侵入。", "score": "1-0、2-1、2-0；變艮則收。", "mistake": "巽數五不能直接轉五球。"},
    "兌為澤": {"core": "雙口、悅、缺口。", "football": "破門口、禁區口、雙方口門。", "score": "配家人可放大至 3-0、3-1；變節則收。", "mistake": "兌口要判是哪一方的口。"},
    "風水渙": {"core": "渙散、風吹水散。", "football": "防線被吹散，節奏打開。", "score": "用巽在上可吹散體坎，0-2、1-2。", "mistake": "渙不是平均打開，常是一方被吹散。"},
    "水澤節": {"core": "節制、有度、收束。", "football": "控節奏、限制總進球。", "score": "1-0、2-0、1-1；總進球下修。", "mistake": "節不是沒有進球，而是有度。"},
    "風澤中孚": {"core": "誠信、真機會、可信連線。", "football": "少數有效配合，真機會不多但可信。", "score": "1-0、1-1、2-1。", "mistake": "中孚通常不是亂戰大爆。"},
    "雷山小過": {"core": "小幅越過、細節得失。", "football": "定位球、小失誤、細節破口。", "score": "1-0、1-1、2-1。", "mistake": "小過多小差距，不宜大勝。"},
    "水火既濟": {"core": "已成、完成、攻勢落地。", "football": "機會能被完成，攻防結構成形。", "score": "1-0、2-1、2-0。", "mistake": "要看完成的是體方還是用方。"},
    "火水未濟": {"core": "未成、差一步。", "football": "有威脅但臨門差，攻勢未落地。", "score": "0-0、1-0、1-1。", "mistake": "未濟不等於無威脅，而是差最後一步。"},
}

# 若有新卦名未填，保底補齊，避免 KeyError。
for _name in set(HEXAGRAM_NAMES.values()):
    HEXAGRAM_KNOWLEDGE.setdefault(_name, {"core": "待補充核心象。", "football": "待補充足球象。", "score": "依體用、本互變、動爻再定比分。", "mistake": "不可只用卦名硬套比分。"})

# -----------------------------------------------------------------------------
# 二、計數與起卦
# -----------------------------------------------------------------------------

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
    return {"upper": upper_m, "lower": lower_m, "name": get_hexagram_name(upper_m, lower_m), "six": six}


def get_changed_hexagram(upper: str, lower: str, moving_line: int) -> dict:
    six = list(BAGUA_LINES[lower] + BAGUA_LINES[upper])
    idx = moving_line - 1
    six[idx] = "0" if six[idx] == "1" else "1"
    lower_c = LINES_TO_BAGUA["".join(six[:3])]
    upper_c = LINES_TO_BAGUA["".join(six[3:])]
    return {"upper": upper_c, "lower": lower_c, "name": get_hexagram_name(upper_c, lower_c), "six": "".join(six)}


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


def relation_interpretation(relation: str) -> str:
    if relation.startswith("用生體"):
        return "用方之氣反而生扶體方，體方較容易把場面或壓力轉成有效機會。"
    if relation.startswith("體生用"):
        return "體方會耗氣生用方，代表體方主動時也可能餵大用方反擊或亮點。"
    if relation.startswith("體剋用"):
        return "體方能壓制用方，但剋不等於必進多球，仍需看本互變是否能完成。"
    if relation.startswith("用剋體"):
        return "用方對體方有壓制，體方進攻或節奏會被限制。"
    if relation.startswith("比和"):
        return "體用同氣，節奏接近，需靠本卦、互卦、動爻與變卦判斷誰真正破局。"
    return "依五行生剋未能明確判斷，回到本互變總鏈分析。"


def moving_line_interpretation(moving_line: int, moving_side: str, changed_hexagram: str) -> str:
    stage = {1: "開局基礎位", 2: "前段執行位", 3: "上半場到中段轉折位", 4: "下半場初段轉折位", 5: "後段主導位", 6: "終局極點位"}[moving_line]
    if moving_side == "體方":
        side = "動在體方，下卦自身有變，代表體方節奏、策略或完成度會變。"
    else:
        side = "動在用方，上卦對手有變，代表用方壓力、反擊或防守結構會變。"
    return f"{moving_line}爻為{stage}；{side}變卦為「{changed_hexagram}」，需看變卦是打開還是收束。"


def calculate_match_hexagram(match_name, body_team, use_team, body_text, use_text, full_text) -> dict:
    body_count = count_meihua_units(body_text)
    use_count = count_meihua_units(use_text)
    total_count = count_meihua_units(full_text)
    body_gua = number_to_bagua(body_count)
    use_gua = number_to_bagua(use_count)
    mutual = get_mutual_hexagram(use_gua, body_gua)
    moving_line = moving_line_from_total(total_count)
    changed = get_changed_hexagram(use_gua, body_gua, moving_line)
    relation = body_use_relation(body_gua, use_gua)
    return {
        "match_name": match_name, "body_team": body_team, "use_team": use_team,
        "body_count": body_count, "use_count": use_count, "total_count": total_count,
        "body_gua": body_gua, "use_gua": use_gua,
        "body_number": BAGUA_NUMBER[body_gua], "use_number": BAGUA_NUMBER[use_gua],
        "body_element": ELEMENTS[body_gua], "use_element": ELEMENTS[use_gua],
        "main_hexagram": get_hexagram_name(use_gua, body_gua),
        "mutual_hexagram": mutual["name"],
        "moving_line": moving_line,
        "moving_side": "體方" if moving_line <= 3 else "用方",
        "changed_hexagram": changed["name"],
        "relation": relation,
        "relation_detail": relation_interpretation(relation),
        "moving_detail": moving_line_interpretation(moving_line, "體方" if moving_line <= 3 else "用方", changed["name"]),
    }

# -----------------------------------------------------------------------------
# 三、足球比分預測引擎
# -----------------------------------------------------------------------------

CALIBRATED_PATTERNS = {
    ("坎", "乾", "天水訟", "風火家人", 6, "用方", "澤水困"): {"scores": [(3, 1), (2, 1), (1, 1)], "reason": "校準：訟卦遇用乾生體坎，六爻乾變兌，容易形成用方硬守到極點後裂口；體方坎水不可壓太低。"},
    ("坎", "巽", "風水渙", "山雷頤", 5, "用方", "山水蒙"): {"scores": [(0, 2), (0, 1), (1, 2)], "reason": "校準：體坎生用巽，用方巽風在上形成風水渙，先吹散體方坎水；五爻巽變艮，打開後收住。"},
    ("坎", "兌", "澤水困", "風火家人", 3, "體方", "澤風大過"): {"scores": [(1, 1), (2, 1), (1, 0)], "reason": "校準：澤水困作本卦時，體方坎水先受困；坎變巽多是解出一球，大過若從困局來，不宜直接大幅上修。"},
    ("兌", "兌", "兌為澤", "風火家人", 4, "用方", "水澤節"): {"scores": [(3, 0), (2, 0), (3, 1)], "reason": "校準：兌為開口，家人使強方組織連線擴大破口；用方兌變坎時常是自身防線坎險，水澤節收住比分。"},
    ("坤", "坤", "坤為地", "坤為地", 5, "用方", "水地比"): {"scores": [(4, 0), (3, 0), (4, 1)], "reason": "校準：雙坤不一定低分；強方體坤可形成整體厚勢，用方坤變坎可能是防守核心位反覆坎險。"},
    ("坎", "坤", "地水師", "地雷復", 2, "體方", "坤為地"): {"scores": [(0, 2), (0, 1), (1, 2)], "reason": "校準：用方坤土剋體坎，地水師代表軍陣壓制，體方坎變坤常被用方厚土吸收。"},
    ("震", "震", "震為雷", "水山蹇", 4, "用方", "地雷復"): {"scores": [(3, 0), (2, 0), (3, 1)], "reason": "校準：雙震本卦雖有雙方啟動，但互卦水山蹇阻住用方完成度；用方震變坤轉承受，變卦地雷復保留體方下卦震雷復起。"},
    ("巽", "離", "火風鼎", "澤天夬", 6, "用方", "雷風恆"): {"scores": [(3, 2), (2, 1), (2, 2)], "reason": "校準：火風鼎、體巽生用離、互卦澤天夬、用方六爻離變震、變雷風恆時，用方離火不可只給一球，需防高張力 3-2 或 2-2。"},
    ("坤", "艮", "山地剝", "坤為地", 4, "用方", "火地晉"): {"scores": [(0, 0), (1, 0), (1, 1)], "reason": "校準：山地剝 + 坤為地 + 體用土象 + 用方艮土，攻勢被削薄，0-0 不可只列冷防，必須進前三甚至首選。"},
}

CALIBRATED_RULES_TEXT = [
    "山地剝 + 坤為地 + 體用土象 + 用方艮土：0-0 必須提前，不能因紙面強隊硬給 1-0。",
    "火風鼎 + 體巽生用離 + 澤天夬 + 用方六爻離變震：用方火點可上修到 2，需納入 3-2、2-2。",
    "雙震本卦 + 水山蹇互卦 + 用方震變坤：不要自動給用方 1 球，蹇可阻住用方完成度。",
    "天水訟 + 用乾生體坎 + 六爻乾變兌：後段硬守可能裂口，體方坎水可上修。",
]

OPEN_HEXAGRAMS = {"乾為天", "離為火", "震為雷", "兌為澤", "雷火豐", "火天大有", "澤天夬", "雷天大壯", "火雷噬嗑", "雷水解", "風水渙", "澤地萃", "風雷益", "火地晉", "地天泰"}
TIGHT_HEXAGRAMS = {"天水訟", "澤水困", "水山蹇", "山水蒙", "艮為山", "地山謙", "水澤節", "山澤損", "火澤睽", "天地否", "天山遯", "風澤中孚", "山地剝", "坤為地"}
BODY_FAVOR_HEXAGRAMS = {"火天大有", "地天泰", "火地晉", "雷天大壯", "澤天夬", "雷水解", "風雷益", "地雷復"}
USE_FAVOR_HEXAGRAMS = {"風水渙", "天水訟", "澤水困", "山水蒙", "天地否", "天風姤"}
RELEASE_CHANGED = {"澤天夬", "雷水解", "風水渙", "震為雷", "離為火", "雷火豐", "火地晉", "雷風恆"}
RESTRICT_CHANGED = {"水澤節", "山澤損", "艮為山", "山水蒙", "地山謙", "天地否", "天山遯", "坤為地", "山地剝"}
EARLY_ZERO_ZERO_HEX = {"山地剝", "坤為地", "艮為山", "水山蹇", "天地否", "地山謙"}


def clamp_goal(v: float) -> int:
    return int(round(max(0, min(6, v))))


def score_tuple_to_text(score):
    return f"{score[0]}-{score[1]}"


def prediction_key(result):
    return (result["body_gua"], result["use_gua"], result["main_hexagram"], result["mutual_hexagram"], result["moving_line"], result["moving_side"], result["changed_hexagram"])


def add_candidate(candidates, score):
    score = (max(0, min(6, int(score[0]))), max(0, min(6, int(score[1]))))
    if score not in candidates:
        candidates.append(score)


def generic_predict_scores(result: dict) -> dict:
    body_gua = result["body_gua"]
    use_gua = result["use_gua"]
    main = result["main_hexagram"]
    mutual = result["mutual_hexagram"]
    changed = result["changed_hexagram"]
    relation = result["relation"]
    moving_side = result["moving_side"]
    moving_line = result["moving_line"]

    base = {"乾": 1.2, "兌": 1.3, "離": 1.6, "震": 1.8, "巽": 1.5, "坎": 1.35, "艮": 0.75, "坤": 0.9}
    body = base[body_gua]
    use = base[use_gua] - 0.05
    reasons = []

    if main in OPEN_HEXAGRAMS:
        body += 0.4; use += 0.25; reasons.append(f"本卦「{main}」偏開，雙方進球空間上修。")
    if main in TIGHT_HEXAGRAMS:
        body -= 0.3; use -= 0.25; reasons.append(f"本卦「{main}」偏收、偏困或偏拉鋸，原始卦數先折減。")
    if main in BODY_FAVOR_HEXAGRAMS:
        body += 0.35; reasons.append(f"本卦「{main}」對體方較有利，體方上修。")
    if main in USE_FAVOR_HEXAGRAMS:
        use += 0.25; reasons.append(f"本卦「{main}」較偏用方壓力，用方上修。")

    if relation.startswith("體生用"):
        body -= 0.2; use += 0.4; reasons.append("體生用：體方力量流向用方，用方反擊或亮點上修。")
    elif relation.startswith("用生體"):
        body += 0.45; use -= 0.1; reasons.append("用生體：用方力量生出體方機會，體方得勢。")
    elif relation.startswith("體剋用"):
        body += 0.25; use -= 0.15; reasons.append("體剋用：體方能壓制用方，但不直接等於多球。")
    elif relation.startswith("用剋體"):
        body -= 0.35; use += 0.25; reasons.append("用剋體：用方壓制體方，體方完成度下修。")
    elif relation.startswith("比和"):
        body += 0.05; use += 0.05; reasons.append("體用比和：雙方節奏接近，回到本互變判斷誰破局。")

    if mutual in {"風火家人", "山雷頤", "水火既濟", "火雷噬嗑", "雷水解", "澤天夬"}:
        body += 0.2; use += 0.15; reasons.append(f"互卦「{mutual}」代表中段供應鏈、咬合或破口，機會略增。")
    if mutual in {"山澤損", "山地剝", "水澤節", "水山蹇", "坤為地", "艮為山"}:
        body -= 0.25; use -= 0.2; reasons.append(f"互卦「{mutual}」削弱或限制中段完成度。")

    if moving_side == "體方":
        if changed in RELEASE_CHANGED:
            body += 0.45; reasons.append(f"動爻在體方且變卦「{changed}」偏打開，體方後段上修。")
        elif changed in RESTRICT_CHANGED:
            body -= 0.3; reasons.append(f"動爻在體方且變卦「{changed}」偏收束，體方後段折減。")
    else:
        if changed in RELEASE_CHANGED:
            use += 0.45; reasons.append(f"動爻在用方且變卦「{changed}」偏打開，用方後段上修。")
        elif changed in RESTRICT_CHANGED:
            use -= 0.25; reasons.append(f"動爻在用方且變卦「{changed}」偏收束，用方後段折減。")

    if moving_line == 6:
        reasons.append("六爻動代表後段極點，要注意硬守到極點後裂口或領先方收住。")
        if use_gua == "乾" and changed.startswith("澤"):
            body += 0.35; reasons.append("用方乾到六爻變兌，常見硬度到極點後露口，體方可上修。")
        if use_gua == "離" and changed in {"雷風恆", "震為雷", "雷火豐"}:
            use += 0.35; reasons.append("用方離火在六爻變震，火到極點化雷，弱方進球不可只給一球。")

    # 土重收束：強制把 0-0 提前進候選。
    earth_heavy = (
        main in {"山地剝", "坤為地", "艮為山"}
        or (ELEMENTS[body_gua] == "土" and ELEMENTS[use_gua] == "土" and mutual in {"坤為地", "艮為山", "山地剝"})
    )
    if earth_heavy:
        body -= 0.35; use -= 0.35; reasons.append("土重收束：艮坤剝鏈強時，0-0 或小比分要提前，不可只靠紙面強弱硬破。")

    if changed in {"水澤節", "山澤損", "艮為山", "坤為地"} and body + use > 3.0:
        body *= 0.86; use *= 0.86; reasons.append(f"變卦「{changed}」有節制、削減或厚土收束，總進球略收。")

    candidates = []
    first = (clamp_goal(body), clamp_goal(use))
    if earth_heavy:
        add_candidate(candidates, (0, 0))
    add_candidate(candidates, first)

    if first[0] > first[1]:
        add_candidate(candidates, (max(0, first[0] - 1), first[1]))
        add_candidate(candidates, (first[0], min(3, first[1] + 1)))
    elif first[1] > first[0]:
        add_candidate(candidates, (first[0], max(0, first[1] - 1)))
        add_candidate(candidates, (min(3, first[0] + 1), first[1]))
    else:
        add_candidate(candidates, (min(6, first[0] + 1), first[1]))
        add_candidate(candidates, (first[0], min(6, first[1] + 1)))

    while len(candidates) < 3:
        a, b = candidates[-1]
        add_candidate(candidates, (min(6, a + 1), b) if a <= b else (a, min(6, b + 1)))

    return {"scores": candidates[:3], "reason": "；".join(reasons) or "依一般卦勢權重折算。", "method": "general_rules_v2"}


def predict_scores(result: dict) -> dict:
    key = prediction_key(result)
    if key in CALIBRATED_PATTERNS:
        p = CALIBRATED_PATTERNS[key]
        return {"scores": p["scores"], "reason": p["reason"], "method": "calibrated_pattern_v2"}
    return generic_predict_scores(result)

# -----------------------------------------------------------------------------
# 四、輸出、儲存、統計
# -----------------------------------------------------------------------------

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


def hexagram_detail_md(name: str, title: str = "卦") -> str:
    info = HEXAGRAM_KNOWLEDGE.get(name, {})
    seq = HEXAGRAM_SEQUENCE.get(name, "")
    return f"""### {title}：{name}{f'（第{seq}卦）' if seq else ''}

- 核心象：{info.get('core', '')}
- 足球象：{info.get('football', '')}
- 比分規則：{info.get('score', '')}
- 容易誤判：{info.get('mistake', '')}
"""


def trigram_detail_md(gua: str, team_label: str = "") -> str:
    info = TRIGRAM_KNOWLEDGE[gua]
    return f"""### {team_label}{gua}卦

- 卦數：{info['number']}
- 五行：{info['element']}
- 陰陽：{info['yin_yang']}
- 三爻：{info['lines']}
- 自然象：{info['nature']}
- 足球象：{info['football']}
- 進攻象：{info['attack']}
- 防守象：{info['defense']}
- 比分折算：{info['score_rule']}
"""


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

| 取數項目 | 字數 | 對應卦 | 卦數 | 五行 |
|---|---:|---|---:|---|
| {result['body_team']}段 | {result['body_count']} | {result['body_gua']} | {result['body_number']} | {result['body_element']} |
| {result['use_team']}段 | {result['use_count']} | {result['use_gua']} | {result['use_number']} | {result['use_element']} |
| 全段總數 | {result['total_count']} | {result['moving_line']}爻動 | - | - |

---

## 三、卦象結果

- 體卦：{result['body_team']} = {result['body_gua']}
- 用卦：{result['use_team']} = {result['use_gua']}
- 本卦：{result['main_hexagram']}
- 互卦：{result['mutual_hexagram']}
- 動爻：{result['moving_line']}爻動，在{result['moving_side']}
- 變卦：{result['changed_hexagram']}
- 體用生剋：{result['relation']}

---

## 四、八卦細節

{trigram_detail_md(result['body_gua'], result['body_team'] + '：')}

{trigram_detail_md(result['use_gua'], result['use_team'] + '：')}

---

## 五、本卦、互卦、變卦細節

{hexagram_detail_md(result['main_hexagram'], '本卦')}

{hexagram_detail_md(result['mutual_hexagram'], '互卦')}

{hexagram_detail_md(result['changed_hexagram'], '變卦')}

---

## 六、體用與動爻分析

- 體用生剋：{result['relation']}
- 生剋解讀：{result['relation_detail']}
- 動爻解讀：{result['moving_detail']}

---

## 七、自動整體卦勢鏈

**{result['main_hexagram']} → {result['mutual_hexagram']} → {result['moving_line']}爻動在{result['moving_side']} → {result['changed_hexagram']}**

自動判斷理由：

{prediction['reason']}

預測模式：{prediction['method']}

---

## 八、自動比分預測

- 首選：{first}
- 第二選：{second}
- 第三選：{third}

---

## 九、校準規則提醒

""" + "\n".join([f"- {x}" for x in CALIBRATED_RULES_TEXT]) + f"""

---

## 十、賽後校準

- 實際比分：{actual}
- 校準原因：{review}
"""


def save_report(result, report):
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", result["match_name"]).strip() or "match"
    local_path = REPORT_DIR / f"{safe_name}.md"
    local_path.write_text(report, encoding="utf-8")

    if USE_GITHUB_BACKEND:
        remote_path = f"{GITHUB_REPORTS_DIR.strip('/')}/{safe_name}.md"
        github_put_file(remote_path, report, f"Update report: {result['match_name']}")
        return remote_path

    return str(local_path)


def load_cases():
    if USE_GITHUB_BACKEND:
        text, _ = github_get_file(GITHUB_CASES_PATH)
        if not text:
            return pd.DataFrame()
        return pd.read_csv(io.StringIO(text), dtype="object", keep_default_na=False)
    if CASES_CSV.exists():
        return pd.read_csv(CASES_CSV, dtype="object", keep_default_na=False)
    return pd.DataFrame()


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="cases")
    return output.getvalue()


def save_cases(df):
    csv_text = df.to_csv(index=False, encoding="utf-8-sig")
    CASES_CSV.parent.mkdir(exist_ok=True)
    CASES_CSV.write_text(csv_text, encoding="utf-8-sig")
    CASES_XLSX.write_bytes(dataframe_to_excel_bytes(df))
    if USE_GITHUB_BACKEND:
        github_put_file(GITHUB_CASES_PATH, csv_text, "Update meihua casebook")


def make_case_row(result, prediction, actual_score, review, report_path):
    first, second, third = [score_tuple_to_text(s) for s in prediction["scores"]]
    actual = normalize_score(actual_score)
    hit = score_result(first, second, third, actual)
    return {
        "建立時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "比賽": result["match_name"], "體方": result["body_team"], "用方": result["use_team"],
        "體方段字數": result["body_count"], "用方段字數": result["use_count"], "全段總字數": result["total_count"],
        "體卦": result["body_gua"], "體卦數": result["body_number"], "體卦五行": result["body_element"], "用卦": result["use_gua"], "用卦數": result["use_number"], "用卦五行": result["use_element"],
        "本卦": result["main_hexagram"], "互卦": result["mutual_hexagram"], "動爻": result["moving_line"], "動爻位置": result["moving_side"], "變卦": result["changed_hexagram"],
        "體用生剋": result["relation"], "預測模式": prediction["method"], "首選比分": first, "第二選比分": second, "第三選比分": third, "實際比分": actual,
        "首選命中": hit["首選命中"], "第二選命中": hit["第二選命中"], "第三選命中": hit["第三選命中"], "三選一命中": hit["三選一命中"],
        "首選勝平負": hit["首選勝平負"], "實際勝平負": hit["實際勝平負"], "首選勝平負命中": hit["首選勝平負命中"], "首選總進球誤差": hit["首選總進球誤差"],
        "自動預測理由": prediction["reason"], "校準原因": review, "報告檔案": report_path,
    }


def upsert_case(row, mode):
    df = load_cases()
    if not df.empty:
        df = df.astype("object")
    safe_row = {k: ("" if v is None else v) for k, v in row.items()}

    if df.empty:
        df = pd.DataFrame([safe_row]).astype("object")
        save_cases(df)
        return df, "新增"

    key_cols = ["比賽", "體方", "用方", "本卦", "互卦", "動爻", "動爻位置", "變卦"]
    for c in key_cols:
        if c not in df.columns:
            df[c] = ""
    for c in safe_row.keys():
        if c not in df.columns:
            df[c] = ""

    mask = pd.Series([True] * len(df), index=df.index)
    for c in key_cols:
        mask = mask & (df[c].astype(str).str.strip() == str(safe_row.get(c, "")).strip())

    idxs = list(df[mask].index)
    if mode == "強制新增" or not idxs:
        df = pd.concat([df, pd.DataFrame([safe_row])], ignore_index=True).astype("object")
        action = "新增"
    else:
        idx = idxs[-1]
        for k, v in safe_row.items():
            df.loc[idx, k] = v
        action = "更新"

    save_cases(df)
    return df, action

# -----------------------------------------------------------------------------
# 五、Streamlit UI
# -----------------------------------------------------------------------------

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("輸入賽前段落後，系統會自動起卦、自動折算首選 / 第二選 / 第三選比分，並輸出更完整卦象報告。僅供研究與紀錄，不作投注建議。")

with st.sidebar:
    st.header("輸入比賽資料")
    match_name = st.text_input("比賽名稱", value="阿根廷 vs 埃及")
    body_team = st.text_input("體方", value="阿根廷")
    use_team = st.text_input("用方", value="埃及")
    st.info("無特定支持：先寫隊伍為體，後寫隊伍為用。若你賽前支持某隊，支持隊為體。判斷範圍固定為 90 分鐘。")
    if USE_GITHUB_BACKEND:
        st.success(f"GitHub 後台已啟用：{GITHUB_REPO} / {GITHUB_BRANCH}")
    else:
        st.warning("目前使用本機暫存。部署後請設定 Streamlit Secrets 才會寫回 GitHub。")
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
        {"項目": "體卦", "內容": f"{result['body_team']} = {result['body_gua']}，數 {result['body_number']}，五行 {result['body_element']}"},
        {"項目": "用卦", "內容": f"{result['use_team']} = {result['use_gua']}，數 {result['use_number']}，五行 {result['use_element']}"},
        {"項目": "本卦", "內容": result["main_hexagram"]},
        {"項目": "互卦", "內容": result["mutual_hexagram"]},
        {"項目": "動爻", "內容": f"{result['moving_line']}爻動，在{result['moving_side']}"},
        {"項目": "變卦", "內容": result["changed_hexagram"]},
        {"項目": "體用生剋", "內容": result["relation"]},
    ])
    st.dataframe(result_df, use_container_width=True)

    st.subheader("卦象詳細解讀")
    tabs = st.tabs(["八卦", "本互變", "體用與動爻", "校準提醒"])
    with tabs[0]:
        st.markdown(trigram_detail_md(result["body_gua"], result["body_team"] + "："))
        st.markdown(trigram_detail_md(result["use_gua"], result["use_team"] + "："))
    with tabs[1]:
        st.markdown(hexagram_detail_md(result["main_hexagram"], "本卦"))
        st.markdown(hexagram_detail_md(result["mutual_hexagram"], "互卦"))
        st.markdown(hexagram_detail_md(result["changed_hexagram"], "變卦"))
    with tabs[2]:
        st.markdown(f"**體用生剋：** {result['relation']}")
        st.write(result["relation_detail"])
        st.markdown(f"**動爻：** {result['moving_line']}爻動，在{result['moving_side']}")
        st.write(result["moving_detail"])
    with tabs[3]:
        for rule in CALIBRATED_RULES_TEXT:
            st.write("- " + rule)

    safe_download_name = re.sub(r"[\\/:*?\"<>|]", "_", result["match_name"])
    st.download_button("下載 Markdown 詳細報告", data=report, file_name=f"{safe_download_name}.md", mime="text/markdown")
    with st.expander("查看完整 Markdown 報告"):
        st.markdown(report)

    if st.button("儲存或更新案例庫"):
        row = make_case_row(result, prediction, actual_score, review, report_path)
        df, action = upsert_case(row, save_mode)
        st.success(f"案例庫已{action}。目前共 {len(df)} 筆。")

st.divider()
st.subheader("卦象知識庫查詢")
col_a, col_b = st.columns(2)
with col_a:
    selected_trigram = st.selectbox("查八卦", list(TRIGRAM_KNOWLEDGE.keys()))
    st.markdown(trigram_detail_md(selected_trigram))
with col_b:
    selected_hex = st.selectbox("查六十四卦", sorted(HEXAGRAM_KNOWLEDGE.keys(), key=lambda x: HEXAGRAM_SEQUENCE.get(x, 999)))
    st.markdown(hexagram_detail_md(selected_hex, "查詢卦"))

casebook_df = load_cases()
if not casebook_df.empty:
    st.subheader("案例庫")
    st.dataframe(casebook_df.tail(20), use_container_width=True)
    st.download_button(
        "下載 CSV 案例庫",
        data=casebook_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="meihua_cases.csv",
        mime="text/csv",
    )
    st.download_button(
        "下載 Excel 案例庫",
        data=dataframe_to_excel_bytes(casebook_df),
        file_name="meihua_cases.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
