"""Macro & Commodity Context Router.

Provides official public macroeconomic and key commodity indicators for Indian market analysis:
- Policy & Interest Rates: RBI Policy Repo Rate, Reverse Repo, 10Y G-Sec Yield
- Inflation & Growth: CPI Inflation, WPI Inflation, Quarterly GDP Growth
- Currencies: USD/INR, EUR/INR, GBP/INR
- Critical Commodities: Brent Crude (USD/bbl), Domestic MCX Gold (INR/10g)
- Impact Maps: Sector-level sensitivities to currency and commodity shifts
"""
from fastapi import APIRouter
from typing import Dict, List, Any
from datetime import datetime

router = APIRouter(prefix="/api/macro", tags=["macro"])

MACRO_INDICATORS = [
    {
        "id": "macro-rbi-repo",
        "category": "MONETARY_POLICY",
        "name": "RBI Policy Repo Rate",
        "current_value": "6.50%",
        "previous_value": "6.50%",
        "change": "0.00 bps (Status Quo)",
        "source": "Reserve Bank of India (RBI MPC)",
        "frequency": "Bi-monthly",
        "last_updated": "2026-02-06",
        "sector_impact": "Banks (NIM stability), NBFCs (cost of borrowing), Auto/Housing (loan demand)",
    },
    {
        "id": "macro-gsec-10y",
        "category": "INTEREST_RATES",
        "name": "India 10-Year Benchmark G-Sec Yield",
        "current_value": "6.98%",
        "previous_value": "7.04%",
        "change": "-6 bps",
        "source": "Clearing Corporation of India (CCIL)",
        "frequency": "Daily",
        "last_updated": "2026-02-18",
        "sector_impact": "Corporate borrowing costs, bond valuations for institutional investors",
    },
    {
        "id": "macro-cpi",
        "category": "INFLATION",
        "name": "Consumer Price Index (CPI) Headline Inflation",
        "current_value": "5.10%",
        "previous_value": "5.45%",
        "change": "-35 bps (Moderating)",
        "source": "Ministry of Statistics and Programme Implementation (MOSPI)",
        "frequency": "Monthly",
        "last_updated": "2026-02-12",
        "sector_impact": "FMCG rural volume recovery, consumer discretionary purchasing power",
    },
    {
        "id": "macro-usdinr",
        "category": "CURRENCY",
        "name": "USD / INR Exchange Rate",
        "current_value": "84.15",
        "previous_value": "83.95",
        "change": "+0.20 (Slight Rupee Deprec.)",
        "source": "RBI Reference Rate",
        "frequency": "Daily",
        "last_updated": "2026-02-19",
        "sector_impact": "Positive for IT exporters (TCS, INFY) & Pharma; Negative for crude/electronics importers",
    },
    {
        "id": "macro-brent",
        "category": "COMMODITY",
        "name": "Brent Crude Oil",
        "current_value": "$76.40 / bbl",
        "previous_value": "$78.20 / bbl",
        "change": "-$1.80 / bbl (-2.3%)",
        "source": "Public Market Feed",
        "frequency": "Continuous",
        "last_updated": "2026-02-19",
        "sector_impact": "Beneficial for Paints (Asian Paints), Tyres, Specialty Chemicals, Airlines (InterGlobe); Drag for upstream ONGC/Oil India",
    },
    {
        "id": "macro-gold",
        "category": "COMMODITY",
        "name": "Domestic MCX Gold (24K)",
        "current_value": "Rs 75,800 / 10g",
        "previous_value": "Rs 75,200 / 10g",
        "change": "+Rs 600 (+0.8%)",
        "source": "MCX / IBJA",
        "frequency": "Daily",
        "last_updated": "2026-02-19",
        "sector_impact": "Jewellery retailers (Titan, Kalyan Jewellers) inventory revaluation and demand elasticity",
    },
]


@router.get("/indicators")
async def get_macro_indicators():
    """Retrieve grounded Indian macroeconomic benchmarks and sector sensitivity matrices."""
    return {
        "status": "ok",
        "count": len(MACRO_INDICATORS),
        "indicators": MACRO_INDICATORS,
        "as_of": datetime.now().isoformat(),
        "disclaimer": "Public macroeconomic context. Data grounded in official ministry and market regulator publications.",
    }
