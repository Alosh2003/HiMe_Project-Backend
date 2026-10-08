# HiMe Platform — Frontend API Integration Guide

## Overview

This document lists all API endpoints the frontend needs to consume for the AI Matching & Analytics feature (Epic 06 — Sprint 4).

---

## API Endpoints for Frontend

### 1. Generate Resume Embedding

**When to call:** After user uploads resume and it's processed

| Detail | Value |
|--------|-------|
| **Method** | `POST` |
| **Endpoint** | `/api/ai/embeddings/resume/{seeker_id}` |
| **Auth** | Required (Job Seeker) |

**Request:**
```
POST /api/ai/embeddings/resume/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "seeker_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "success",
  "message": "Resume embedding generated successfully",
  "model": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

**Frontend Usage:**
```javascript
// After resume upload is complete
const generateEmbedding = async (seekerId) => {
  const response = await fetch(`/api/ai/embeddings/resume/${seekerId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  return response.json();
};
```

---

### 2. Generate Job Embedding

**When to call:** After employer publishes a job

| Detail | Value |
|--------|-------|
| **Method** | `POST` |
| **Endpoint** | `/api/ai/embeddings/job/{job_id}` |
| **Auth** | Required (Employer) |

**Request:**
```
POST /api/ai/embeddings/job/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "success",
  "message": "Job embedding generated successfully",
  "model": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

**Frontend Usage:**
```javascript
// After job is published
const generateJobEmbedding = async (jobId) => {
  const response = await fetch(`/api/ai/embeddings/job/${jobId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  return response.json();
};
```

---

### 3. Check Embedding Status

**When to call:** To show whether a profile/job has been processed by AI

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/embeddings/status/{entity_type}/{entity_id}` |
| **Auth** | Required |

**Request:**
```
GET /api/ai/embeddings/status/resume/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "entity_type": "resume",
  "entity_id": "123e4567-e89b-12d3-a456-426614174000",
  "has_embedding": true,
  "model_version": "all-MiniLM-L6-v2",
  "created_at": "2026-10-03T12:00:00"
}
```

**Frontend Usage:**
```javascript
// Show AI processing status on profile
const checkEmbeddingStatus = async (entityType, entityId) => {
  const response = await fetch(`/api/ai/embeddings/status/${entityType}/${entityId}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  const data = await response.json();
  return data.has_embedding; // true = AI ready, false = pending
};
```

---

### 4. Get Match Score (Seeker ↔ Job)

**When to call:** When viewing a job details page

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/match/seeker/{seeker_id}/job/{job_id}` |
| **Auth** | Required |

**Request:**
```
GET /api/ai/match/seeker/123e4567-e89b-12d3-a456-426614174000/job/987e6543-e89b-12d3-a456-426614174000
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "seeker_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_id": "987e6543-e89b-12d3-a456-426614174000",
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

**Frontend Usage:**
```javascript
// Show match score on job card
const getMatchScore = async (seekerId, jobId) => {
  const response = await fetch(`/api/ai/match/seeker/${seekerId}/job/${jobId}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  return response.json();
};

// Display in UI
const MatchBadge = ({ matchPercentage }) => (
  <div className={`match-badge ${matchPercentage >= 70 ? 'high' : 'medium'}`}>
    {matchPercentage}% Match
  </div>
);
```

---

### 5. Get All Job Matches for Seeker

**When to call:** Job seeker dashboard — "Recommended Jobs" section

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/match/seeker/{seeker_id}/jobs` |
| **Auth** | Required (Job Seeker) |

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_match` | float | 0.0 | Minimum match percentage (0-100) |

**Request:**
```
GET /api/ai/match/seeker/123e4567-e89b-12d3-a456-426614174000/jobs?min_match=60
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "seeker_id": "123e4567-e89b-12d3-a456-426614174000",
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

**Frontend Usage:**
```javascript
// Recommended jobs list
const getRecommendedJobs = async (seekerId, minMatch = 60) => {
  const response = await fetch(
    `/api/ai/match/seeker/${seekerId}/jobs?min_match=${minMatch}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  return response.json();
};

// Job card component
const JobMatchCard = ({ job }) => (
  <div className="job-card">
    <h3>{job.job_title}</h3>
    <p>{job.company_name}</p>
    <MatchBadge percentage={job.match_percentage} />
    <SkillMatch matched={job.matched_skills} missing={job.missing_skills} />
  </div>
);
```

---

### 6. Get Ranked Candidates for Job

**When to call:** Employer dashboard — "Top Candidates" for a job

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/match/job/{job_id}/candidates` |
| **Auth** | Required (Employer) |

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | float | 0.0 | Minimum match score (0-100) |

**Request:**
```
GET /api/ai/match/job/987e6543-e89b-12d3-a456-426614174000/candidates?min_score=70
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "job_id": "987e6543-e89b-12d3-a456-426614174000",
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

**Frontend Usage:**
```javascript
// Ranked candidates list
const getRankedCandidates = async (jobId, minScore = 70) => {
  const response = await fetch(
    `/api/ai/match/job/${jobId}/candidates?min_score=${minScore}`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  return response.json();
};

// Candidate card component
const CandidateCard = ({ candidate, rank }) => (
  <div className="candidate-card">
    <div className="rank">#{rank}</div>
    <h3>{candidate.full_name}</h3>
    <p>{candidate.email}</p>
    <MatchBadge percentage={candidate.match_percentage} />
    <MatchBreakdown breakdown={candidate} />
  </div>
);
```

---

### 7. Get Model Info

**When to call:** Admin panel or debug info

| Detail | Value |
|--------|-------|
| **Method** | `GET` |
| **Endpoint** | `/api/ai/model/info` |
| **Auth** | None |

**Request:**
```
GET /api/ai/model/info
```

**Response (200):**
```json
{
  "model_name": "all-MiniLM-L6-v2",
  "embedding_dimension": 384,
  "loaded": true
}
```

**Frontend Usage:**
```javascript
// Show AI model info in admin panel
const getModelInfo = async () => {
  const response = await fetch('/api/ai/model/info');
  return response.json();
};
```

---

## Summary Table

| # | Endpoint | Method | Auth | Frontend Use Case |
|---|----------|--------|------|-------------------|
| 1 | `/api/ai/embeddings/resume/{seeker_id}` | POST | Seeker | After resume upload |
| 2 | `/api/ai/embeddings/job/{job_id}` | POST | Employer | After job publish |
| 3 | `/api/ai/embeddings/status/{type}/{id}` | GET | Any | Show AI status |
| 4 | `/api/ai/match/seeker/{sid}/job/{jid}` | GET | Any | Job detail page |
| 5 | `/api/ai/match/seeker/{sid}/jobs` | GET | Seeker | Recommended jobs |
| 6 | `/api/ai/match/job/{jid}/candidates` | GET | Employer | Top candidates |
| 7 | `/api/ai/model/info` | GET | None | Admin/debug |

---

## Frontend Component Suggestions

### 1. Match Badge Component
```javascript
const MatchBadge = ({ percentage }) => {
  let color = 'red';
  if (percentage >= 80) color = 'green';
  else if (percentage >= 60) color = 'yellow';
  
  return (
    <span className={`match-badge ${color}`}>
      {percentage}% Match
    </span>
  );
};
```

### 2. Skills Match Component
```javascript
const SkillMatch = ({ matched, missing }) => (
  <div className="skill-match">
    <div className="matched">
      {matched.map(s => <span key={s} className="skill-tag matched">{s}</span>)}
    </div>
    <div className="missing">
      {missing.map(s => <span key={s} className="skill-tag missing">{s}</span>)}
    </div>
  </div>
);
```

### 3. Match Breakdown Component
```javascript
const MatchBreakdown = ({ breakdown }) => (
  <div className="match-breakdown">
    <div className="breakdown-item">
      <label>Skills</label>
      <progress value={breakdown.skills_match * 100} max="100" />
      <span>{Math.round(breakdown.skills_match * 100)}%</span>
    </div>
    <div className="breakdown-item">
      <label>Experience</label>
      <progress value={breakdown.experience_match * 100} max="100" />
      <span>{Math.round(breakdown.experience_match * 100)}%</span>
    </div>
    <div className="breakdown-item">
      <label>Education</label>
      <progress value={breakdown.education_match * 100} max="100" />
      <span>{Math.round(breakdown.education_match * 100)}%</span>
    </div>
  </div>
);
```

### 4. Recommended Jobs List
```javascript
const RecommendedJobs = ({ seekerId }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      const data = await getRecommendedJobs(seekerId, 60);
      setJobs(data.jobs);
      setLoading(false);
    };
    fetchJobs();
  }, [seekerId]);

  if (loading) return <Loader />;

  return (
    <div className="recommended-jobs">
      <h2>Recommended Jobs</h2>
      {jobs.map(job => <JobMatchCard key={job.job_id} job={job} />)}
    </div>
  );
};
```

### 5. Ranked Candidates List
```javascript
const RankedCandidates = ({ jobId }) => {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCandidates = async () => {
      const data = await getRankedCandidates(jobId, 70);
      setCandidates(data.candidates);
      setLoading(false);
    };
    fetchCandidates();
  }, [jobId]);

  if (loading) return <Loader />;

  return (
    <div className="ranked-candidates">
      <h2>Top Candidates</h2>
      {candidates.map((candidate, index) => (
        <CandidateCard key={candidate.seeker_id} candidate={candidate} rank={index + 1} />
      ))}
    </div>
  );
};
```

---

## Error Handling

### Common Error Responses

| Status | Message | Frontend Action |
|--------|---------|-----------------|
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Show "Access Denied" |
| 404 | Not Found | Show "Not Found" message |
| 400 | Embedding not found | Trigger embedding generation |
| 500 | Server Error | Show generic error, retry |

### Error Handling Example
```javascript
const handleApiCall = async (url, options) => {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API Error');
    }
    return response.json();
  } catch (error) {
    console.error('API Error:', error);
    showToast(error.message, 'error');
    throw error;
  }
};
```

---

## API Base URL Configuration

```javascript
// config.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  generateResumeEmbedding: (seekerId) => `${API_BASE_URL}/api/ai/embeddings/resume/${seekerId}`,
  generateJobEmbedding: (jobId) => `${API_BASE_URL}/api/ai/embeddings/job/${jobId}`,
  checkEmbeddingStatus: (type, id) => `${API_BASE_URL}/api/ai/embeddings/status/${type}/${id}`,
  getMatchScore: (seekerId, jobId) => `${API_BASE_URL}/api/ai/match/seeker/${seekerId}/job/${jobId}`,
  getRecommendedJobs: (seekerId, minMatch = 60) => `${API_BASE_URL}/api/ai/match/seeker/${seekerId}/jobs?min_match=${minMatch}`,
  getRankedCandidates: (jobId, minScore = 70) => `${API_BASE_URL}/api/ai/match/job/${jobId}/candidates?min_score=${minScore}`,
  getModelInfo: () => `${API_BASE_URL}/api/ai/model/info`,
};
```

---

## Environment Variables

```env
# .env
VITE_API_URL=http://localhost:8000
```
