"""Unit tests for Point-in-Time as-of joins and Future Information Leakage Prevention."""
import pytest
from datetime import datetime, timezone, timedelta
from packages.scenario_engine.features.event_features import EventFeatureExtractor


def test_leakage_future_announcement_rejected():
    """Verify events occurring after prediction timestamp are strictly excluded from feature snapshot."""
    prediction_time = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Event announced on March 20 (future relative to prediction_time)
    future_event = {
        "event_id": "ev-future-1",
        "symbol": "RELIANCE",
        "announcement_time": (prediction_time + timedelta(days=5)).isoformat(),
        "importance": "CRITICAL",
        "event_type": "ORDER_WIN",
        "amount": 10000.0 * 1e7,
    }

    # Past event announced on March 10
    past_event = {
        "event_id": "ev-past-1",
        "symbol": "RELIANCE",
        "announcement_time": (prediction_time - timedelta(days=5)).isoformat(),
        "importance": "HIGH",
        "event_type": "CAPEX",
        "amount": 2000.0 * 1e7,
    }

    features = EventFeatureExtractor.extract(
        events=[future_event, past_event],
        as_of=prediction_time,
    )

    # Future event must not be counted in recent critical events
    assert features["events_critical_count_90d"] == 0
    # Only past event should be reflected
    assert features["events_high_count_90d"] == 1
    assert features["events_order_win_count"] == 0
    assert features["events_capex_count"] == 1


def test_leakage_future_financial_results_rejected():
    """Verify announcements after prediction timestamp do not leak into recency calculation."""
    prediction_time = datetime(2026, 3, 31, 15, 30, 0, tzinfo=timezone.utc)

    # Future corporate filing on May 15
    future_filing = {
        "event_id": "ev-future-q4",
        "symbol": "RELIANCE",
        "announcement_time": "2026-05-15T10:00:00+00:00",
        "importance": "CRITICAL",
        "event_type": "FINANCIAL_RESULTS",
    }

    # Past filing on January 15
    past_filing = {
        "event_id": "ev-past-q3",
        "symbol": "RELIANCE",
        "announcement_time": "2026-01-15T10:00:00+00:00",
        "importance": "HIGH",
        "event_type": "FINANCIAL_RESULTS",
    }

    features = EventFeatureExtractor.extract(
        events=[future_filing, past_filing],
        as_of=prediction_time,
    )

    # Future event must not be counted
    assert features["events_critical_count_90d"] == 0
    assert features["events_high_count_90d"] == 1
    # Recency must be measured from January, not May
    assert features["event_recency_days"] > 60.0


def test_leakage_future_candle_rejected():
    """Verify future price candles after prediction timestamp are strictly excluded."""
    from packages.scenario_engine.features.price_features import PriceFeatureExtractor

    as_of = datetime(2026, 3, 15, 15, 30, 0, tzinfo=timezone.utc)

    candles = [
        {"timestamp": "2026-03-10T10:00:00+00:00", "close": 2400.0},
        {"timestamp": "2026-03-11T10:00:00+00:00", "close": 2420.0},
        {"timestamp": "2026-03-12T10:00:00+00:00", "close": 2450.0},
        {"timestamp": "2026-03-13T10:00:00+00:00", "close": 2480.0},
        {"timestamp": "2026-03-14T10:00:00+00:00", "close": 2500.0},
        # Future candles that occurred after prediction timestamp (e.g. huge rally)
        {"timestamp": "2026-03-20T10:00:00+00:00", "close": 3200.0},
        {"timestamp": "2026-03-25T10:00:00+00:00", "close": 3500.0},
    ]

    features = PriceFeatureExtractor.extract_point_in_time(candles, as_of=as_of)

    # 1D return should be from 2480 to 2500 (+0.81%), NOT from 3200 to 3500 (+9.38%)
    assert features["return_1d"] == pytest.approx(0.81, rel=1e-1)
    # 52W high should be 2500 (distance = 0.0), NOT 3500
    assert features["distance_from_52w_high"] == pytest.approx(0.0, abs=1e-2)


def test_leakage_future_corporate_action_rejected():
    """Verify corporate actions announced after prediction timestamp are strictly excluded."""
    prediction_time = datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc)

    future_split = {
        "event_id": "ev-split-future",
        "symbol": "TCS",
        "announcement_time": "2026-02-28T10:00:00+00:00",
        "importance": "HIGH",
        "event_type": "SPLIT",
    }

    past_dividend = {
        "event_id": "ev-div-past",
        "symbol": "TCS",
        "announcement_time": "2026-01-10T10:00:00+00:00",
        "importance": "HIGH",
        "event_type": "DIVIDEND",
    }

    features = EventFeatureExtractor.extract(
        events=[future_split, past_dividend],
        as_of=prediction_time,
    )

    # Future split must NOT be counted; only the past dividend is counted
    assert features["events_corporate_action_count"] == 1

