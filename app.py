from __future__ import annotations

import importlib


# Streamlit 會在同一個 Python 行程中重跑腳本；當資料類別欄位在部署中新增時，
# 舊的已匯入模組可能仍留在記憶體，導致 MatchInput 拒絕新的關鍵字參數。
# 這裡依相依順序重新載入本地模組，確保 v3.3 的 dataclass、規則與 AI 控制器一致。
def _reload_local(name: str):
    module = importlib.import_module(name)
    return importlib.reload(module)


_models = _reload_local("models")
_evaluation = _reload_local("evaluation")
_decision = _reload_local("decision_control_v33")

# 舊模組仍從 evaluation 匯入控制函式，因此先掛上 v3.3 實作再重載下游模組。
_evaluation.candidate_scores = _decision.candidate_scores
_evaluation.controlled_final_scores = _decision.controlled_final_scores
_evaluation.final_scores = _decision.final_scores

for _module_name in [
    "meihua_engine",
    "case_memory",
    "score_engine",
    "ai_reasoner_v32",
    "ai_reasoner_v33",
    "storage",
    "storage_v32",
    "storage_v33",
    "report_builder",
    "report_builder_v33",
    "calibration_center",
    "metrics_dashboard",
]:
    _reload_local(_module_name)

# 下游模組重載完成後再補一次，避免任何舊匯入覆蓋控制器。
_evaluation.candidate_scores = _decision.candidate_scores
_evaluation.controlled_final_scores = _decision.controlled_final_scores
_evaluation.final_scores = _decision.final_scores

_app = _reload_local("app_v33")
_app.run_app()
