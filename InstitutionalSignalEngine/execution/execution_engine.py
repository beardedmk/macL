"""
Execution engine module for the Institutional Signal Intelligence Engine.

Central orchestration layer responsible for executing approved trading signals 
and managing active trades based on market updates. Strictly isolated from 
signal generation, indicator calculation, broker execution, and storage.
"""

import threading
from typing import Any, Dict, Optional

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from execution.trade_manager import TradeManager
from models import FeatureSnapshot
from signals.exit_signal import ExitSignalGenerator
from signals.risk_filter import RiskFilter


class ExecutionEngine:
    """
    Thread-safe orchestration engine that coordinates the RiskFilter, 
    TradeManager, and ExitSignalGenerator to manage the complete 
    execution lifecycle of approved trading signals.
    """

    def __init__(
        self,
        trade_manager: TradeManager,
        risk_filter: RiskFilter,
        exit_generator: ExitSignalGenerator
    ) -> None:
        """
        Initializes the execution engine with required dependencies.
        
        Args:
            trade_manager: Manages order and position lifecycles.
            risk_filter: Validates signals against market risk thresholds.
            exit_generator: Evaluates market conditions for position exits.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._trade_manager = trade_manager
        self._risk_filter = risk_filter
        self._exit_generator = exit_generator

    def execute_entry(
        self,
        signal: Dict[str, Any],
        features: FeatureSnapshot,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        target: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes an approved entry signal, applies risk filtering, and 
        initiates a trade if all conditions are met.
        
        Args:
            signal: The validated entry signal dictionary.
            features: The current engineered feature snapshot.
            symbol: The trading instrument symbol.
            entry_price: The exact price at which to execute the entry.
            quantity: The number of units/contracts to trade.
            stop_loss: The stop loss price for the position.
            target: The target price for the position.
            metadata: Optional context for the trade.
            
        Returns:
            A dictionary containing execution success status, message, and order ID.
        """
        with self._lock:
            # 1. Check for duplicate active trades
            if self._trade_manager.has_active_trade():
                self._logger.warning("Execution rejected: An active trade already exists.")
                return {
                    "success": False,
                    "message": "Rejected: An active trade already exists.",
                    "order_id": None
                }

            # 2. Run RiskFilter
            filter_result = self._risk_filter.filter(signal, features)
            if not filter_result["allowed"]:
                reasons = " | ".join(filter_result["reasons"])
                self._logger.warning(f"Execution rejected by risk filter: {reasons}")
                return {
                    "success": False,
                    "message": f"Rejected by risk filter: {reasons}",
                    "order_id": None
                }

            # 3. Open trade via TradeManager
            try:
                side = signal.get("signal")
                if side not in {"BUY", "SELL"}:
                    raise ValidationError(f"Invalid signal side for execution: {side}")
                    
                order_id = self._trade_manager.open_trade(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=entry_price,
                    stop_loss=stop_loss,
                    target=target,
                    metadata=metadata
                )
                
                self._logger.info(f"Trade executed successfully | Order ID: {order_id}")
                return {
                    "success": True,
                    "message": "Trade executed successfully.",
                    "order_id": order_id
                }
                
            except ValidationError as e:
                self._logger.error(f"Failed to open trade: {e}")
                return {
                    "success": False,
                    "message": f"Failed to open trade: {str(e)}",
                    "order_id": None
                }

    def process_market_update(
        self, 
        features: FeatureSnapshot, 
        current_price: float
    ) -> Dict[str, Any]:
        """
        Processes a market update for an active trade, updating the market 
        price and evaluating exit conditions.
        
        Args:
            features: The current engineered feature snapshot.
            current_price: The latest market price.
            
        Returns:
            A dictionary containing the action ("EXIT" or "HOLD") and the reason.
        """
        with self._lock:
            # If no trade exists, do nothing
            if not self._trade_manager.has_active_trade():
                return {"action": "HOLD", "reason": "No active trade to process."}

            # Update PositionManager market price via TradeManager
            self._trade_manager.update_market_price(current_price)

            # Get current position state
            active_trade = self._trade_manager.get_active_trade()
            if not active_trade or not active_trade.get("has_open_position"):
                return {"action": "HOLD", "reason": "No open position to evaluate for exit."}
                
            current_position = active_trade["current_position"]

            # Run ExitSignalGenerator
            exit_result = self._exit_generator.generate(current_position, features)
            
            # If EXIT is returned, close the trade
            if exit_result["action"] == "EXIT":
                try:
                    self._trade_manager.close_trade(current_price)
                    self._logger.info(f"Trade closed via exit signal | Reason: {exit_result['reason']}")
                except ValidationError as e:
                    self._logger.error(f"Failed to close trade on exit signal: {e}")
                    
            return exit_result

    def get_execution_status(self) -> Dict[str, Any]:
        """
        Retrieves the current execution status, including active trade details.
        
        Returns:
            A dictionary containing execution status information.
        """
        with self._lock:
            return {
                "has_active_trade": self._trade_manager.has_active_trade(),
                "active_trade": self._trade_manager.get_active_trade(),
                "trade_summary": self._trade_manager.get_trade_summary()
            }

    def reset(self) -> None:
        """Resets the execution engine and clears all underlying trade states."""
        with self._lock:
            self._trade_manager.reset()
            self._logger.info("Execution engine state reset.")