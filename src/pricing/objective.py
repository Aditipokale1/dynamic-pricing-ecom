# src/pricing/objective.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ObjectiveInputs:
    price: float
    unit_cost: float
    expected_units: float

def expected_profit(x: ObjectiveInputs) -> float:
    """
    Expected profit objective:
        (price - unit_cost) * expected_units
    """
    return (x.price - x.unit_cost) * x.expected_units
