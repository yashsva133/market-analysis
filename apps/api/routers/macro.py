"""Macro & Commodity Context Router.

No macroeconomic time series is ingested by this deployment, so the endpoint
reports that honestly rather than serving hardcoded indicator values.
"""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/indicators")
async def get_macro_indicators():
    """Macro indicators require an ingested official-statistics feed; none is connected yet."""
    return {
        "status": "ok",
        "count": 0,
        "indicators": [],
        "as_of": datetime.now(timezone.utc).isoformat(),
        "note": (
            "No macroeconomic data feed (RBI, MOSPI, CCIL, MCX) is ingested in this deployment. "
            "Indicator values are not fabricated; connect an official statistics source to populate this panel."
        ),
    }
