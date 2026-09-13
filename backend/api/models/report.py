"""分析报告存储"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from datetime import datetime
from api.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    report_type = Column(String(50), default="eda")  # eda, ml, full
    format = Column(String(20), default="markdown")  # markdown, html
    content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
