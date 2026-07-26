"""
Position sizer module for the Institutional Signal Intelligence Engine.

Calculates optimal trade quantity based on account equity, signal confidence, 
and predefined risk parameters. Strictly isolated from order execution.
"""

from core.exceptions import ValidationError
from core.logger import LoggerFactory


class PositionSizer:
    """
    Calculates dynamic position sizing for trade execution based on 
    risk-per-trade and signal confidence.
    """

    def __init__(self, base_risk_per_trade: float = 0.01, max_position_size: int = 1000) -> None:
        """
        Args:
            base_risk_per_trade: Base percentage of capital to risk per trade (default 1%).
            max_position_size: Absolute maximum quantity allowed per trade to prevent fat-finger errors.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._base_risk = base_risk_per_trade
        self._max_size = max_position_size

    def calculate_quantity(
        self, 
        available_capital: float, 
        current_price: float, 
        signal_confidence: float,
        stop_loss_distance: float
    ) -> int:
        """
        Calculates the optimal trade quantity.
        
        Args:
            available_capital: Current available trading capital.
            current_price: The entry price of the asset.
            signal_confidence: The confidence score of the signal (0.0 to 100.0).
            stop_loss_distance: The absolute price distance to the stop loss (e.g., Entry - SL).
            
        Returns:
            The calculated integer quantity to trade.
            
        Raises:
            ValidationError: If inputs are invalid or risk cannot be calculated.
        """
        if available_capital <= 0:
            raise ValidationError("Available capital must be greater than zero.")
        if current_price <= 0:
            raise ValidationError("Current price must be greater than zero.")
        if not (0.0 <= signal_confidence <= 100.0):
            raise ValidationError(f"Signal confidence must be 0-100, got {signal_confidence}.")
        if stop_loss_distance <= 0:
            # Fallback for market orders without explicit SL distance: assume 1% risk distance
            stop_loss_distance = current_price * 0.01

        # 1. Calculate risk amount based on confidence scaling
        # Higher confidence = higher risk allocation (up to 2x base risk)
        confidence_multiplier = 0.5 + (signal_confidence / 100.0) 
        risk_amount = available_capital * self._base_risk * confidence_multiplier

        # 2. Calculate quantity based on risk per share/contract
        risk_per_unit = stop_loss_distance
        quantity = int(risk_amount / risk_per_unit)

        # 3. Enforce maximum position size limits
        final_quantity = min(quantity, self._max_size)
        
        # 4. Enforce minimum viable quantity (at least 1 if risk allows)
        if final_quantity < 1 and risk_amount >= risk_per_unit:
            final_quantity = 1
        elif final_quantity < 1:
            self._logger.warning("Calculated quantity is 0. Capital or confidence too low for minimum risk.")
            return 0

        self._logger.debug(
            f"Position Sizing: Capital={available_capital:.2f}, Conf={signal_confidence:.1f}%, "
            f"RiskAmt={risk_amount:.2f}, Qty={final_quantity}"
        )
        
        return final_quantity