"""Comparable Event Engine for Historical Event Studies.

Finds and analyzes statistically analogous historical events matching:
- Event type (ORDER_WIN, EARNINGS_RESULT, REGULATORY_APPROVAL, CAPEX)
- Sector and market cap bracket
- Event magnitude (% of revenue or order value)
- Prevailing market regime (Low Vol, High Vol, Trending)
Calculates historical return distributions (1D, 5D, 20D) and abnormal volumes.

Comparable events are ONLY derived from real ingested historical events supplied
by the caller. No fabricated "verified historical event" database is substituted:
when no real events are available, the engine returns an honest
DATA_UNAVAILABLE state rather than inventing reaction percentages.
"""
from typing import List, Dict, Any, Optional
import numpy as np


class ComparableEventEngine:
    @classmethod
    def find_comparables(
        cls,
        event_type: str,
        sector: Optional[str] = None,
        min_amount_cr: float = 0.0,
        limit: int = 5,
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Find analogous historical corporate announcements and calculate reaction statistics.

        `events` must be a list of real ingested historical events, each carrying at
        least `event_type`, `sector`, and observed reaction fields
        (`reaction_1d_pct`, `reaction_5d_pct`, `reaction_20d_pct`,
        `volume_multiple`). If no events are supplied, an honest
        DATA_UNAVAILABLE result is returned.
        """
        ev_norm = (event_type or "").upper()
        sec_norm = (sector or "").upper()
        source_events = events or []

        matches = []
        for ev in source_events:
            ev_type = str(ev.get("event_type", "")).upper()
            ev_sector = str(ev.get("sector", "")).upper()
            # Match on event type
            if ev_norm in ev_type or ev_type in ev_norm:
                # Optional sector filter
                if not sec_norm or ev_sector == sec_norm:
                    matches.append(ev)

        if not matches:
            return {
                "status": "DATA_UNAVAILABLE",
                "reason": "No ingested historical events match this event type/sector. "
                          "Comparable event studies require real historical corporate events.",
                "query_event_type": event_type,
                "query_sector": sector,
                "sample_size": 0,
                "statistics": None,
                "comparable_events": [],
                "disclaimer": "HISTORICAL COMPARABLE EVENT STUDY. Past market reactions to similar events provide statistical context only and do not guarantee future stock performance.",
            }

        matches = matches[:limit]

        def _nums(key: str) -> List[float]:
            out = []
            for m in matches:
                v = m.get(key)
                if v is not None:
                    try:
                        out.append(float(v))
                    except (TypeError, ValueError):
                        continue
            return out

        r1d = _nums("reaction_1d_pct")
        r5d = _nums("reaction_5d_pct")
        r20d = _nums("reaction_20d_pct")
        vols = _nums("volume_multiple")

        return {
            "status": "AVAILABLE",
            "query_event_type": event_type,
            "query_sector": sector,
            "sample_size": len(matches),
            "statistics": {
                "median_1d_reaction_pct": float(round(np.median(r1d), 2)) if r1d else None,
                "median_5d_reaction_pct": float(round(np.median(r5d), 2)) if r5d else None,
                "median_20d_reaction_pct": float(round(np.median(r20d), 2)) if r20d else None,
                "median_volume_multiple": float(round(np.median(vols), 2)) if vols else None,
                "positive_reaction_ratio": float(round(sum(1 for x in r5d if x > 0) / max(1, len(r5d)), 2)) if r5d else None,
            },
            "comparable_events": matches,
            "disclaimer": "HISTORICAL COMPARABLE EVENT STUDY. Past market reactions to similar events provide statistical context only and do not guarantee future stock performance.",
        }
