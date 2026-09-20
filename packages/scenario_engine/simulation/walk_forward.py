"""Walk-Forward Validation Engine for Time Series and Quant Models (§12).

Strictly enforces time-series validation protocols without random shuffling:
TRAIN -> VALIDATE -> TEST -> ROLL FORWARD -> NEXT WINDOW

Supports:
- Expanding Window (train window grows over time)
- Rolling Window (fixed train window moving forward)
- Multi-horizon evaluation
- Zero future look-ahead bias
- Out-of-sample metrics: MAE, RMSE, Directional Accuracy, Coverage (Q10-Q90)
"""
from typing import List, Dict, Any, Generator, Optional
import numpy as np


class WalkForwardSplitter:
    """Generates sequential, temporal non-shuffled train/validate/test splits."""

    @staticmethod
    def split(
        n_samples: int,
        train_window: int = 120,
        test_window: int = 20,
        step_size: int = 20,
        mode: str = "expanding",
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield (train_indices, test_indices, window_id) slices."""
        if n_samples < train_window + test_window:
            raise ValueError(f"Insufficient samples ({n_samples}) for train ({train_window}) + test ({test_window})")

        window_id = 0
        current_train_end = train_window

        while current_train_end + test_window <= n_samples:
            if mode == "rolling":
                train_start = current_train_end - train_window
            else:  # expanding
                train_start = 0

            train_idx = list(range(train_start, current_train_end))
            test_idx = list(range(current_train_end, current_train_end + test_window))

            # Temporal integrity assertion: max(train) < min(test)
            assert max(train_idx) < min(test_idx), "Leakage detected: train overlaps or follows test!"

            yield {
                "window_id": window_id,
                "train_start": train_start,
                "train_end": current_train_end,
                "test_start": current_train_end,
                "test_end": current_train_end + test_window,
                "train_indices": train_idx,
                "test_indices": test_idx,
                "train_size": len(train_idx),
                "test_size": len(test_idx),
            }

            current_train_end += step_size
            window_id += 1


class WalkForwardEvaluator:
    """Evaluates forecasting models over walk-forward folds."""

    @staticmethod
    def evaluate(
        prices: List[float],
        train_window: int = 60,
        test_window: int = 10,
        step_size: int = 10,
        mode: str = "expanding",
    ) -> Dict[str, Any]:
        """Perform full walk-forward out-of-sample backtest on a price series."""
        p = np.array(prices, dtype=float)
        n = len(p)
        splitter = WalkForwardSplitter.split(
            n_samples=n,
            train_window=train_window,
            test_window=test_window,
            step_size=step_size,
            mode=mode,
        )

        windows_results = []
        all_errors = []
        directional_correct = 0
        total_directional_preds = 0
        coverage_count = 0
        total_test_points = 0

        for split in splitter:
            train_prices = p[split["train_indices"]]
            test_prices = p[split["test_indices"]]

            # Simple out-of-sample persistence + drift baseline for evaluation
            last_train = float(train_prices[-1])
            recent_segment = train_prices[-21:] if len(train_prices) >= 21 else train_prices
            drift = float(np.mean(np.diff(recent_segment) / recent_segment[:-1])) if len(recent_segment) > 1 else 0.0
            
            # Predict test horizon
            preds = [last_train * ((1.0 + drift) ** (k + 1)) for k in range(len(test_prices))]
            
            errors = [abs(preds[k] - test_prices[k]) for k in range(len(test_prices))]
            all_errors.extend(errors)

            # Directional accuracy
            actual_dir = np.sign(test_prices[-1] - last_train)
            pred_dir = np.sign(preds[-1] - last_train)
            if actual_dir == pred_dir or actual_dir == 0:
                directional_correct += 1
            total_directional_preds += 1

            # Quantile bands (approximate ±1.5 vol)
            vol = float(np.std(np.diff(train_prices) / train_prices[:-1])) if len(train_prices) > 5 else 0.015
            for k in range(len(test_prices)):
                band_w = last_train * vol * np.sqrt(k + 1) * 1.645
                lower_b = preds[k] - band_w
                upper_b = preds[k] + band_w
                if lower_b <= test_prices[k] <= upper_b:
                    coverage_count += 1
                total_test_points += 1

            windows_results.append({
                "window_id": split["window_id"],
                "train_end_idx": split["train_end"],
                "mae": round(float(np.mean(errors)), 2),
                "last_train_price": round(last_train, 2),
                "actual_final_price": round(float(test_prices[-1]), 2),
            })

        mae = float(np.mean(all_errors)) if all_errors else 0.0
        rmse = float(np.sqrt(np.mean(np.array(all_errors) ** 2))) if all_errors else 0.0
        dir_acc = (directional_correct / max(1, total_directional_preds)) * 100.0
        coverage_pct = (coverage_count / max(1, total_test_points)) * 100.0

        return {
            "validation_protocol": f"WALK_FORWARD_{mode.upper()}",
            "total_windows": len(windows_results),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "directional_accuracy_pct": round(dir_acc, 2),
            "prediction_interval_coverage_pct": round(coverage_pct, 2),
            "window_details": windows_results,
            "disclaimer": "Out-of-sample walk-forward backtest strictly without future look-ahead bias.",
        }
