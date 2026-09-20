"""Tests for Dynamic Universe Manager: ISIN deduplication, change detection, and multi-exchange mappings."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from packages.common.models import Company, Security, UniverseChangeEvent
from services.collector.universe_manager import UniverseManager


@pytest.mark.asyncio
async def test_dual_exchange_isin_deduplication():
    """Verify that one company appearing on both exchanges maps to one company identity with multiple securities."""
    manager = UniverseManager()

    # Shared ISIN on both NSE and BSE
    nse_data = [
        {
            "isin": "INE002A01018",
            "symbol": "RELIANCE",
            "legal_name": "Reliance Industries Limited",
            "series": "EQ",
            "security_type": "EQUITY",
            "is_active": True,
        }
    ]
    bse_data = [
        {
            "isin": "INE002A01018",
            "symbol": "RELIANCE",
            "bse_scrip_code": "500325",
            "legal_name": "Reliance Industries Limited",
            "series": "A",
            "security_type": "EQUITY",
            "is_active": True,
        }
    ]

    added_objects = []
    
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_res)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    def mock_add(obj):
        added_objects.append(obj)
        if isinstance(obj, Company) and not getattr(obj, "id", None):
            import uuid
            obj.id = uuid.uuid4()

    mock_session.add = MagicMock(side_effect=mock_add)

    stats = await manager.refresh_universe(mock_session, custom_nse=nse_data, custom_bse=bse_data)

    assert stats["created_companies"] == 1
    assert stats["created_securities"] == 2
    assert stats["new_listings"] == 2

    # 1 Company should be created
    companies = [o for o in added_objects if isinstance(o, Company)]
    assert len(companies) == 1
    assert companies[0].isin == "INE002A01018"
    assert companies[0].legal_name == "Reliance Industries Limited"

    # 2 Securities should be created (NSE + BSE)
    securities = [o for o in added_objects if isinstance(o, Security)]
    assert len(securities) == 2
    exchanges = {s.exchange for s in securities}
    assert exchanges == {"NSE", "BSE"}

    # Both securities must point to the single Company ID
    for s in securities:
        assert s.company_id == companies[0].id

    # Check Upstox key mapped
    nse_sec = next(s for s in securities if s.exchange == "NSE")
    bse_sec = next(s for s in securities if s.exchange == "BSE")
    assert nse_sec.upstox_instrument_key == "NSE_EQ|INE002A01018"
    assert bse_sec.upstox_instrument_key == "BSE_EQ|INE002A01018"

    # Check UniverseChangeEvent records created
    change_events = [o for o in added_objects if isinstance(o, UniverseChangeEvent)]
    assert len(change_events) == 2
    for ev in change_events:
        assert ev.change_type == "NEW_LISTING"
        assert ev.isin == "INE002A01018"


@pytest.mark.asyncio
async def test_symbol_change_detection():
    """Verify that when a company changes its trading symbol, UniverseChangeEvent and alias are created."""
    manager = UniverseManager()
    import uuid

    comp_id = uuid.uuid4()
    existing_company = Company(
        id=comp_id,
        isin="INE123A01010",
        legal_name="Tata Motors Limited",
        status="ACTIVE",
    )
    existing_security = Security(
        id=uuid.uuid4(),
        company_id=comp_id,
        exchange="NSE",
        symbol="TATAMOTORS_OLD",
        is_active=True,
    )

    nse_data = [
        {
            "isin": "INE123A01010",
            "symbol": "TATAMOTORS_NEW",
            "legal_name": "Tata Motors Limited",
            "series": "EQ",
            "security_type": "EQUITY",
            "is_active": True,
        }
    ]

    added_objects = []
    mock_session = AsyncMock()

    async def mock_execute(query):
        res = MagicMock()
        q_str = str(query)
        if "pg_advisory_xact_lock" in q_str:
            return res
        if "companies" in q_str:
            # Bulk company load: existing ISIN identity is returned
            res.scalars.return_value.all.return_value = [existing_company]
        elif "securities" in q_str:
            # Bulk security load: previous symbol listing is returned
            res.scalars.return_value.all.return_value = [existing_security]
        else:
            res.scalars.return_value.all.return_value = []
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    stats = await manager.refresh_universe(mock_session, custom_nse=nse_data, custom_bse=[])

    assert stats["symbol_changes"] == 1
    # Old security marked inactive
    assert existing_security.is_active is False

    # Event emitted
    change_events = [o for o in added_objects if isinstance(o, UniverseChangeEvent)]
    symbol_changes = [e for e in change_events if e.change_type == "SYMBOL_CHANGE"]
    assert len(symbol_changes) == 1
    assert symbol_changes[0].details["previous_symbol"] == "TATAMOTORS_OLD"
    assert symbol_changes[0].details["new_symbol"] == "TATAMOTORS_NEW"

