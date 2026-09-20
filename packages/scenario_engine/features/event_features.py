"""Event Features Extractor for Scenario & Forecast Engine.

Transforms structured corporate actions, order wins, board decisions,
and regulatory disclosures into quantitative feature representations.
"""
from typing import List, Dict, Any
from datetime import datetime, timezone


class EventFeatureExtractor:
    @staticmethod
    def extract(events: List[Dict[str, Any]], as_of: datetime = None) -> Dict[str, float]:
        """Extract quantitative features from recent corporate disclosures."""
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        critical_count = 0
        high_count = 0
        order_win_count = 0
        order_win_value_cr = 0.0
        results_count = 0
        regulatory_count = 0
        management_change_count = 0
        capex_count = 0
        dividend_or_bonus_count = 0

        most_recent_days = 999.0

        for ev in events:
            imp = (ev.get("importance") or "MEDIUM").upper()
            ev_type = (ev.get("event_type") or "").upper()
            amt = float(ev.get("amount") or 0.0)

            # Point-in-time filtering: exclude events published after as_of
            ann_time = ev.get("announcement_time") or ev.get("created_at") or ev.get("published_at")
            if ann_time:
                try:
                    if isinstance(ann_time, str):
                        dt = datetime.fromisoformat(ann_time.replace("Z", "+00:00"))
                    elif isinstance(ann_time, datetime):
                        dt = ann_time if ann_time.tzinfo else ann_time.replace(tzinfo=timezone.utc)
                    else:
                        dt = None
                    
                    if dt and dt > as_of:
                        # Future announcement relative to point-in-time as_of date: SKIP to prevent leakage!
                        continue

                    if dt:
                        days_ago = max(0.0, (as_of - dt).total_seconds() / 86400.0)
                        if days_ago < most_recent_days:
                            most_recent_days = days_ago
                except Exception:
                    pass

            if imp == "CRITICAL":
                critical_count += 1
            elif imp == "HIGH":
                high_count += 1

            if "ORDER" in ev_type or "CONTRACT" in ev_type:
                order_win_count += 1
                order_win_value_cr += (amt / 1e7) if amt > 0 else 0.0
            elif "RESULT" in ev_type or "FINANCIAL" in ev_type:
                results_count += 1
            elif "REGULATORY" in ev_type or "SEBI" in ev_type:
                regulatory_count += 1
            elif "MANAGEMENT" in ev_type or "DIRECTOR" in ev_type:
                management_change_count += 1
            elif "CAPEX" in ev_type or "EXPANSION" in ev_type:
                capex_count += 1
            elif "DIVIDEND" in ev_type or "BONUS" in ev_type or "SPLIT" in ev_type:
                dividend_or_bonus_count += 1

        recency_val = min(most_recent_days, 180.0) if most_recent_days < 999.0 else 180.0
        # Decay score: e^(-days / 30)
        import math
        event_intensity = math.exp(-recency_val / 30.0) * (1.0 + (0.5 * critical_count) + (0.2 * high_count))

        return {
            "events_critical_count_90d": float(critical_count),
            "events_high_count_90d": float(high_count),
            "events_order_win_count": float(order_win_count),
            "events_order_win_value_cr": float(round(order_win_value_cr, 2)),
            "events_results_count": float(results_count),
            "events_regulatory_count": float(regulatory_count),
            "events_management_change_count": float(management_change_count),
            "events_capex_count": float(capex_count),
            "events_corporate_action_count": float(dividend_or_bonus_count),
            "event_recency_days": float(round(recency_val, 1)),
            "event_intensity_score": float(round(event_intensity, 4)),
        }
