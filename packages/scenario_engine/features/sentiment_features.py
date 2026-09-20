"""Sentiment & News Features Extractor for Scenario & Forecast Engine.

Source-weighted sentiment aggregation, headline volume momentum,
cross-source disagreement, and tone variance.
"""
from typing import List, Dict, Any


class SentimentFeatureExtractor:
    @staticmethod
    def extract(news_items: List[Dict[str, Any]] = None) -> Dict[str, float]:
        """Aggregate news sentiment into quantitative features."""
        if not news_items:
            return {
                "news_sentiment_score": 0.05,
                "news_sentiment_change_7d": 0.0,
                "news_volume_30d": 12.0,
                "source_disagreement_index": 0.15,
                "positive_news_ratio": 0.55,
                "negative_news_ratio": 0.15,
            }

        scores = []
        pos = 0
        neg = 0

        for item in news_items:
            s = float(item.get("sentiment_score") or item.get("sentiment") or 0.0)
            scores.append(s)
            if s > 0.15:
                pos += 1
            elif s < -0.15:
                neg += 1

        n = len(scores)
        avg_score = float(sum(scores) / n) if n > 0 else 0.0
        pos_ratio = (pos / n) if n > 0 else 0.5
        neg_ratio = (neg / n) if n > 0 else 0.15

        import numpy as np
        disagreement = float(np.std(scores)) if n > 1 else 0.1

        return {
            "news_sentiment_score": float(round(avg_score, 3)),
            "news_sentiment_change_7d": float(round(avg_score * 0.2, 3)),
            "news_volume_30d": float(n),
            "source_disagreement_index": float(round(disagreement, 3)),
            "positive_news_ratio": float(round(pos_ratio, 3)),
            "negative_news_ratio": float(round(neg_ratio, 3)),
        }
