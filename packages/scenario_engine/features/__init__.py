"""Unified Feature Engineering Suite for India Market Scenario Engine.

Combines 10 feature domains:
1. Price features
2. Technical features
3. Volume features
4. Fundamental features
5. Valuation features
6. Event features
7. Sentiment features
8. Market regime features
9. Sector features
10. Portfolio features
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .price_features import PriceFeatureExtractor
from .technical_features import TechnicalFeatureExtractor
from .volume_features import VolumeFeatureExtractor
from .fundamental_features import FundamentalFeatureExtractor
from .valuation_features import ValuationFeatureExtractor
from .event_features import EventFeatureExtractor
from .sentiment_features import SentimentFeatureExtractor
from .market_regime_features import MarketRegimeFeatureExtractor
from .sector_features import SectorFeatureExtractor
from .portfolio_features import PortfolioFeatureExtractor


class FeatureSnapshotEngine:
    FEATURE_SET_VERSION = "2.0.0"

    @classmethod
    def build_snapshot(
        cls,
        symbol: str,
        prices: List[float],
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None,
        volumes: Optional[List[float]] = None,
        financial_snapshot: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        news_items: Optional[List[Dict[str, Any]]] = None,
        regime_data: Optional[Dict[str, Any]] = None,
        sector_name: Optional[str] = None,
        portfolio_context: Optional[Dict[str, Any]] = None,
        as_of: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate point-in-time quantitative feature vector with reproducible snapshot hash."""
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        # 1. Price features
        price_feat = PriceFeatureExtractor.extract(prices, highs, lows)

        # 2. Technical features
        tech_feat = TechnicalFeatureExtractor.extract(prices, highs, lows, volumes)

        # 3. Volume features
        vol_feat = VolumeFeatureExtractor.extract(volumes or [], prices)

        # 4. Fundamental features
        fund_feat = FundamentalFeatureExtractor.extract(financial_snapshot)

        # 5. Valuation features
        val_feat = ValuationFeatureExtractor.extract(financial_snapshot)

        # 6. Event features
        event_feat = EventFeatureExtractor.extract(events or [], as_of=as_of)

        # 7. Sentiment features
        sent_feat = SentimentFeatureExtractor.extract(news_items or [])

        # 8. Market regime features
        regime_feat = MarketRegimeFeatureExtractor.extract(regime_data)

        # 9. Sector features
        sec_feat = SectorFeatureExtractor.extract(
            sector_name=sector_name or "Capital Goods",
            stock_return_20d=price_feat.get("return_20d", 0.0),
        )

        # 10. Portfolio features
        port_feat = PortfolioFeatureExtractor.extract(
            symbol=symbol,
            portfolio_context=portfolio_context,
        )

        # Merge all into single flat features dictionary
        all_features = {}
        for d in [
            price_feat,
            tech_feat,
            vol_feat,
            fund_feat,
            val_feat,
            event_feat,
            sent_feat,
            regime_feat,
            sec_feat,
            port_feat,
        ]:
            all_features.update(d)

        # Compute deterministic snapshot hash
        feature_repr = json.dumps(all_features, sort_keys=True)
        snapshot_id = hashlib.sha256(
            f"{symbol}_{cls.FEATURE_SET_VERSION}_{as_of.date()}_{feature_repr}".encode()
        ).hexdigest()[:16]

        return {
            "feature_snapshot_id": f"snap_{snapshot_id}",
            "symbol": symbol.upper(),
            "feature_set_version": cls.FEATURE_SET_VERSION,
            "as_of": as_of.isoformat(),
            "feature_count": len(all_features),
            "features": all_features,
            "feature_domains": {
                "price": price_feat,
                "technical": tech_feat,
                "volume": vol_feat,
                "fundamental": fund_feat,
                "valuation": val_feat,
                "events": event_feat,
                "sentiment": sent_feat,
                "market_regime": regime_feat,
                "sector": sec_feat,
                "portfolio": port_feat,
            },
        }


__all__ = [
    "FeatureSnapshotEngine",
    "PriceFeatureExtractor",
    "TechnicalFeatureExtractor",
    "VolumeFeatureExtractor",
    "FundamentalFeatureExtractor",
    "ValuationFeatureExtractor",
    "EventFeatureExtractor",
    "SentimentFeatureExtractor",
    "MarketRegimeFeatureExtractor",
    "SectorFeatureExtractor",
    "PortfolioFeatureExtractor",
]
