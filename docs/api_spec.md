# API Spec (summary)

POST /api/start-analysis
  body: { repository_url: string, options: object }
  returns: { job_id: string }

POST /api/control/{job_id}/pause
POST /api/control/{job_id}/resume

GET /api/jobs/{job_id}/status
GET /api/docs/{job_id}/mermaid
