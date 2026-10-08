# HiMe Platform — Backend API Requirements

## Overview

This document lists all API endpoints in the AI Matching module and what is needed from the backend team to make them fully production-ready.

---

## AI Matching API Endpoints

### 1. Generate Resume Embedding

| Detail | Value |
|--------|-------|
| **Method** | `POST` |
| **Endpoint** | `/api/ai/embeddings/resume/{seeker_id}` |
| **Auth** | Required (Job Seeker) |
| **Story** | PB-15 |

**Request:**
```json
{
  "seeker_id": "uuid"
}
```

**Response (200):**
```json
{
  "seeker_id": "uuid",
  "status": "success",
  "message": "Resume embedding generated successfully",
  "model": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

**What's Needed from Backend:**
- [ ] Ensure `JobSeeker` model has related `experiences`, `educations`, `skills` loaded
- [ ] Ensure `SeekerSkill` table is populated with skill names
- [ ] Trigger embedding generation automatically after resume upload/processing is complete

---

### 2. Generate Job Embedding

| Detail | Value |
|--------|-------|
| **Method** | `POST` |
| **Endpoint** | `/api/ai/embeddings/job/{job_id}` |
| **Auth** | Required (Employer) |
| **Story** | PB-15 |

**Request:**
```json
{
  "job_id": "uuid"
}
```

**Response (200):**
```json
{
  "job_id": "uuid",
  "status": "success",
  "message": "Job embedding generated successfully",
  "model": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

**What's Needed from Backend:**
- [ ] Ensure `Job` model has related `skills` (JobSkill) loaded
- [ ] Ensure `Job.company` relationship is loaded for company name
- [ ] Trigger embedding generation automatically after job is published

---

### 3. Check Embedding Status

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/embeddings/status/{entity_type}/{entity_id}` |
| **Auth** | Required |
| **Story** | PB-15 |

**Path Parameters:**
- `entity_type`: `"resume"` or `"job"`
- `entity_id`: UUID

**Response (200):**
```json
{
  "entity_type": "resume",
  "entity_id": "uuid",
  "has_embedding": true,
  "model_version": "all-MiniLM-L6-v2",
  "created_at": "2026-10-03T12:00:00"
}
```

**What's Needed from Backend:**
- [ ] None — fully implemented

---

### 4. Get Match Score (Seeker ↔ Job)

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/match/seeker/{seeker_id}/job/{job_id}` |
| **Auth** | Required |
| **Story** | PB-12 |

**Response (200):**
```json
{
  "seeker_id": "uuid",
  "job_id": "uuid",
  "match_percentage": 78.5,
  "match_score": 0.785,
  "breakdown": {
    "skills_match": 0.85,
    "experience_match": 0.70,
    "education_match": 0.90,
    "overall_text_match": 0.75
  },
  "matched_skills": ["Python", "FastAPI", "SQL"],
  "missing_skills": ["Docker", "AWS"]
}
```

**What's Needed from Backend:**
- [ ] Ensure seeker profile data is complete (skills, experience, education)
- [ ] Ensure job data is complete (title, description, requirements, skills)
- [ ] Both embeddings must exist before calling this endpoint

---

### 5. Get All Job Matches for Seeker

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/match/seeker/{seeker_id}/jobs` |
| **Auth** | Required (Job Seeker) |
| **Story** | PB-12 |

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_match` | float | 0.0 | Minimum match percentage (0-100) |

**Response (200):**
```json
{
  "seeker_id": "uuid",
  "min_match": 60.0,
  "total_jobs": 15,
  "jobs": [
    {
      "job_id": "uuid",
      "job_title": "Senior Python Developer",
      "company_name": "Tech Corp",
      "match_percentage": 85.2,
      "match_score": 0.852,
      "required_skills": ["Python", "FastAPI", "PostgreSQL"],
      "matched_skills": ["Python", "FastAPI"],
      "missing_skills": ["PostgreSQL"]
    }
  ]
}
```

**What's Needed from Backend:**
- [ ] Ensure all active jobs have embeddings generated
- [ ] Consider adding pagination for large job lists
- [ ] Consider caching results for performance

---

### 6. Get Ranked Candidates for Job

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/match/job/{job_id}/candidates` |
| **Auth** | Required (Employer) |
| **Story** | PB-17 |

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | float | 0.0 | Minimum match score (0-100) |

**Response (200):**
```json
{
  "job_id": "uuid",
  "job_title": "Senior Python Developer",
  "total_candidates": 42,
  "candidates": [
    {
      "seeker_id": "uuid",
      "full_name": "Ahmed Ali",
      "email": "ahmed@example.com",
      "match_percentage": 92.1,
      "match_score": 0.921,
      "skills_match": 0.95,
      "experience_match": 0.90,
      "education_match": 0.85,
      "resume_url": "https://..."
    }
  ]
}
```

**What's Needed from Backend:**
- [ ] Ensure all seeker profiles have embeddings generated
- [ ] Add authorization: only the job's company can view candidates
- [ ] Consider adding pagination
- [ ] Consider adding filters (e.g., by skills, location, experience)

---

### 7. Get Model Info

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/model/info` |
| **Auth** | None |
| **Story** | PB-15 |

**Response (200):**
```json
{
  "model_name": "all-MiniLM-L6-v2",
  "embedding_dimension": 384,
  "loaded": true
}
```

**What's Needed from Backend:**
- [ ] None — fully implemented

---

## Summary Table

| # | Endpoint | Method | Auth | Status |
|---|----------|--------|------|--------|
| 1 | `/api/ai/embeddings/resume/{seeker_id}` | POST | Seeker | Ready |
| 2 | `/api/ai/embeddings/job/{job_id}` | POST | Employer | Ready |
| 3 | `/api/ai/embeddings/status/{type}/{id}` | GET | Any | Ready |
| 4 | `/api/ai/match/seeker/{sid}/job/{jid}` | GET | Any | Ready |
| 5 | `/api/ai/match/seeker/{sid}/jobs` | GET | Seeker | Ready |
| 6 | `/api/ai/match/job/{jid}/candidates` | GET | Employer | Ready |
| 7 | `/api/ai/model/info` | GET | None | Ready |

---

## Backend Team Action Items

### High Priority
1. **Auto-generate embeddings** when resume is uploaded/processed
2. **Auto-generate embeddings** when job is published
3. **Add authorization** to candidate ranking endpoint (only job owner can view)

### Medium Priority
4. **Add pagination** to list endpoints (jobs, candidates)
5. **Add caching** for match score calculations
6. **Add filters** to candidate ranking (skills, location, experience)

### Low Priority
7. **Add bulk embedding generation** endpoint for batch processing
8. **Add embedding regeneration** trigger when profile/job is updated
9. **Monitor model performance** and consider upgrading to larger model

---

## Environment Variables Needed

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/hime

# AI Model
AI_EMBEDDING_MODEL=all-MiniLM-L6-v2
AI_EMBEDDING_DIMENSION=384

# Optional: Caching
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
```

---

## Database Migration

Run the following to create the embeddings table:

```bash
cd backend
alembic upgrade head
```

This will create the `embeddings` table with:
- `id` (PK)
- `entity_type` (resume/job)
- `entity_id` (UUID)
- `embedding_vector` (ARRAY of Floats, 384 dimensions)
- `model_version` (String)
- `created_at`, `updated_at` (Timestamps)
