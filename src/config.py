from dataclasses import dataclass


@dataclass
class FeeConfig:
    """Default commission structure for order execution."""

    maker_fee: float = 0.00018  # 0.0180%
    taker_fee: float = 0.00045  # 0.0450%
    default_order_type: str = "maker"

    def get_rate(self, order_type: str | None = None) -> float:
        order = (order_type or self.default_order_type or "").lower()
        if order == "maker":
            return self.maker_fee
        if order == "taker":
            return self.taker_fee
        raise ValueError(f"Unsupported order type for fee calculation: {order_type}")


FEE_CONFIG = FeeConfig()
