from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CostModel:
    gas_price_per_gallon: Decimal
    mpg: Decimal
    maintenance_cost_per_mile: Decimal
    depreciation_cost_per_mile: Decimal = Decimal("0.000")
    labor_cost_per_hour: Decimal = Decimal("0.00")
    avg_speed_mph: Decimal = Decimal("25.0")  # fallback when using Haversine

    def cost_per_mile(self) -> Decimal:
        # gas $/mile = $/gal / mpg
        return (self.gas_price_per_gallon / self.mpg) + self.maintenance_cost_per_mile + self.depreciation_cost_per_mile

    def labor_cost_per_minute(self) -> Decimal:
        return self.labor_cost_per_hour / Decimal("60.0")
