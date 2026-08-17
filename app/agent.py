import json
import uuid
from sqlalchemy.orm import Session
from app.llm_client import chat_completion
from app.schemas import ToolCallTrace, AskResponse
from app.tools.definitions import TOOLS
from app.tools.handlers import HANDLERS

SYSTEM_PROMPT = """You are ESCA HSE Assistant — an expert Health, Safety & Environment AI assistant for the ESCA HSE management system with live read-only access to MySQL.

DATABASE COVERAGE (60 domain tables loaded from Excel dataset):
- Master Data: departments, zones, employees, roles, users, user_roles, rbac_matrix, service_catalog, environments.
- Core Operations: incidents, inspections, findings, capas, risk_register, jsa, jsa_steps, permits, permit_approvals, permit_checklist, permit_gas_tests, simops, incident_rca, inspection_responses, monthly_kpis, report_definitions, report_runs.
- Assets, Training & Health: training_courses, certificates, ppe_inventory, ppe_matrix, fire_equipment, fire_inspections, chemicals, sds_records, medical_protocols, employee_exposures, health_exams, clinic_visits, training_requirements, ppe_transactions, fixed_safety_assets.
- AI, IoT & Integrations: iot_sensors, sensor_readings, cameras, ai_models, ai_events, wearable_devices, wearable_events, integrations, api_logs, integration_outbox, qa_sessions, qa_messages, qa_tool_calls, notifications, audit_logs, security_events, automation_rules, automation_runs, automation_actions.

IMPORTANT SCHEMA RULES:
- Prefer the purpose-built tool for standard tasks: use `list_incidents` for incident listings, `list_overdue_capas` for CAPA status checks, `get_employee_info` for employee lookups, and `get_recent_ai_events` / `get_recent_sensor_alerts` for AI and alert summaries.
- For custom SQL with `run_read_only_query`, use the exact column names from the ESCA HSE schema. Common examples: `incident_id` not `id`, `capa_id` not `id`, `employee_id` not `id`, `department_id` not `department` or `id`.
- Do not assume generic `id` columns exist across all tables; each table has its own primary key name.
- When a user asks for incidents by department, use the `department_id` filter on `list_incidents` unless special aggregation is required.

RESPONSE GUIDELINES:
1. Provide helpful, accurate, intelligent, and natural language answers to any inquiry about the data.
2. Format answers beautifully in Markdown using clear headings, bold text, bullet points, or structured tables when helpful.
3. Automatically match the user's language (respond in fluent English or Arabic as requested).
4. Use `run_read_only_query` to run SQL SELECT queries for counts, aggregations, filters, or custom questions across any of the 60 tables. Use `get_db_schema` to inspect table structure if needed.
5. NEVER expose raw SQL queries, technical error tracebacks, or tool names in your final response to the user — synthesize the facts into clear natural prose.
6. If a query returns no rows or zero results, state clearly and politely that no matching records were found in the database."""

SESSION_HISTORIES: dict[str, list[dict]] = {}

def run_agent_loop(question: str, db: Session, session_id: str | None = None) -> AskResponse:
    if not session_id or session_id not in SESSION_HISTORIES:
        session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        SESSION_HISTORIES[session_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    history = SESSION_HISTORIES[session_id]

    # Keep conversation history bounded to last 6 turns (12 messages) + system prompt
    if len(history) > 13:
        history = [history[0]] + history[-12:]
        SESSION_HISTORIES[session_id] = history

    messages = list(history)
    messages.append({"role": "user", "content": question})

    traces: list[ToolCallTrace] = []
    max_loops = 5
    seen_tool_calls: set[str] = set()

    for i in range(max_loops):
        response = chat_completion(messages=messages, tools=TOOLS)
        message = response.choices[0].message

        # If model returned textual answer without tool calls, we're done!
        if not message.tool_calls:
            final_answer = message.content or "No content returned."
            SESSION_HISTORIES[session_id].append({"role": "user", "content": question})
            SESSION_HISTORIES[session_id].append({"role": "assistant", "content": final_answer})
            return AskResponse(
                session_id=session_id,
                answer=final_answer,
                tool_calls=traces
            )

        # Append assistant tool call request to loop context
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in message.tool_calls
            ]
        })

        # Process each tool call
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            raw_args = None
            if tool_call.function.arguments:
                try:
                    raw_args = json.loads(tool_call.function.arguments)
                except Exception:
                    raw_args = {}
            if not isinstance(raw_args, dict):
                raw_args = {}

            args = {k: v for k, v in raw_args.items() if v is not None}

            dedup_key = f"{func_name}:{json.dumps(args, sort_keys=True)}"
            if dedup_key in seen_tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"note": "Already executed — refer to previous tool result."})
                })
                continue
            seen_tool_calls.add(dedup_key)

            if func_name in HANDLERS:
                handler = HANDLERS[func_name]
                try:
                    result_data = handler(db=db, **args)
                except Exception as exc:
                    result_data = {"rows": [], "count": 0, "error": str(exc)}
                    traces.append(ToolCallTrace(
                        tool_name=func_name,
                        query_summary=f"Failed {func_name}: {exc}",
                        rows_returned=0
                    ))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result_data, default=str)
                    })
                    continue

                if isinstance(result_data, dict):
                    rows_count = result_data.get("total_count", result_data.get("count", len(result_data.get("rows", []))))
                elif isinstance(result_data, list):
                    rows_count = len(result_data)
                else:
                    rows_count = 1

                traces.append(ToolCallTrace(
                    tool_name=func_name,
                    query_summary=f"Executed {func_name} with args: {args}",
                    rows_returned=rows_count
                ))

                # Structure payload safely without breaking JSON string validity
                if isinstance(result_data, dict) and "rows" in result_data and isinstance(result_data["rows"], list):
                    trimmed = dict(result_data)
                    trimmed["rows"] = result_data["rows"][:15]  # Cap rows safely before dumping to JSON
                    payload = json.dumps(trimmed, default=str)
                else:
                    payload = json.dumps(result_data, default=str)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": payload
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"error": f"Tool '{func_name}' not implemented"})
                })

    # Fallback if max_loops reached
    final_answer = "I searched the database but reached the maximum inquiry steps. Please ask a more specific question."
    SESSION_HISTORIES[session_id].append({"role": "user", "content": question})
    SESSION_HISTORIES[session_id].append({"role": "assistant", "content": final_answer})
    return AskResponse(
        session_id=session_id,
        answer=final_answer,
        tool_calls=traces
    )