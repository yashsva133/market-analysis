"""Global Unified Search Router.

Provides fast multi-entity search across the entire Indian equity database:
- Companies (Name, Ticker, BSE Scrip, ISIN)
- Corporate Events (Taxonomy, Headline, Keywords)
- Exchange Filings & Extracted Documents
- News Headlines & Clusters
- Sectors & Themes
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import re

router = APIRouter(prefix="/api/search", tags=["search"])

SEARCH_INDEX = {
    "companies": [
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "isin": "INE002A01018", "sector": "Energy & Telecom", "bse_scrip": "500325", "price": "₹3,021.23", "aliases": ["RIL", "JIO", "RELIANCE"]},
        {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "isin": "INE467B01029", "sector": "Information Technology", "bse_scrip": "532540", "price": "₹4,250.00", "aliases": ["TCS", "TATA CONSULTANCY"]},
        {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "isin": "INE040A01034", "sector": "Financial Services", "bse_scrip": "500180", "price": "₹1,640.00", "aliases": ["HDFC", "HDFCBANK"]},
        {"symbol": "INFY", "name": "Infosys Ltd", "isin": "INE009A01021", "sector": "Information Technology", "bse_scrip": "500209", "price": "₹1,885.00", "aliases": ["INFY", "INFOSYS"]},
        {"symbol": "LT", "name": "Larsen & Toubro Ltd", "isin": "INE018A01030", "sector": "Infrastructure & EPC", "bse_scrip": "500510", "price": "₹3,712.45", "aliases": ["LT", "L&T", "LARSEN"]},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "isin": "INE397D01024", "sector": "Telecommunication", "bse_scrip": "532454", "price": "₹1,893.30", "aliases": ["AIRTEL", "BHARTI", "BHARTIARTL"]},
        {"symbol": "ASAHIINDIA", "name": "Asahi India Glass Ltd (AIGL)", "isin": "INE439A01020", "sector": "Auto Ancillaries & Glass", "bse_scrip": "515030", "price": "₹685.40", "aliases": ["AIGL", "ASAHI", "ASAHIINDIA", "ASAHI GLASS"]},
        {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "isin": "INE090A01021", "sector": "Financial Services", "bse_scrip": "532174", "price": "₹1,220.00", "aliases": ["ICICI", "ICICIBANK"]},
        {"symbol": "SBIN", "name": "State Bank of India", "isin": "INE062A01020", "sector": "Financial Services", "bse_scrip": "500112", "price": "₹810.00", "aliases": ["SBI", "SBIN", "STATE BANK"]},
        {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "isin": "INE155A01022", "sector": "Automobile & EV", "bse_scrip": "500570", "price": "₹980.00", "aliases": ["TML", "TATAMOTORS", "TATA MOTORS"]},
        {"symbol": "ITC", "name": "ITC Ltd", "isin": "INE154A01025", "sector": "Consumer Goods & FMCG", "bse_scrip": "500875", "price": "₹490.00", "aliases": ["ITC"]},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "isin": "INE030A01027", "sector": "Consumer Goods", "bse_scrip": "500696", "price": "₹2,720.00", "aliases": ["HUL", "HINDUNILVR"]},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "isin": "INE296A01024", "sector": "Financial Services", "bse_scrip": "500034", "price": "₹7,150.00", "aliases": ["BAJAJFINANCE", "BAJFINANCE"]},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "isin": "INE237A01028", "sector": "Financial Services", "bse_scrip": "500247", "price": "₹1,790.00", "aliases": ["KOTAK", "KOTAKBANK"]},
        {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "isin": "INE585B01010", "sector": "Automobile", "bse_scrip": "532500", "price": "₹12,400.00", "aliases": ["MARUTI", "SUZUKI"]},
        {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "isin": "INE238A01034", "sector": "Financial Services", "bse_scrip": "532215", "price": "₹1,230.00", "aliases": ["AXIS", "AXISBANK"]},
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd", "isin": "INE044A01036", "sector": "Pharmaceuticals", "bse_scrip": "524715", "price": "₹1,810.00", "aliases": ["SUNPHARMA", "SUN"]},
        {"symbol": "TITAN", "name": "Titan Company Ltd", "isin": "INE280A01028", "sector": "Consumer Discretionary", "bse_scrip": "500114", "price": "₹3,550.00", "aliases": ["TITAN", "TANISHQ"]},
        {"symbol": "NTPC", "name": "NTPC Ltd", "isin": "INE733E01010", "sector": "Energy & Utilities", "bse_scrip": "532555", "price": "₹420.00", "aliases": ["NTPC"]},
        {"symbol": "ONGC", "name": "Oil & Natural Gas Corp Ltd", "isin": "INE213A01029", "sector": "Energy", "bse_scrip": "500312", "price": "₹295.00", "aliases": ["ONGC"]},
        {"symbol": "POWERGRID", "name": "Power Grid Corporation of India Ltd", "isin": "INE752E01010", "sector": "Energy & Utilities", "bse_scrip": "532898", "price": "₹340.00", "aliases": ["POWERGRID", "PGCIL"]},
        {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "isin": "INE423A01024", "sector": "Conglomerate", "bse_scrip": "512599", "price": "₹3,050.00", "aliases": ["ADANIENT", "ADANI"]},
        {"symbol": "ADANIPORTS", "name": "Adani Ports and SEZ Ltd", "isin": "INE742F01042", "sector": "Infrastructure & Logistics", "bse_scrip": "532921", "price": "₹1,440.00", "aliases": ["ADANIPORTS", "APSEZ"]},
        {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "isin": "INE081A01020", "sector": "Metals & Mining", "bse_scrip": "500470", "price": "₹155.00", "aliases": ["TATASTEEL"]},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "isin": "INE481G01011", "sector": "Building Materials", "bse_scrip": "532538", "price": "₹11,400.00", "aliases": ["ULTRACEMCO", "ULTRATECH"]},
        {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd", "isin": "INE101A01026", "sector": "Automobile", "bse_scrip": "500520", "price": "₹3,020.00", "aliases": ["M&M", "MAHINDRA"]},
        {"symbol": "COALINDIA", "name": "Coal India Ltd", "isin": "INE522F01014", "sector": "Energy & Resources", "bse_scrip": "533278", "price": "₹505.00", "aliases": ["COALINDIA", "CIL"]},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "isin": "INE918I01026", "sector": "Financial Services", "bse_scrip": "532978", "price": "₹1,920.00", "aliases": ["BAJAJFINSV"]},
        {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd", "isin": "INE021A01026", "sector": "Consumer Goods", "bse_scrip": "500820", "price": "₹2,920.00", "aliases": ["ASIANPAINT"]},
        {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "isin": "INE860A01027", "sector": "Information Technology", "bse_scrip": "532281", "price": "₹1,810.00", "aliases": ["HCLTECH", "HCL"]},
        {"symbol": "WIPRO", "name": "Wipro Ltd", "isin": "INE075A01022", "sector": "Information Technology", "bse_scrip": "507685", "price": "₹545.00", "aliases": ["WIPRO"]},
        {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "isin": "INE669C01036", "sector": "Information Technology", "bse_scrip": "532755", "price": "₹1,690.00", "aliases": ["TECHM"]},
        {"symbol": "NESTLEIND", "name": "Nestle India Ltd", "isin": "INE239A01024", "sector": "Consumer Goods", "bse_scrip": "500790", "price": "₹2,490.00", "aliases": ["NESTLEIND", "NESTLE"]},
        {"symbol": "GRASIM", "name": "Grasim Industries Ltd", "isin": "INE047A01021", "sector": "Materials & Conglomerate", "bse_scrip": "500300", "price": "₹2,720.00", "aliases": ["GRASIM"]},
        {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "isin": "INE019A01038", "sector": "Metals & Mining", "bse_scrip": "500228", "price": "₹965.00", "aliases": ["JSWSTEEL", "JSW"]},
        {"symbol": "CUPID", "name": "Cupid Ltd", "isin": "INE509F01011", "sector": "Healthcare & Consumer", "bse_scrip": "530843", "price": "₹265.00", "aliases": ["CUPID"]},
        {"symbol": "NIFTYBEES", "name": "Nippon India ETF Nifty BeES", "isin": "INF732E01015", "sector": "Index ETF", "bse_scrip": "590108", "price": "₹266.50", "aliases": ["NIFTYBEES", "NIFTY ETF"]},
        {"symbol": "ZOMATO", "name": "Zomato Ltd", "isin": "INE758T01015", "sector": "Internet & E-Commerce", "bse_scrip": "543320", "price": "₹280.40", "aliases": ["ZOMATO", "BLINKIT"]},
        {"symbol": "JIOFIN", "name": "Jio Financial Services Ltd", "isin": "INE758E01017", "sector": "Financial Services", "bse_scrip": "543940", "price": "₹342.10", "aliases": ["JIOFIN", "JFS"]},
        {"symbol": "TRENT", "name": "Trent Ltd (Tata Retail)", "isin": "INE849A01020", "sector": "Retail & Apparel", "bse_scrip": "500251", "price": "₹7,380.00", "aliases": ["TRENT", "ZUDIO", "WESTSIDE"]},
        {"symbol": "SUZLON", "name": "Suzlon Energy Ltd", "isin": "INE040H01021", "sector": "Renewable Energy", "bse_scrip": "532667", "price": "₹78.50", "aliases": ["SUZLON", "SUZLON ENERGY"]},
    ],
    "events": [
        {"id": "evt-lt-001", "symbol": "LT", "headline": "Won Mega EPC order worth Rs 4,500 Crore in Middle East", "event_type": "ORDER_WIN", "importance": "HIGH"},
        {"id": "evt-tcs-001", "symbol": "TCS", "headline": "Declared Rs 77.00 per share dividend on Q3 net profit", "event_type": "DIVIDEND", "importance": "MEDIUM"},
        {"id": "evt-ril-001", "symbol": "RELIANCE", "headline": "Reliance Green Energy commissions phase-1 gigafactory unit for solar PV module fabrication", "event_type": "CAPEX", "importance": "HIGH"},
        {"id": "evt-tatamtr-001", "symbol": "TATAMOTORS", "headline": "Board approves demerger into two separate listed companies", "event_type": "MNA", "importance": "CRITICAL"},
        {"id": "evt-bharti-001", "symbol": "BHARTIARTL", "headline": "Bharti Airtel expands 5G enterprise contracts and tariff re-rating trajectory", "event_type": "TARIFF_HIKE", "importance": "HIGH"},
        {"id": "evt-asahi-001", "symbol": "ASAHIINDIA", "headline": "Asahi India Glass (AIGL) secures long-term OEM supply agreements for solar & automotive glass", "event_type": "ORDER_WIN", "importance": "HIGH"},
    ],
    "sectors": [
        {"name": "Infrastructure & Capital Goods", "code": "INFRA", "top_symbol": "LT"},
        {"name": "Information Technology", "code": "IT", "top_symbol": "TCS"},
        {"name": "Banking & Financial Services", "code": "BANK", "top_symbol": "HDFCBANK"},
        {"name": "Automotive & EV", "code": "AUTO", "top_symbol": "TATAMOTORS"},
        {"name": "Oil, Gas & Petrochemicals", "code": "ENERGY", "top_symbol": "RELIANCE"},
        {"name": "Telecommunications", "code": "TELECOM", "top_symbol": "BHARTIARTL"},
        {"name": "Auto Ancillaries & Glass", "code": "AUTO_ANC", "top_symbol": "ASAHIINDIA"},
    ],
}


@router.get("")
async def search_all(
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(20, ge=1, le=100),
):
    """Global search returning matching companies, events, and sectors."""
    query = q.strip().lower()
    terms = query.split()

    matched_companies = []
    for c in SEARCH_INDEX["companies"]:
        # Build searchable string including aliases
        aliases_str = " ".join(c.get("aliases", []))
        searchable = f"{c['symbol']} {c['name']} {c['isin']} {c['sector']} {c['bse_scrip']} {aliases_str}".lower()
        
        # Check exact symbol match or term match
        is_direct_match = any(query == a.lower() for a in [c["symbol"]] + c.get("aliases", []))
        if is_direct_match or all(term in searchable for term in terms):
            entry = dict(c)
            if query in [a.lower() for a in c.get("aliases", [])] and query != c["symbol"].lower():
                entry["match_note"] = f"Matched alias '{q.upper()}'"
            matched_companies.append(entry)

    matched_events = []
    for e in SEARCH_INDEX["events"]:
        searchable = f"{e['symbol']} {e['headline']} {e['event_type']} {e['importance']}".lower()
        if all(term in searchable for term in terms):
            matched_events.append(e)

    matched_sectors = []
    for s in SEARCH_INDEX["sectors"]:
        searchable = f"{s['name']} {s['code']} {s['top_symbol']}".lower()
        if any(term in searchable for term in terms):
            matched_sectors.append(s)

    lim = limit if isinstance(limit, int) else 20
    total_results = len(matched_companies) + len(matched_events) + len(matched_sectors)

    return {
        "status": "ok",
        "query": q,
        "total_results": total_results,
        "results": {
            "companies": matched_companies[:lim],
            "events": matched_events[:lim],
            "sectors": matched_sectors[:lim],
        }
    }
