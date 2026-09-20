"""Configurable Transaction Costs Model for Indian Equity Markets.

Calculates realistic Indian regulatory and exchange turnover charges:
- Securities Transaction Tax (STT: 0.1% on delivery buy/sell)
- Exchange Turnover Charges (NSE: 0.00297%, BSE: 0.00375%)
- SEBI Turnover Charges (Rs 10 per Crore = 0.0001%)
- Stamp Duty (0.015% on buy delivery)
- Brokerage (Configurable flat Rs 20 or 0.05%)
- GST (18% on brokerage + exchange charges + SEBI charges)
- Slippage assumption (Configurable 0.05%)
"""
from typing import Dict, Any, Optional
from datetime import date


# Verified Indian Statutory & Regulatory Rate Schedule (§19)
DEFAULT_COST_SCHEDULE = {
    "effective_from": "2024-10-01",
    "effective_to": "OPEN",
    "source": "SEBI Circular / Finance Act 2024 / NSE Circular",
    "notes": "Cash delivery equity statutory charges for retail Indian markets",
    "rates": {
        "stt_delivery_buy": 0.001,           # 0.1% on buy delivery
        "stt_delivery_sell": 0.001,          # 0.1% on sell delivery
        "exchange_turnover_nse": 0.0000297,  # NSE cash delivery turnover fee
        "exchange_turnover_bse": 0.0000375,  # BSE cash delivery turnover fee
        "sebi_turnover": 0.000001,           # SEBI fee ₹10 per crore
        "stamp_duty_buy": 0.00015,           # 0.015% on buy delivery only
        "gst_rate": 0.18,                    # 18% GST on (brokerage + exchange + SEBI)
        "default_brokerage_pct": 0.0005,     # 0.05% discount broker rate
        "default_brokerage_flat_cap": 20.0,  # ₹20 maximum cap per order
        "default_slippage_pct": 0.0005,      # 5 bps execution slippage assumption
    }
}


class TransactionCostModel:
    def __init__(
        self,
        stt_rate: Optional[float] = None,
        exchange_turnover_rate: Optional[float] = None,
        sebi_turnover_rate: Optional[float] = None,
        stamp_duty_buy_rate: Optional[float] = None,
        brokerage_pct: Optional[float] = None,
        brokerage_flat_cap: Optional[float] = None,
        gst_rate: Optional[float] = None,
        slippage_pct: Optional[float] = None,
        schedule: Optional[Dict[str, Any]] = None,
    ):
        rates = (schedule or DEFAULT_COST_SCHEDULE)["rates"]
        self.schedule_metadata = {
            "effective_from": (schedule or DEFAULT_COST_SCHEDULE).get("effective_from", "2024-10-01"),
            "effective_to": (schedule or DEFAULT_COST_SCHEDULE).get("effective_to", "OPEN"),
            "source": (schedule or DEFAULT_COST_SCHEDULE).get("source", "SEBI / Exchange Circulars"),
        }
        self.stt_rate = stt_rate if stt_rate is not None else rates["stt_delivery_buy"]
        self.stt_sell_rate = rates.get("stt_delivery_sell", 0.001)
        self.exchange_turnover_rate = exchange_turnover_rate if exchange_turnover_rate is not None else rates["exchange_turnover_nse"]
        self.sebi_turnover_rate = sebi_turnover_rate if sebi_turnover_rate is not None else rates["sebi_turnover"]
        self.stamp_duty_buy_rate = stamp_duty_buy_rate if stamp_duty_buy_rate is not None else rates["stamp_duty_buy"]
        self.brokerage_pct = brokerage_pct if brokerage_pct is not None else rates["default_brokerage_pct"]
        self.brokerage_flat_cap = brokerage_flat_cap if brokerage_flat_cap is not None else rates["default_brokerage_flat_cap"]
        self.gst_rate = gst_rate if gst_rate is not None else rates["gst_rate"]
        self.slippage_pct = slippage_pct if slippage_pct is not None else rates["default_slippage_pct"]

    def estimate_buy_costs(self, notional: float) -> Dict[str, float]:
        """Compute estimated buy-side statutory and transaction fees."""
        if notional <= 0:
            return {"total_cost": 0.0, "total_estimated_cost": 0.0, "cost_pct": 0.0}

        brokerage = min(notional * self.brokerage_pct, self.brokerage_flat_cap)
        stt = notional * self.stt_rate
        exchange_turnover = notional * self.exchange_turnover_rate
        sebi_charges = notional * self.sebi_turnover_rate
        stamp_duty = notional * self.stamp_duty_buy_rate
        gst = (brokerage + exchange_turnover + sebi_charges) * self.gst_rate
        slippage = notional * self.slippage_pct

        total = brokerage + stt + exchange_turnover + sebi_charges + stamp_duty + gst + slippage

        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "exchange_turnover": round(exchange_turnover, 2),
            "sebi_charges": round(sebi_charges, 2),
            "stamp_duty": round(stamp_duty, 2),
            "gst": round(gst, 2),
            "slippage": round(slippage, 2),
            "total_estimated_cost": round(total, 2),
            "total_cost": round(total, 2),
            "cost_pct": round((total / notional) * 100, 3),
            "effective_from": self.schedule_metadata["effective_from"],
            "source": self.schedule_metadata["source"],
        }

    def estimate_sell_costs(self, notional: float) -> Dict[str, float]:
        """Compute estimated sell-side statutory and transaction fees (no stamp duty)."""
        if notional <= 0:
            return {"total_cost": 0.0, "total_estimated_cost": 0.0, "cost_pct": 0.0}

        brokerage = min(notional * self.brokerage_pct, self.brokerage_flat_cap)
        stt = notional * self.stt_sell_rate
        exchange_turnover = notional * self.exchange_turnover_rate
        sebi_charges = notional * self.sebi_turnover_rate
        stamp_duty = 0.0  # Stamp duty applies only on buy delivery in India
        gst = (brokerage + exchange_turnover + sebi_charges) * self.gst_rate
        slippage = notional * self.slippage_pct

        total = brokerage + stt + exchange_turnover + sebi_charges + stamp_duty + gst + slippage

        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "exchange_turnover": round(exchange_turnover, 2),
            "sebi_charges": round(sebi_charges, 2),
            "stamp_duty": 0.0,
            "gst": round(gst, 2),
            "slippage": round(slippage, 2),
            "total_estimated_cost": round(total, 2),
            "total_cost": round(total, 2),
            "cost_pct": round((total / notional) * 100, 3),
        }

    def estimate_roundtrip_costs(self, buy_notional: float, sell_notional: float) -> Dict[str, float]:
        """Compute total round-trip entry and exit costs."""
        buy = self.estimate_buy_costs(buy_notional)
        sell = self.estimate_sell_costs(sell_notional)
        total = buy["total_estimated_cost"] + sell["total_estimated_cost"]
        total_notional = buy_notional + sell_notional
        return {
            "buy_costs": buy,
            "sell_costs": sell,
            "total_roundtrip_cost": round(total, 2),
            "roundtrip_cost_pct": round((total / total_notional) * 100, 3) if total_notional > 0 else 0.0,
        }

