"""Source-aware 《奇門遁甲元靈經》 modules.

The package intentionally keeps 演數七要 and 日奇門 independent.  Any bridge
between them is an explicit project experiment, not a claim that the transmitted
text mandates one combined method.
"""

from .riqimen import build_riqimen_base, rest_door_start_palace
from .yanshu_qiyao import build_qiyao_review

__all__ = ["build_qiyao_review", "build_riqimen_base", "rest_door_start_palace"]
