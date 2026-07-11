import evaluation as _evaluation
from decision_control_v33 import candidate_scores, controlled_final_scores, final_scores

# 讓仍沿用 evaluation 匯入路徑的舊模組自動取得 v3.3 控制器，避免破壞賽後校準相容性。
_evaluation.candidate_scores = candidate_scores
_evaluation.controlled_final_scores = controlled_final_scores
_evaluation.final_scores = final_scores

from app_v33 import run_app

run_app()
