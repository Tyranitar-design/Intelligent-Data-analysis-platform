# -*- coding: utf-8 -*-
"""调度频率计算 · 单元测试

锚定假设：2026-09-14 是周一（测试内显式断言）。
"""
from datetime import datetime

import pytest

from collect.schedule_runner import compute_next_run, validate_frequency


def _sched(**kw):
    base = {
        "frequency": "daily",
        "interval_hours": None,
        "time_of_day": None,
        "weekday": None,
    }
    base.update(kw)
    return base


def test_anchor_2026_09_14_is_monday():
    assert datetime(2026, 9, 14).weekday() == 0


# --------------------------------------------------------------------------- #
# 每天
# --------------------------------------------------------------------------- #


class TestDaily:
    def test_before_time_returns_today(self):
        now = datetime(2026, 9, 14, 5, 30)
        nxt = compute_next_run(_sched(frequency="daily", time_of_day="06:00"), now=now)
        assert nxt == datetime(2026, 9, 14, 6, 0)

    def test_after_time_returns_tomorrow(self):
        now = datetime(2026, 9, 14, 7, 0)
        nxt = compute_next_run(_sched(frequency="daily", time_of_day="06:00"), now=now)
        assert nxt == datetime(2026, 9, 15, 6, 0)

    def test_exact_time_returns_tomorrow(self):
        """恰好在触发点：视为已到点，顺延到明天（避免同刻重复触发）。"""
        now = datetime(2026, 9, 14, 6, 0)
        nxt = compute_next_run(_sched(frequency="daily", time_of_day="06:00"), now=now)
        assert nxt == datetime(2026, 9, 15, 6, 0)


# --------------------------------------------------------------------------- #
# 每周
# --------------------------------------------------------------------------- #


class TestWeekly:
    def test_same_day_before_time(self):
        now = datetime(2026, 9, 14, 5, 0)  # 周一 05:00
        nxt = compute_next_run(
            _sched(frequency="weekly", time_of_day="06:00", weekday=0), now=now
        )
        assert nxt == datetime(2026, 9, 14, 6, 0)

    def test_same_day_after_time_next_week(self):
        now = datetime(2026, 9, 14, 7, 0)  # 周一 07:00
        nxt = compute_next_run(
            _sched(frequency="weekly", time_of_day="06:00", weekday=0), now=now
        )
        assert nxt == datetime(2026, 9, 21, 6, 0)

    def test_upcoming_day(self):
        now = datetime(2026, 9, 14, 9, 0)  # 周一
        nxt = compute_next_run(
            _sched(frequency="weekly", time_of_day="08:00", weekday=4), now=now
        )
        assert nxt == datetime(2026, 9, 18, 8, 0)  # 周五


# --------------------------------------------------------------------------- #
# 每 N 小时
# --------------------------------------------------------------------------- #


class TestHourly:
    def test_uses_base(self):
        now = datetime(2026, 9, 14, 10, 0)
        base = datetime(2026, 9, 14, 9, 30)
        nxt = compute_next_run(
            _sched(frequency="hourly", interval_hours=2), base=base, now=now
        )
        assert nxt == datetime(2026, 9, 14, 11, 30)

    def test_catches_up_when_overdue(self):
        """积压时只顺延到下一个未来时刻，不补跑。"""
        now = datetime(2026, 9, 14, 10, 0)
        base = datetime(2026, 9, 14, 1, 0)
        nxt = compute_next_run(
            _sched(frequency="hourly", interval_hours=2), base=base, now=now
        )
        assert nxt == datetime(2026, 9, 14, 11, 0)

    def test_default_base_is_now(self):
        now = datetime(2026, 9, 14, 10, 15)
        nxt = compute_next_run(_sched(frequency="hourly", interval_hours=1), now=now)
        assert nxt == datetime(2026, 9, 14, 11, 15)


# --------------------------------------------------------------------------- #
# 校验
# --------------------------------------------------------------------------- #


class TestValidation:
    def test_hourly_requires_interval(self):
        with pytest.raises(ValueError):
            validate_frequency("hourly", interval_hours=None)

    def test_hourly_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            validate_frequency("hourly", interval_hours=25)

    def test_daily_rejects_bad_time(self):
        with pytest.raises(ValueError):
            validate_frequency("daily", time_of_day="25:00")

    def test_weekly_requires_weekday(self):
        with pytest.raises(ValueError):
            validate_frequency("weekly", time_of_day="06:00", weekday=7)

    def test_ok_combinations(self):
        validate_frequency("hourly", interval_hours=2)
        validate_frequency("daily", time_of_day="06:00")
        validate_frequency("weekly", time_of_day="06:00", weekday=0)

    def test_unknown_frequency(self):
        with pytest.raises(ValueError):
            validate_frequency("cron")
