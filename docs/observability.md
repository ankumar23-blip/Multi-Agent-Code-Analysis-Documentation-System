# Observability & Traceability

- Each agent emits events using `backend/utils/langfuse_client.py::track_event`
- Store agent operational logs in a system table for traceability.
- Consider adding OpenTelemetry instrumentation for distributed traces.
- Langfuse integration placeholder in `backend/utils/langfuse_client.py`.
