"""
Tool (function) definitions handed to the LLM.
Streamlined for maximum token efficiency and cost-friendliness on Groq.
Keep this list in sync with app/tools/handlers.py.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_read_only_query",
            "description": "Execute a SQL SELECT query on the MySQL database (60 domain tables: employees, incidents, permits, capas, inspections, chemicals, medical, iot, etc.). Use for custom filters, counts, joins, or details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "SQL SELECT statement to run.",
                    },
                },
                "required": ["sql_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_db_schema",
            "description": "Inspect columns of a table or list all 60 database tables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Optional table name (e.g. 'health_exams', 'audit_logs'). Omit to list all tables.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_incidents",
            "description": "List recent HSE incidents/near-misses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "e.g. OPEN, CLOSED, INVESTIGATING"},
                    "department_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_overdue_capas",
            "description": "List overdue CAPAs (past due_date, not completed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 15},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_info",
            "description": "Lookup employee details by employee_id (EMP-XXX) or name search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "query": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Name or job title search term"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_kpis",
            "description": "Get monthly safety KPI performance indicators (hours worked, TRIR, LTIFR, recordable incidents).",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "e.g. 2026-07"},
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 12},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_ai_events",
            "description": "List computer-vision detection events (PPE violations, restricted zone entry, fire).",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "LOW, MEDIUM, HIGH, CRITICAL"},
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_sensor_alerts",
            "description": "List IoT sensor readings at WARNING or CRITICAL alert level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": 10},
                },
            },
        },
    },
]