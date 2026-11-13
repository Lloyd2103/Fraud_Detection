import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.modules.realtime.connection_manager import manager
from app.modules.alerts.service import alert_service
from app.modules.verdicts.service import verdict_service

router = APIRouter(tags=["Realtime"])

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Full-duplex WebSocket for Alert Queue.
    - session_inspector_id: Tracks the logged-in auditor identity to accurately compute
      personal KPIs (My Shift Audited, My Fraud Verdicts, etc.) regardless of list filter.
    - last_params: Filter parameters for table pagination and filtering.
    """
    await manager.connect(websocket)

    session_inspector_id = websocket.query_params.get("inspector_id") or websocket.query_params.get("user_id")

    last_params = {
        "status": "PENDING",
        "page": 1,
        "limit": 50,
        "sort_by": "risk_score:desc",
        "search": "",
        "channel": "ALL",
        "amount_range": "ALL",
        "inspector_id": None,
    }

    def _fetch_alerts(params):
        status = params.get("status", "PENDING")
        if status == "PROCESSED":
            return verdict_service.get_inspected_alerts(
                page=params.get("page", 1),
                limit=params.get("limit", 50),
                search=params.get("search", ""),
                channel=params.get("channel") if params.get("channel") not in (None, "ALL") else None,
                amount_range=params.get("amount_range") if params.get("amount_range") not in (None, "ALL") else None,
                inspector_id=params.get("inspector_id"),
            )
        else:
            return alert_service.get_pending_alerts(
                page=params.get("page", 1),
                limit=params.get("limit", 50),
                search=params.get("search", ""),
                channel=params.get("channel") if params.get("channel") not in (None, "ALL") else None,
                amount_range=params.get("amount_range") if params.get("amount_range") not in (None, "ALL") else None,
                sort_by=params.get("sort_by", "risk_score:desc"),
                order="desc",
            )

    def _get_summary():
        return alert_service.get_alerts_summary(inspector_id=session_inspector_id)

    try:
        # INIT: push summary (computed for session auditor) + first page of alerts
        summary = _get_summary()
        alerts_result = _fetch_alerts(last_params)
        await websocket.send_json({
            "type": "INIT",
            "summary": summary,
            "alerts": alerts_result.get("data", []),
            "total": alerts_result.get("total", 0),
            "total_pages": alerts_result.get("total_pages", 1),
            "page": alerts_result.get("page", 1),
            "timestamp": str(asyncio.get_event_loop().time()),
        })

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                cmd = json.loads(data)
                action = cmd.get("action", "")

                incoming_user = cmd.get("current_user") or cmd.get("session_user")
                if incoming_user:
                    session_inspector_id = incoming_user

                if action in ("FETCH_ALERTS", "FETCH_INSPECTED"):
                    last_params.update({
                        "status": "PROCESSED" if action == "FETCH_INSPECTED" else cmd.get("status", "PENDING"),
                        "page": int(cmd.get("page", 1)),
                        "limit": int(cmd.get("limit", 50)),
                        "sort_by": cmd.get("sortBy", "risk_score:desc"),
                        "search": cmd.get("search", ""),
                        "channel": cmd.get("channel", "ALL"),
                        "amount_range": cmd.get("amountRange", "ALL"),
                        "inspector_id": cmd.get("inspector_id"),
                    })
                    alerts_result = _fetch_alerts(last_params)
                    summary = _get_summary()
                    await websocket.send_json({
                        "type": "ALERT_LIST",
                        "status": last_params["status"],
                        "alerts": alerts_result.get("data", []),
                        "total": alerts_result.get("total", 0),
                        "total_pages": alerts_result.get("total_pages", 1),
                        "page": last_params["page"],
                        "summary": summary,
                    })

                elif action == "REFRESH_SUMMARY":
                    inspector_id = cmd.get("inspector_id") or cmd.get("current_user")
                    if inspector_id:
                        session_inspector_id = inspector_id
                    summary = _get_summary()
                    await websocket.send_json({
                        "type": "SUMMARY_UPDATE",
                        "summary": summary,
                    })

            except asyncio.TimeoutError:
                # Heartbeat: push fresh summary for session auditor + re-query list with last known params
                summary = _get_summary()
                alerts_result = _fetch_alerts(last_params)
                await websocket.send_json({
                    "type": "HEARTBEAT",
                    "summary": summary,
                    "alerts": alerts_result.get("data", []),
                    "total": alerts_result.get("total", 0),
                    "total_pages": alerts_result.get("total_pages", 1),
                    "page": last_params["page"],
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

