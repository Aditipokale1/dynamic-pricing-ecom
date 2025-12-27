# src/pricing/rules.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Context:
    sku: str
    segment: str
    unit_cost: float
    msrp: Optional[float]
    map_price: Optional[float]
    yesterday_price: Optional[float]
    competitor_price: Optional[float]
    is_kvi: bool
    promo_active: bool
    promo_price: Optional[float]
    days_of_cover: Optional[float]
    # later phases will populate this (used for weekly volatility checks)
    recent_prices: Optional[List[float]] = None


@dataclass
class RuleResult:
    final_price: float
    reasons: List[str]


def clamp(value: float, lo: Optional[float], hi: Optional[float]) -> float:
    if lo is not None and value < lo:
        value = lo
    if hi is not None and value > hi:
        value = hi
    return value


def apply_guardrails(candidate_price: float, ctx: Context, policy: dict) -> RuleResult:
    """
    Apply business guardrails to a candidate price and return:
      - final_price (float)
      - reasons (list of reason codes explaining adjustments)
    """
    reasons: List[str] = []
    p = float(candidate_price)

    if p <= 0:
        raise ValueError("candidate_price must be > 0")

    # 1) Promo lock
    promo_cfg = policy["guardrails"]["promo"]
    if promo_cfg["enabled"] and ctx.promo_active:
        if ctx.promo_price is None:
            raise ValueError("promo_active=True but promo_price is None")
        return RuleResult(final_price=float(ctx.promo_price), reasons=["PROMO_LOCK"])

    # 2) Price floor (cost + margin)
    floor_cfg = policy["guardrails"]["price_floor"]
    if floor_cfg["enabled"]:
        min_margin = float(floor_cfg["min_margin_pct"])
        floor = float(ctx.unit_cost) * (1.0 + min_margin)
        if p < floor:
            p = floor
            reasons.append("MARGIN_FLOOR_APPLIED")

    # 3) Ceiling (MSRP) + MAP enforcement
    ceil_cfg = policy["guardrails"]["price_ceiling"]

    # MAP acts like an additional floor
    if ceil_cfg["enabled"] and ceil_cfg.get("enforce_map", False) and ctx.map_price is not None:
        if p < float(ctx.map_price):
            p = float(ctx.map_price)
            reasons.append("MAP_FLOOR_APPLIED")

    # MSRP acts like a ceiling
    if ceil_cfg["enabled"] and ctx.msrp is not None:
        msrp = float(ctx.msrp)
        if p > msrp:
            p = msrp
            reasons.append("MSRP_CEILING_APPLIED")

    # 4) Max daily price move (inventory-aware)
    change_cfg = policy["guardrails"]["max_daily_change"]
    if change_cfg["enabled"] and ctx.yesterday_price is not None:
        y = float(ctx.yesterday_price)

        low_stock = (
            ctx.days_of_cover is not None
            and ctx.days_of_cover < policy["inventory_flags"]["low_stock_days_of_cover_lt"]
        )
        overstock = (
            ctx.days_of_cover is not None
            and ctx.days_of_cover > policy["inventory_flags"]["overstock_days_of_cover_gt"]
        )

        up_pct = float(change_cfg["default_pct"])
        down_pct = float(change_cfg["default_pct"])

        if low_stock:
            up_pct = down_pct = float(change_cfg["low_stock_pct"])
        elif overstock:
            # allow bigger downward change only
            down_pct = float(change_cfg["overstock_pct"])

        min_p = y * (1.0 - down_pct)
        max_p = y * (1.0 + up_pct)

        p2 = clamp(p, lo=min_p, hi=max_p)
        if p2 != p:
            reasons.append("MAX_DAILY_CHANGE_CLAMPED")
        p = p2

    # 5) Competitor cap (KVI only)
    comp_cfg = policy["guardrails"]["competitor"]
    if comp_cfg["enabled"] and ctx.is_kvi and ctx.competitor_price is not None:
        cap = float(ctx.competitor_price) * (1.0 + float(comp_cfg["max_over_competitor_pct"]))
        if p > cap:
            p = cap
            reasons.append("COMPETITOR_CAP_APPLIED")

    # 6) Trust constraint (weekly volatility) — placeholder for later phases
    trust_cfg = policy["guardrails"]["trust"]
    if trust_cfg["enabled"] and ctx.recent_prices:
        # Implement in later phases when you have reliable historical price series
        # Example future reason: "TRUST_VOLATILITY_LIMIT_APPLIED"
        pass

    if p <= 0:
        raise ValueError("Final price must be > 0")

    return RuleResult(final_price=float(p), reasons=reasons)
