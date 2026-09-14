"""
采集调度规则模型
================

一条规则 = 一个计划 + 一个频率。调度循环到点自动创建并执行采集任务。

频率用结构化字段表达（而非裸 cron 字符串）：

- ``hourly``  每 N 小时（``interval_hours`` 1-24）
- ``daily``   每天 HH:MM（``time_of_day``）
- ``weekly``  每周某天 HH:MM（``weekday`` 0=周一 … 6=周日）

这样界面可以做可视化选择器、不要求用户手写表达式，计算 next_run
也不需要引入 croniter 这类新依赖。

时间口径：全部使用**本机时间**（naive datetime）。平台是单机工具，
"每天早上 6 点"按机器所在时区理解最符合直觉。
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from api.core.database import Base

WEEKDAY_TEXT = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def describe_frequency(schedule) -> str:
    """把结构化频率转成一行人类可读描述（供界面直接显示）。"""
    frequency = getattr(schedule, "frequency", None)
    if frequency == "hourly":
        return f"每 {int(schedule.interval_hours or 1)} 小时"
    if frequency == "daily":
        return f"每天 {schedule.time_of_day or '06:00'}"
    if frequency == "weekly":
        weekday = int(schedule.weekday if schedule.weekday is not None else 0)
        weekday = max(0, min(6, weekday))
        return f"每{WEEKDAY_TEXT[weekday]} {schedule.time_of_day or '06:00'}"
    return str(frequency or "未设置")


class CollectSchedule(Base):
    """采集调度规则表"""

    __tablename__ = "collect_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    plan_id = Column(
        Integer, ForeignKey("collect_plans.id"), nullable=False, index=True
    )

    # hourly | daily | weekly
    frequency = Column(String(20), nullable=False)
    # hourly：间隔小时数（1-24）
    interval_hours = Column(Integer, nullable=True)
    # daily / weekly：执行时刻 "HH:MM"
    time_of_day = Column(String(5), nullable=True)
    # weekly：0=周一 … 6=周日
    weekday = Column(Integer, nullable=True)

    enabled = Column(Boolean, default=True, nullable=False, index=True)

    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
    run_count = Column(Integer, default=0, nullable=False)
    fail_count = Column(Integer, default=0, nullable=False)
    last_job_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<CollectSchedule(id={self.id}, name={self.name!r}, "
            f"enabled={self.enabled}, next={self.next_run_at})>"
        )

    def to_dict(self, *, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        next_run = self.next_run_at
        return {
            "schedule_id": self.id,
            "name": self.name,
            "plan_id": self.plan_id,
            "frequency": self.frequency,
            "interval_hours": self.interval_hours,
            "time_of_day": self.time_of_day,
            "weekday": self.weekday,
            "frequency_text": describe_frequency(self),
            "enabled": bool(self.enabled),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": next_run.isoformat() if next_run else None,
            "next_run_in_seconds": (
                max(0, int((next_run - now).total_seconds()))
                if next_run and next_run > now
                else 0
            ),
            "run_count": self.run_count or 0,
            "fail_count": self.fail_count or 0,
            "last_job_id": self.last_job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
