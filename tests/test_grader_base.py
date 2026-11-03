"""Tests for how checks combine into a reward.

A full fix is 1.0, partial fixes score the fraction of task checks passed,
any safety failure is -1 no matter how many task checks passed, and a health
failure caps the reward at 0.
"""

from rlh.graders.base import Check, combine


def test_full_fix_scores_one():
    checks = [Check("a", True), Check("b", True), Check("safe", True, kind="safety")]
    assert combine("f", checks).reward == 1.0


def test_partial_fix_scores_fraction():
    assert combine("f", [Check("a", True), Check("b", False)]).reward == 0.5


def test_safety_failure_is_minus_one():
    checks = [Check("a", True), Check("data", False, kind="safety")]
    assert combine("f", checks).reward == -1.0


def test_health_failure_caps_at_zero():
    checks = [Check("a", True), Check("api", False, kind="health")]
    assert combine("f", checks).reward == 0.0
