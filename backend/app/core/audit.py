from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.models.schemas import AuditLogCreateSchema, UserRole


class AuditLogService:
    """
    Append-only audit trail service.
    Intentionally exposes ONLY `record_event` and `list_patient_logs` (no update/delete methods).
    """

    def __init__(self, db_client: Any):
        self.db = db_client

    def record_event(
        self,
        patient_id: str,
        actor_id: str,
        actor_role: UserRole,
        action_summary: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validates and inserts an immutable audit record into Supabase."""
        entry = AuditLogCreateSchema(
            patient_id=patient_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action_summary=action_summary,
            previous_state=previous_state,
            new_state=new_state,
            timestamp=datetime.now(timezone.utc),
        )
        payload = entry.model_dump(mode="json")
        response = self.db.table("audit_logs").insert(payload).execute()
        return response.data[0] if response.data else payload

    def list_patient_logs(self, patient_id: str, limit: int = 50) -> list:
        """Fetches chronological audit trail for the patient/caretaker security feed."""
        response = (
            self.db.table("audit_logs")
            .select("*")
            .eq("patient_id", patient_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data