# HiMe Platform — AI Section Implementation Plan

## Epic 06: AI Matching & Analytics (Sprint 4)

**Total: 21 Story Points | 4 User Stories | Target: Sprint 4**

---

## Story Point Breakdown

### PB-15: Convert Resumes and Jobs to Embeddings (8 pts)
**Priority:** High | **Sprint:** 4

**Description:** As a system, I need to convert resume and job data into vector embeddings so that semantic similarity can be computed.

**Acceptance Criteria:**
- Embeddings are successfully created and stored
- Resume data (skills, experience, education) is converted to a text representation
- Job data (title, description, requirements) is converted to a text representation
- Embedding model: `all-MiniLM-L6-v2` (384 dimensions)
- Embeddings stored in PostgreSQL with proper indexing

**Technical Details:**
- New model: `Embedding` (entity_type, entity_id, embedding_vector, model_version)
- New service: `EmbeddingService` with lazy-loaded sentence-transformers model
- Text preprocessor for cleaning and normalizing input text
- Batch embedding generation support for efficiency

**Files Added:**
- `backend/app/services/ai/__init__.py`
- `backend/app/services/ai/embedding_service.py`
- `backend/app/services/ai/text_preprocessor.py`
- `backend/app/models/embedding.py`
- `backend/alembic/versions/xxx_add_embeddings_table.py`

---

### PB-16: Calculate Cosine Similarity (5 pts)
**Priority:** High | **Sprint:** 4

**Description:** As a system, I need to compute cosine similarity between candidate and job embeddings to determine match scores.

**Acceptance Criteria:**
- Cosine similarity is calculated and returned
- Match score is a weighted combination of:
  - Skills match (40%)
  - Experience match (25%)
  - Education match (15%)
  - Overall text similarity (20%)
- Score is normalized to 0-1 range
- Detailed breakdown is available

**Technical Details:**
- New service: `MatchingService` with component-level scoring
- Skills matching using Jaccard similarity
- Experience matching based on years vs required level
- Education matching based on degree hierarchy
- Configurable weights for different components

**Files Added:**
- `backend/app/services/ai/matching_service.py`

---

### PB-17: Employer Sees Ranked Candidates (5 pts)
**Priority:** High | **Sprint:** 4

**Description:** As an employer, I want to see candidates ranked by match score so I can prioritize outreach.

**Acceptance Criteria:**
- A ranked list of candidates is displayed, sorted by match
- Each candidate shows match percentage and breakdown
- Filter by minimum match score is available
- Only candidates with embeddings are included

**Technical Details:**
- API endpoint: `GET /api/ai/match/job/{job_id}/candidates`
- Optional query parameter: `min_score` (0-100)
- Response includes candidate details and match breakdown
- Sorted descending by match score

**Files Added:**
- `backend/app/api/ai_matching.py`
- `backend/app/schemas/ai_matching.py`

---

### PB-12: Job Seeker Sees Match Percentage (3 pts)
**Priority:** Medium | **Sprint:** 4

**Description:** As a job seeker, I want to see my match percentage with each job so I can prioritize applications.

**Acceptance Criteria:**
- Match percentage is shown for each job
- Matched and missing skills are displayed
- Filter by minimum match percentage is available
- Match breakdown is visible

**Technical Details:**
- API endpoint: `GET /api/ai/match/seeker/{seeker_id}/jobs`
- Optional query parameter: `min_match` (0-100)
- Response includes job details and match breakdown
- Sorted descending by match percentage

**Files Added:**
- (Uses same files as PB-17)

---

## Implementation Summary

| Story | Points | Priority | Status |
|-------|--------|----------|--------|
| PB-15: Resume & Job Embeddings | 8 | High | Files Created |
| PB-16: Cosine Similarity | 5 | High | Files Created |
| PB-17: Employer Candidate Ranking | 5 | High | Files Created |
| PB-12: Job Seeker Match % | 3 | Medium | Files Created |
| **Total** | **21** | | |

---

## API Endpoints

| Method | Endpoint | Story | Description |
|--------|----------|-------|-------------|
| GET | `/api/ai/match/seeker/{seeker_id}/job/{job_id}` | PB-12 | Single match score |
| GET | `/api/ai/match/seeker/{seeker_id}/jobs` | PB-12 | All job matches for seeker |
| GET | `/api/ai/match/job/{job_id}/candidates` | PB-17 | Ranked candidates for job |
| POST | `/api/ai/embeddings/resume/{seeker_id}` | PB-15 | Generate resume embedding |
| POST | `/api/ai/embeddings/job/{job_id}` | PB-15 | Generate job embedding |
| GET | `/api/ai/embeddings/status/{entity_type}/{entity_id}` | PB-15 | Check embedding status |
| GET | `/api/ai/model/info` | PB-15 | Get model information |

---

## Dependencies

```
sentence-transformers==2.2.2
torch>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
```

---

## Next Steps

1. Install dependencies: `pip install -r backend/ai_requirements.txt`
2. Run database migration: `alembic upgrade head`
3. Connect API endpoints to existing database models
4. Add frontend components for match display
5. Implement background job for bulk embedding generation
6. Add caching layer for performance
