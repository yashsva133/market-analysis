# Ingestion Engine & Data Sources Guide

**System:** India Market AI Research Terminal  
**Status:** Production Hardened  
**Coverage:** NSE, BSE, SEBI, PIB, MCA, Company IR & RSS Feeds  

---

## 1. Data Ingestion Architecture

The terminal monitors official disclosure endpoints across the entire Indian capital markets ecosystem. It utilizes an asynchronous, non-blocking collector mesh backed by circuit breakers, rate limiters, session bootstrappers, and content deduplicators.

```
                    ┌─────────────────────────┐
                    │     Source Registry     │
                    └────────────┬────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
┌───────────────┐       ┌─────────────────┐       ┌──────────────────┐
│ NSE Client    │       │   BSE Client    │       │ Regulatory (PIB/ │
│ (Announcements│       │ (Corporate      │       │ SEBI / MCA / RSS)│
│  & Circulars) │       │  Filings)       │       │                  │
└───────┬───────┘       └────────┬────────┘       └────────┬─────────┘
        │                        │                         │
        └────────────────────────┼─────────────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │  Circuit Breaker &    │
                     │  Rate Limiting Mesh   │
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │  Raw Capture & Store  │
                     │ (SHA-256 Deduplication│
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │ Event Pipeline Worker │
                     └───────────────────────┘
```

---

## 2. Integrated Data Sources

| Source Name | Protocol | Poll Frequency | Rate Limit | Primary Payload Type | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NSE Announcements** | HTTPS / REST | 60s | 5 req / 10s | JSON / PDF Links | Corporate actions, board meetings, financial results, order book wins. |
| **BSE Filings** | HTTPS / REST | 60s | 5 req / 10s | JSON / XML / PDF | SEBI Reg 30 disclosures, insider trading, management change, resolution plans. |
| **SEBI Regulatory** | HTTPS / RSS | 300s | 2 req / 10s | XML / HTML | Regulatory orders, adjudication proceedings, circulars, takeover panel. |
| **PIB Economic** | HTTPS / RSS | 300s | 2 req / 10s | XML / HTML | Ministry of Finance, Commerce & Industry, Cabinet approvals, PLI schemes. |
| **Company IR / RSS**| HTTPS / Feed | 600s | 5 req / 10s | RSS / Atom / XML | Official press releases, investor presentations, transcripts. |

---

## 3. Resilience, Fault Tolerance & Self-Healing

Exchange endpoints frequently present anti-bot mechanisms, Cloudflare challenges, or transient socket timeouts. The terminal enforces strict resilience boundaries:

### 3.1 Session Bootstrapping & Cookie Handling
- **NSE Handshake:** NSE India endpoints require specific browser headers (`User-Agent`, `Accept-Language`, `Referer`) and valid session cookies set by visiting `https://www.nseindia.com/` prior to hitting API paths. The `NSEClient` automatically initiates and caches this cookie jar.
- **BSE Anti-Scraping:** BSE endpoints use rolling query parameters and dynamic request headers handled by `BSEClient`.

### 3.2 Circuit Breaker Specification
Each client implements an independent `CircuitBreaker` with three states:
- **CLOSED:** Normal operation. All requests proceed.
- **OPEN:** After consecutive failures (configured as `failure_threshold = 5`), the breaker trips. Requests immediately fail fast without making outbound network calls for `recovery_timeout = 60` seconds.
- **HALF-OPEN:** When the recovery timeout elapses, a single probe request is attempted. If it succeeds, the breaker resets to `CLOSED`; if it fails, it returns to `OPEN`.

### 3.3 Retry Policy & Exponential Backoff
- Failed HTTP calls (status codes 429, 500, 502, 503, 504 or network disconnects) retry up to 3 times.
- Delay follows exponential backoff with full jitter:
  $$\text{Delay} = \min(\text{max\_delay}, \text{base\_delay} \times 2^{\text{attempt}}) \pm \text{jitter}$$
- Every source has a hard retry budget per polling cycle to avoid cascading thread exhaustion.

### 3.4 Cross-Source Failure Isolation
> [!IMPORTANT]
> **Zero Cascading Failures:** A complete failure or IP block of NSE India will **never** stop BSE, PIB, or RSS sources from functioning. Collectors run in independent async tasks with bounded worker pools.

---

## 4. Health & Status Classification

Every registered source is continuously monitored and evaluated against five distinct operational states:

1. **`healthy`**: The source is responding normally, latency is within SLA (< 2000ms), and consecutive failures = 0.
2. **`degraded`**: The source is experiencing intermittent errors, but still returning valid data within retry limits.
3. **`rate-limited`**: The source returned HTTP 429. The rate limiter backoff window is actively pausing requests.
4. **`failed`**: The circuit breaker is OPEN. All recent requests failed consecutively.
5. **`stale`**: The source has not yielded a successful update within 3x its scheduled polling interval.

The current system health is always available via:
```http
GET /api/sources/health
```

Example output:
```json
{
  "total_sources": 5,
  "healthy": 4,
  "degraded": 1,
  "failed": 0,
  "stale": 0,
  "sources": [
    {
      "source_id": "nse_corp_announcements",
      "name": "NSE Corporate Announcements",
      "status": "healthy",
      "consecutive_failures": 0,
      "last_latency_ms": 342.1,
      "last_success": "2026-09-20T04:30:15Z"
    }
  ]
}
```

---

## 5. Offline Replay & Testing Mode

To enable automated testing and offline development without triggering exchange IP bans:
- The system includes synthetic and recorded replay fixtures in `tests/fixtures/`.
- Set `OFFLINE_MODE=true` in `.env` to bypass live socket connections and cycle through pre-recorded announcement payloads.
- All deduplication and document extraction logic can be verified completely offline.
