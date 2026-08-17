from typing import Optional
from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    admin_user_id: str = "USR-DEV"
    session_id: Optional[str] = None   # omit to start a new session

class ToolCallTrace(BaseModel):
    tool_name: str
    query_summary: str
    rows_returned: int

class AskResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[ToolCallTrace] = []

class SensorReadingOut(BaseModel):
    reading_id: str
    sensor_id: str
    captured_at: str
    value: float
    unit: str
    alert_level: str

    class Config:
        from_attributes = True

class AIEventOut(BaseModel):
    ai_event_id: str
    detected_at: str
    event_type: str
    camera_id: str
    zone_id: str
    severity: str
    status: str

    class Config:
        from_attributes = True