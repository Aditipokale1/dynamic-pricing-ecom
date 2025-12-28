# src/pricing/demo_run.py
import yaml

from src.pricing.rules import Context, apply_guardrails


def load_policy(path: str = "src/config/pricing_policy.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    policy = load_policy()

    ctx = Context(
        sku="ELEC-001",
        segment="new",
        unit_cost=50.0,
        msrp=120.0,
        map_price=79.99,
        yesterday_price=99.99,
        competitor_price=95.00,
        is_kvi=True,
        promo_active=False,
        promo_price=None,
        days_of_cover=10.0,  # normal inventory
    )

    candidate_price = 130.00  # intentionally too high
    result = apply_guardrails(candidate_price=candidate_price, ctx=ctx, policy=policy)

    print("Candidate price:", candidate_price)
    print("Final price:", result.final_price)
    print("Reasons:", result.reasons)


if __name__ == "__main__":
    main()
