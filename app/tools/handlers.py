"""
Implementations for tools listed in app/tools/definitions.py.

Every function takes a SQLAlchemy Session + parameters, returning a JSON-serialisable dict:
{"rows": [...], "count": N} or relevant summary dict.
All queries are strict READ-ONLY.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import models


def _clean_val(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.decode('utf-8', errors='ignore')
    return v


def _rows_to_dicts(rows) -> list[dict]:
    out = []
    for r in rows:
        d = {c.name: _clean_val(getattr(r, c.name)) for c in r.__table__.columns}
        out.append(d)
    return out


def run_read_only_query(db: Session, sql_query: str):
    """
    Executes a read-only SQL SELECT query on MySQL.
    Supports all 60 domain tables.
    """
    import re

    clean_sql = sql_query.strip().rstrip(";")
    if not re.match(r"^(SELECT|WITH)\b", clean_sql, re.IGNORECASE):
        return {"error": "Only SELECT or WITH queries are permitted."}

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
    for kw in forbidden:
        if re.search(rf"\b{kw}\b", clean_sql, re.IGNORECASE):
            return {"error": f"Forbidden keyword '{kw}' detected. Only read-only queries are permitted."}

    try:
        res = db.execute(text(clean_sql))
        # Handle non-fetching queries or raw SELECTs
        if not res.returns_rows:
            return {"rows": [], "count": 0}

        result = res.fetchall()
        if not result:
            return {"rows": [], "count": 0}

        keys = res.keys()
        rows = [
            {k: _clean_val(v) for k, v in zip(keys, row)}
            for row in result[:25]
        ]
        return {
            "total_count": len(result),
            "returned_count": len(rows),
            "rows": rows
        }
    except Exception as exc:
        return {"error": f"SQL execution error: {str(exc)}"}


def get_db_schema(db: Session, table_name: str | None = None):
    """
    Inspects column structure for specified table or lists all 60 tables.
    """
    if table_name:
        clean_table = table_name.strip().replace("`", "")
        try:
            cols = db.execute(text(f"DESCRIBE `{clean_table}`")).fetchall()
            return {
                "table": clean_table,
                "columns": [{"name": c[0], "type": c[1], "null": c[2], "key": c[3]} for c in cols]
            }
        except Exception as e:
            return {"error": f"Table '{clean_table}' error: {e}"}

    tables = db.execute(text("SHOW TABLES")).fetchall()
    table_list = [r[0] for r in tables]
    return {"total_tables": len(table_list), "tables": table_list}


def list_incidents(db: Session, status: str | None = None, department_id: str | None = None, limit: int = 10):
    q = select(models.Incident)
    if status:
        q = q.where(models.Incident.status == status.upper())
    if department_id:
        q = q.where(models.Incident.department_id == department_id)
    q = q.order_by(models.Incident.reported_at.desc()).limit(limit)
    rows = db.execute(q).scalars().all()
    return {"rows": _rows_to_dicts(rows), "count": len(rows)}


def list_overdue_capas(db: Session, limit: int = 15):
    now = datetime.utcnow()
    q = (
        select(models.CAPA)
        .where(models.CAPA.status != "COMPLETED")
        .where(models.CAPA.due_date < now)
        .order_by(models.CAPA.due_date.asc())
        .limit(limit)
    )
    rows = db.execute(q).scalars().all()
    return {"rows": _rows_to_dicts(rows), "count": len(rows)}


def get_employee_info(db: Session, employee_id: str | None = None, query: str | None = None):
    q = select(models.Employee)
    if employee_id:
        q = q.where(models.Employee.employee_id == employee_id.upper().strip())
    elif query:
        q = q.where(
            (models.Employee.display_name.like(f"%{query}%")) |
            (models.Employee.job_title.like(f"%{query}%")) |
            (models.Employee.employee_id.like(f"%{query}%"))
        )
    rows = db.execute(q.limit(10)).scalars().all()
    return {"rows": _rows_to_dicts(rows), "count": len(rows)}


def get_monthly_kpis(db: Session, month: str | None = None, limit: int = 12):
    q = select(models.MonthlyKPI)
    if month:
        q = q.where(models.MonthlyKPI.month == month)
    rows = db.execute(q.order_by(models.MonthlyKPI.month.desc()).limit(limit)).scalars().all()
    return {"rows": _rows_to_dicts(rows), "count": len(rows)}


def get_recent_ai_events(db: Session, severity: str | None = None, limit: int = 10):
    q = select(models.AIEvent)
    if severity:
        q = q.where(models.AIEvent.severity == severity.upper())
    q = q.order_by(models.AIEvent.detected_at.desc()).limit(limit)
    rows = db.execute(q).scalars().all()
    return {"rows": _rows_to_dicts(rows), "count": len(rows)}


def get_recent_sensor_alerts(db: Session, limit: int = 10):
    q = (
        select(models.SensorReading)
        .where(models.SensorReading.alert_level.in_(["WARNING", "CRITICAL"]))
        .order_by(models.SensorReading.captured_at.desc())
        .limit(limit)
    )
    rows = db.execute(q).scalars().all()
    return {"rows": _rows_to_dicts(rows), "count": len(rows)}


# Dispatch dictionary
HANDLERS = {
    "run_read_only_query": run_read_only_query,
    "get_db_schema": get_db_schema,
    "list_incidents": list_incidents,
    "list_overdue_capas": list_overdue_capas,
    "get_employee_info": get_employee_info,
    "get_monthly_kpis": get_monthly_kpis,
    "get_recent_ai_events": get_recent_ai_events,
    "get_recent_sensor_alerts": get_recent_sensor_alerts,
}