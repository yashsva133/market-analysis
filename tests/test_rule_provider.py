"""Tests for deterministic RuleProvider fact extraction and classification."""
import asyncio
from packages.ai.rule_provider import RuleProvider
from packages.schemas.taxonomy import EventTaxonomy


def test_rule_provider_order_win_crores():
    async def _run():
        provider = RuleProvider()
        headline = "L&T Construction bags Mega order worth ₹850 Cr for high-speed electrification"
        resp = await provider.complete(headline)

        assert resp.parsed_json is not None
        assert resp.parsed_json["event_type"] == EventTaxonomy.ORDER_WIN.value
        # 850 Cr = 8,500,000,000 INR
        assert resp.parsed_json["amount"] == 8500000000.0
        assert resp.parsed_json["is_binding"] is True

    asyncio.run(_run())


def test_rule_provider_insolvency():
    async def _run():
        provider = RuleProvider()
        headline = "National Company Law Tribunal (NCLT) initiates CIRP proceedings under IBC against Company"
        resp = await provider.complete(headline)

        assert resp.parsed_json is not None
        assert resp.parsed_json["event_type"] == EventTaxonomy.INSOLVENCY.value

    asyncio.run(_run())


def test_rule_provider_mou_non_binding():
    async def _run():
        provider = RuleProvider()
        headline = "Company signs non-binding MoU with Global Partner for exploratory green hydrogen study"
        resp = await provider.complete(headline)

        assert resp.parsed_json is not None
        assert resp.parsed_json["event_type"] == EventTaxonomy.MOU.value
        assert resp.parsed_json["is_binding"] is False

    asyncio.run(_run())
