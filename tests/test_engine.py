from __future__ import annotations

from dataclasses import replace

import pytest

from qimen.constants import DEITIES, DOOR_BY_HOME, SOLAR_TERM_JU, STAR_BY_HOME, VISIBLE_STEMS
from qimen.engine import (
    cast_qimen,
    deploy_earth_plate,
    determine_dun,
    determine_fu_head,
    determine_ju,
    determine_yuan,
)


@pytest.mark.parametrize(
    ("day", "expected"),
    [("甲子", "甲子"), ("戊辰", "甲子"), ("己巳", "己巳"), ("癸酉", "己巳"), ("甲戌", "甲戌")],
)
def test_chaibu_fu_head(day, expected):
    assert determine_fu_head(day) == expected


@pytest.mark.parametrize(
    ("day", "yuan"),
    [("甲子", "上元"), ("己巳", "中元"), ("甲戌", "下元")],
)
def test_chaibu_yuan(day, yuan):
    assert determine_yuan(day)[0] == yuan


def test_all_24_terms_have_three_valid_ju():
    assert len(SOLAR_TERM_JU) == 24
    for term, ju_values in SOLAR_TERM_JU.items():
        assert determine_dun(term) in {"陽遁", "陰遁"}
        assert tuple(determine_ju(term, yuan) for yuan in ("上元", "中元", "下元")) == ju_values
        assert set(ju_values).issubset(set(range(1, 10)))


@pytest.mark.parametrize("dun", ["陽遁", "陰遁"])
@pytest.mark.parametrize("ju", range(1, 10))
def test_earth_plate_is_a_permutation(ju, dun):
    earth = deploy_earth_plate(ju, dun)
    assert set(earth) == set(range(1, 10))
    assert tuple(sorted(earth.values())) == tuple(sorted(VISIBLE_STEMS))


def test_cast_board_invariants(calendar_context):
    board = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=calendar_context,
    )
    assert set(board.palaces) == set(range(1, 10))
    assert sorted(state.earth_stem for state in board.palaces.values()) == sorted(VISIBLE_STEMS)

    doors = [state.door for state in board.palaces.values() if state.door]
    deities = [state.deity for state in board.palaces.values() if state.deity]
    stars = [star for state in board.palaces.values() for star in state.stars]
    heaven_stems = [stem for state in board.palaces.values() for stem in state.heaven_stems]
    assert sorted(doors) == sorted(DOOR_BY_HOME.values())
    assert sorted(deities) == sorted(DEITIES)
    assert sorted(stars) == sorted([*STAR_BY_HOME.values(), "天禽"])
    assert sorted(heaven_stems) == sorted(VISIBLE_STEMS)
    assert board.palaces[5].door is None
    assert board.palaces[5].deity is None
    assert board.chief_star_palace != 5
    assert board.chief_door_palace != 5
    assert sum(state.is_horse for state in board.palaces.values()) == 1
    assert sum(state.is_void for state in board.palaces.values()) in {1, 2}


def test_yang_and_yin_charts_differ(calendar_context):
    yang = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=replace(calendar_context, solar_term="冬至"),
    )
    yin = cast_qimen(
        calendar_context.local_datetime,
        calendar_context.timezone_name,
        calendar=replace(calendar_context, solar_term="夏至"),
    )
    assert yang.dun == "陽遁"
    assert yin.dun == "陰遁"
    assert {n: p.earth_stem for n, p in yang.palaces.items()} != {n: p.earth_stem for n, p in yin.palaces.items()}


def test_unsupported_method_is_not_silently_mixed(calendar_context):
    from qimen.models import MethodConfig

    with pytest.raises(NotImplementedError):
        cast_qimen(
            calendar_context.local_datetime,
            calendar_context.timezone_name,
            method=MethodConfig(plate_method="飛盤"),
            calendar=calendar_context,
        )
