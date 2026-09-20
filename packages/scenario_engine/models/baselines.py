"""Deterministic Baseline Forecast Models for Time-Series & Scenarios.

Every advanced model must be benchmarked against these 4 mandatory baselines:
1. Random Walk Baseline (Geometric Brownian Motion)
2. Zero-Return Baseline (drift=0, variance=empirical)
3. Historical Return Distribution (Empirical Bootstrap)
4. Volatility-Adjusted Baseline (Recent ATR / Realized Volatility scaled)
"""
from typing import List, Dict, Any
import numpy as np


class BaselineForecastModels:
    @staticmethod
    def random_walk_forecast(
        current_price: float,
        daily_volatility: float,
        horizon_days: int,
        num_simulations: int = 1000,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """Geometric Brownian motion with 0 drift and empirical daily volatility."""
        np.random.seed(random_seed)
        dt = 1.0
        shocks = np.random.normal(0, daily_volatility, (num_simulations, horizon_days))
        price_paths = current_price * np.cumprod(1.0 + shocks, axis=1)
        final_prices = price_paths[:, -1]

        quantiles = {
            "q10": float(np.percentile(final_prices, 10)),
            "q25": float(np.percentile(final_prices, 25)),
            "q50": float(np.percentile(final_prices, 50)),
            "q75": float(np.percentile(final_prices, 75)),
            "q90": float(np.percentile(final_prices, 90)),
        }
        return {
            "baseline_type": "RANDOM_WALK",
            "horizon_days": horizon_days,
            "quantiles": quantiles,
            "mean_terminal_price": float(np.mean(final_prices)),
            "terminal_std": float(np.std(final_prices)),
        }

    @staticmethod
    def zero_return_baseline(
        current_price: float,
        daily_volatility: float,
        horizon_days: int,
    ) -> Dict[str, Any]:
        """Expected return is strictly 0; uncertainty spreads by sqrt(t)."""
        sqrt_t_vol = daily_volatility * np.sqrt(horizon_days)
        return {
            "baseline_type": "ZERO_RETURN",
            "horizon_days": horizon_days,
            "quantiles": {
                "q10": float(round(current_price * (1.0 - 1.282 * sqrt_t_vol), 2)),
                "q25": float(round(current_price * (1.0 - 0.674 * sqrt_t_vol), 2)),
                "q50": float(round(current_price, 2)),
                "q75": float(round(current_price * (1.0 + 0.674 * sqrt_t_vol), 2)),
                "q90": float(round(current_price * (1.0 + 1.282 * sqrt_t_vol), 2)),
            },
            "mean_terminal_price": current_price,
        }

    @staticmethod
    def historical_distribution_baseline(
        current_price: float,
        historical_prices: List[float],
        horizon_days: int,
    ) -> Dict[str, Any]:
        """Empirical distribution of N-day rolling returns over historical sample."""
        p = np.array(historical_prices, dtype=float)
        if len(p) <= horizon_days:
            return BaselineForecastModels.zero_return_baseline(current_price, 0.015, horizon_days)

        rolling_returns = (p[horizon_days:] - p[:-horizon_days]) / p[:-horizon_days]
        if len(rolling_returns) == 0:
            return BaselineForecastModels.zero_return_baseline(current_price, 0.015, horizon_days)

        q10_ret = float(np.percentile(rolling_returns, 10))
        q25_ret = float(np.percentile(rolling_returns, 25))
        q50_ret = float(np.percentile(rolling_returns, 50))
        q75_ret = float(np.percentile(rolling_returns, 75))
        q90_ret = float(np.percentile(rolling_returns, 90))

        return {
            "baseline_type": "HISTORICAL_DISTRIBUTION",
            "horizon_days": horizon_days,
            "sample_size": len(rolling_returns),
            "quantiles": {
                "q10": float(round(current_price * (1.0 + q10_ret), 2)),
                "q25": float(round(current_price * (1.0 + q25_ret), 2)),
                "q50": float(round(current_price * (1.0 + q50_ret), 2)),
                "q75": float(round(current_price * (1.0 + q75_ret), 2)),
                "q90": float(round(current_price * (1.0 + q90_ret), 2)),
            },
            "median_return_pct": float(round(q50_ret * 100, 2)),
        }

    @staticmethod
    def volatility_adjusted_baseline(
        current_price: float,
        recent_prices: List[float],
        horizon_days: int,
    ) -> Dict[str, Any]:
        """Volatility-adjusted baseline incorporating recent 20-day realized volatility clustering."""
        p = np.array(recent_prices, dtype=float)
        if len(p) >= 20:
            daily_returns = np.diff(p[-21:]) / p[-21:-1]
            daily_vol = float(np.std(daily_returns))
        else:
            daily_vol = 0.015

        horizon_vol = daily_vol * np.sqrt(horizon_days)
        return {
            "baseline_type": "VOLATILITY_ADJUSTED",
            "horizon_days": horizon_days,
            "horizon_volatility_pct": float(round(horizon_vol * 100, 2)),
            "quantiles": {
                "q10": float(round(current_price * (1.0 - 1.282 * horizon_vol), 2)),
                "q25": float(round(current_price * (1.0 - 0.674 * horizon_vol), 2)),
                "q50": float(round(current_price, 2)),
                "q75": float(round(current_price * (1.0 + 0.674 * horizon_vol), 2)),
                "q90": float(round(current_price * (1.0 + 1.282 * horizon_vol), 2)),
            },
        }
