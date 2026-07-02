"""Unit tests for pure paper_service logic (no DB).

_split_by_ratio() sirf arithmetic hai — total ko MCQ/Subjective counts mein
baantne ka contract yahan lock karte hain (DB wale assembly paths test_api_routes
mein cover hote hain)."""

import pytest

from app.services.paper_service import _split_by_ratio


@pytest.mark.parametrize(
    "total,mcq_percent,expected",
    [
        (10, 30, (3, 7)),
        (10, 50, (5, 5)),
        (10, 70, (7, 3)),
        (10, 20, (2, 8)),
        (10, 80, (8, 2)),
        (7, 50, (4, 3)),  # 3.5 -> half-up 4
        (3, 50, (2, 1)),  # 1.5 -> half-up 2
        (10, 0, (0, 10)),  # all subjective
        (10, 100, (10, 0)),  # all mcq
        (0, 50, (0, 0)),  # degenerate total
    ],
)
def test_split_by_ratio(total, mcq_percent, expected):
    assert _split_by_ratio(total, mcq_percent) == expected


@pytest.mark.parametrize("total", [1, 3, 5, 7, 10, 13, 25])
@pytest.mark.parametrize("pct", [0, 20, 30, 33, 50, 67, 70, 100])
def test_split_always_sums_to_total(total, pct):
    mcq, subj = _split_by_ratio(total, pct)
    assert mcq + subj == total
    assert mcq >= 0 and subj >= 0
