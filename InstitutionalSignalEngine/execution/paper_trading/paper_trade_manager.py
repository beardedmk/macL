"""
Paper trade manager module for the Institutional Signal Intelligence Engine.

Simulates trade execution, position management, and PnL calculation without 
communicating with any live broker. Strictly isolated from signal generation, 
market data ingestion, and live order execution.
"""

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import config
from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import Tick


class TradeManagerInterface(ABC):
    """
    Abstract interface for trade execution managers.
    Ensures PaperTradeManager can be seamlessly replaced by LiveTradeManager.
    """

    @abstractmethod
    def place_order(self, order_request: Dict[str, Any]) -> str:
        """Places an order and returns the order ID."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancels a pending order."""
        pass

    @abstractmethod
    def process_tick(self, tick: Tick) -> None:
        """Processes a market tick to update positions and check order fills."""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves the current open position for a symbol."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Retrieves all open positions."""
        pass

    @abstractmethod
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Retrieves all pending orders."""
        pass

    @abstractmethod
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Retrieves the complete trade history."""
        pass

    @abstractmethod
    def get_account_state(self) -> Dict[str, Any]:
        """Retrieves current capital, margin, and daily PnL."""
        pass

    @abstractmethod
    def square_off(self, symbol: str) -> None:
        """Squares off a specific position."""
        pass

    @abstractmethod
    def square_off_all(self) -> None:
        """Squares off all open positions."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets the manager to its initial state."""
        pass


@dataclass
class _PaperConfig:
    """Configuration for paper trading simulation."""
    initial_capital: float = 1000000.0
    brokerage_fixed: float = 20.0
    brokerage_percent: float = 0.0003
    stt_percent: float = 0.00025
    exchange_charges_percent: float = 0.0000325
    gst_percent: float = 0.18
    sebi_charges_per_cr: float = 10.0
    stamp_duty_percent: float = 0.00003
    slippage: float = 0.05
    max_daily_loss: float = 20000.0
    max_position_size: int = 1000
    max_open_trades: int = 5
    risk_per_trade: float = 0.02


@dataclass
class _Position:
    symbol: str
    side: str
    quantity: int
    avg_price: float
    stop_loss: float
    target: float
    trailing_stop: Optional[float]
    margin_used: float
    entry_time: datetime
    signal: str
    reason: str


@dataclass
class _Order:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    price: float
    trigger_price: float
    status: str
    timestamp: datetime
    signal: str
    reason: str
    stop_loss: float
    target: float
    trailing_stop: Optional[float]


@dataclass
class _TradeRecord:
    trade_id: str
    symbol: str
    side: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    signal: str
    reason: str
    stop_loss: float
    target: float
    gross_pnl: float
    charges: float
    net_pnl: float
    duration_seconds: float


class PaperTradeManager(TradeManagerInterface):
    """
    Thread-safe execution simulator for paper trading.
    Manages positions, orders, PnL, and risk controls without live broker interaction.
    """

    def __init__(self) -> None:
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._config = self._load_config()
        
        self._initial_capital = self._config.initial_capital
        self._capital = self._initial_capital
        self._available_margin = self._initial_capital
        self._daily_pnl = 0.0
        
        self._positions: Dict[str, _Position] = {}
        self._pending_orders: Dict[str, _Order] = {}
        self._trade_history: List[_TradeRecord] = []
        self._equity_curve: List[Tuple[datetime, float]] = [(datetime.now(), self._initial_capital)]

    def _load_config(self) -> _PaperConfig:
        cfg = getattr(config, 'paper_trading', None)
        if cfg:
            return _PaperConfig(**{k: getattr(cfg, k, v) for k, v in _PaperConfig().__dict__.items()})
        return _PaperConfig()

    def place_order(self, order_request: Dict[str, Any]) -> str:
        with self._lock:
            req = self._validate_and_build_order(order_request)
            self._check_risk_limits(req)
            
            order_id = uuid.uuid4().hex
            
            if req.order_type == "MARKET":
                fill_price = self._get_fill_price(req.side, req.price)
                self._process_fill(req, fill_price, datetime.now(), order_id)
                return order_id
            
            order = _Order(
                order_id=order_id,
                symbol=req.symbol,
                side=req.side,
                order_type=req.order_type,
                quantity=req.quantity,
                price=req.price,
                trigger_price=req.trigger_price,
                status="PENDING",
                timestamp=datetime.now(),
                signal=req.signal,
                reason=req.reason,
                stop_loss=req.stop_loss,
                target=req.target,
                trailing_stop=req.trailing_stop
            )
            self._pending_orders[order_id] = order
            self._logger.info(f"Pending order placed: {order_id} | {req.side} {req.quantity} {req.symbol} @ {req.price}")
            return order_id

    def cancel_order(self, order_id: str) -> bool:
        with self._lock:
            if order_id in self._pending_orders:
                self._pending_orders[order_id].status = "CANCELLED"
                self._logger.info(f"Order cancelled: {order_id}")
                return True
            return False

    def process_tick(self, tick: Tick) -> None:
        with self._lock:
            self._process_pending_orders(tick)
            self._process_positions(tick)
            self._update_equity_curve(tick.timestamp)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            pos = self._positions.get(symbol)
            return self._position_to_dict(pos) if pos else None

    def get_positions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._position_to_dict(pos) for pos in self._positions.values()]

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._order_to_dict(order) for order in self._pending_orders.values() if order.status == "PENDING"]

    def get_trade_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._trade_to_dict(trade) for trade in self._trade_history]

    def get_account_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initial_capital": self._initial_capital,
                "current_capital": self._capital,
                "available_margin": self._available_margin,
                "daily_pnl": self._daily_pnl,
                "open_positions": len(self._positions),
                "pending_orders": len([o for o in self._pending_orders.values() if o.status == "PENDING"])
            }

    def square_off(self, symbol: str) -> None:
        with self._lock:
            pos = self._positions.get(symbol)
            if pos:
                self._close_position_full(pos, None, pos.avg_price, datetime.now(), "SQUARE_OFF")

    def square_off_all(self) -> None:
        with self._lock:
            for symbol in list(self._positions.keys()):
                self.square_off(symbol)

    def reset(self) -> None:
        with self._lock:
            self._capital = self._initial_capital
            self._available_margin = self._initial_capital
            self._daily_pnl = 0.0
            self._positions.clear()
            self._pending_orders.clear()
            self._trade_history.clear()
            self._equity_curve.clear()
            self._equity_curve.append((datetime.now(), self._initial_capital))
            self._logger.info("Paper trade manager reset to initial state.")

    # -------------------------------------------------------------------------
    # Internal Execution & Position Management
    # -------------------------------------------------------------------------

    def _validate_and_build_order(self, req_dict: Dict[str, Any]) -> Any:
        class OrderReq:
            pass
        req = OrderReq()
        req.symbol = req_dict.get("symbol")
        req.side = req_dict.get("side", "BUY").upper()
        req.order_type = req_dict.get("order_type", "MARKET").upper()
        req.quantity = int(req_dict.get("quantity", 0))
        req.price = float(req_dict.get("price", 0.0))
        req.trigger_price = float(req_dict.get("trigger_price", 0.0))
        req.stop_loss = float(req_dict.get("stop_loss", 0.0))
        req.target = float(req_dict.get("target", 0.0))
        req.trailing_stop = req_dict.get("trailing_stop")
        req.signal = req_dict.get("signal", "")
        req.reason = req_dict.get("reason", "")

        if not req.symbol or req.quantity <= 0:
            raise ValidationError("Invalid order request: symbol and quantity > 0 required.")
        if req.side not in {"BUY", "SELL"}:
            raise ValidationError(f"Invalid side: {req.side}")
        if req.order_type not in {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}:
            raise ValidationError(f"Invalid order type: {req.order_type}")
            
        return req

    def _check_risk_limits(self, req: Any) -> None:
        if self._daily_pnl <= -self._config.max_daily_loss:
            raise ValidationError("Max daily loss reached. Trading halted.")
        if req.quantity > self._config.max_position_size:
            raise ValidationError(f"Quantity {req.quantity} exceeds max position size {self._config.max_position_size}.")
        
        margin_req = self._calculate_margin_requirement(req)
        if self._available_margin < margin_req:
            raise ValidationError(f"Insufficient margin. Required: {margin_req:.2f}, Available: {self._available_margin:.2f}")
            
        if req.symbol not in self._positions and len(self._positions) >= self._config.max_open_trades:
            raise ValidationError(f"Max open trades ({self._config.max_open_trades}) reached.")

    def _calculate_margin_requirement(self, req: Any) -> float:
        # Simplified margin calculation
        pos = self._positions.get(req.symbol)
        if pos and ((req.side == "BUY" and pos.side == "LONG") or (req.side == "SELL" and pos.side == "SHORT")):
            return 0.0  # Increasing position doesn't require new margin in this simplified model
        return req.quantity * req.price * self._config.risk_per_trade

    def _get_fill_price(self, side: str, reference_price: float) -> float:
        slippage = self._config.slippage
        if side == "BUY":
            return reference_price + slippage
        return reference_price - slippage

    def _process_fill(self, req: Any, fill_price: float, timestamp: datetime, order_id: str) -> None:
        symbol = req.symbol
        pos = self._positions.get(symbol)
        
        if pos is None:
            self._open_position(req, fill_price, timestamp, order_id)
        else:
            if (req.side == "BUY" and pos.side == "LONG") or (req.side == "SELL" and pos.side == "SHORT"):
                self._increase_position(pos, req, fill_price)
            else:
                if req.quantity < pos.quantity:
                    self._reduce_position(pos, req, fill_price, timestamp, order_id)
                elif req.quantity == pos.quantity:
                    self._close_position_full(pos, req, fill_price, timestamp, order_id)
                else:
                    self._close_position_full(pos, req, fill_price, timestamp, order_id)
                    self._open_reverse(req, fill_price, timestamp, order_id)

    def _open_position(self, req: Any, fill_price: float, timestamp: datetime, order_id: str) -> None:
        side = "LONG" if req.side == "BUY" else "SHORT"
        margin_used = req.quantity * fill_price * self._config.risk_per_trade
        
        pos = _Position(
            symbol=req.symbol,
            side=side,
            quantity=req.quantity,
            avg_price=fill_price,
            stop_loss=req.stop_loss,
            target=req.target,
            trailing_stop=req.trailing_stop,
            margin_used=margin_used,
            entry_time=timestamp,
            signal=req.signal,
            reason=req.reason
        )
        self._positions[req.symbol] = pos
        self._available_margin -= margin_used
        self._logger.info(f"Position OPENED: {side} {req.quantity} {req.symbol} @ {fill_price}")

    def _increase_position(self, pos: _Position, req: Any, fill_price: float) -> None:
        total_qty = pos.quantity + req.quantity
        pos.avg_price = ((pos.avg_price * pos.quantity) + (fill_price * req.quantity)) / total_qty
        pos.quantity = total_qty
        self._logger.info(f"Position INCREASED: {pos.side} {pos.quantity} {pos.symbol} @ avg {pos.avg_price}")

    def _reduce_position(self, pos: _Position, req: Any, fill_price: float, timestamp: datetime, order_id: str) -> None:
        exit_qty = req.quantity
        gross_pnl = self._calculate_pnl(pos.side, pos.avg_price, fill_price, exit_qty)
        charges = self._calculate_charges(req.side, exit_qty, fill_price)
        net_pnl = gross_pnl - charges
        
        self._record_trade(pos, req, fill_price, timestamp, exit_qty, gross_pnl, charges, net_pnl)
        
        pos.quantity -= exit_qty
        self._available_margin += pos.margin_used * (exit_qty / (pos.quantity + exit_qty))
        self._logger.info(f"Position REDUCED: {pos.side} {pos.quantity} {pos.symbol} | Net PnL: {net_pnl:.2f}")

    def _close_position_full(self, pos: _Position, req: Any, fill_price: float, timestamp: datetime, order_id: str) -> None:
        exit_qty = pos.quantity
        gross_pnl = self._calculate_pnl(pos.side, pos.avg_price, fill_price, exit_qty)
        charges = self._calculate_charges("SELL" if pos.side == "LONG" else "BUY", exit_qty, fill_price)
        net_pnl = gross_pnl - charges
        
        self._record_trade(pos, req, fill_price, timestamp, exit_qty, gross_pnl, charges, net_pnl)
        
        self._available_margin += pos.margin_used
        self._capital += net_pnl
        self._daily_pnl += net_pnl
        
        del self._positions[pos.symbol]
        self._logger.info(f"Position CLOSED: {pos.side} {exit_qty} {pos.symbol} | Net PnL: {net_pnl:.2f}")

    def _open_reverse(self, req: Any, fill_price: float, timestamp: datetime, order_id: str) -> None:
        rev_side = "SELL" if req.side == "BUY" else "BUY"
        rev_qty = req.quantity - self._positions.get(req.symbol, _Position("", "", 0, 0, 0, 0, None, 0, timestamp, "", "")).quantity
        
        class RevReq:
            pass
        rev_req = RevReq()
        rev_req.symbol = req.symbol
        rev_req.side = rev_side
        rev_req.quantity = rev_qty
        rev_req.stop_loss = req.stop_loss
        rev_req.target = req.target
        rev_req.trailing_stop = req.trailing_stop
        rev_req.signal = req.signal
        rev_req.reason = f"Reverse of {req.side}"
        
        self._open_position(rev_req, fill_price, timestamp, order_id)

    def _process_pending_orders(self, tick: Tick) -> None:
        orders_to_remove = []
        for order_id, order in self._pending_orders.items():
            if order.status != "PENDING":
                continue
                
            filled = False
            if order.order_type in ["LIMIT", "STOP_LIMIT"]:
                if order.side == "BUY" and tick.ltp <= order.price:
                    filled = True
                elif order.side == "SELL" and tick.ltp >= order.price:
                    filled = True
                    
            if order.order_type in ["STOP", "STOP_LIMIT"]:
                if order.side == "BUY" and tick.ltp >= order.trigger_price:
                    order.order_type = "MARKET"
                    filled = True
                elif order.side == "SELL" and tick.ltp <= order.trigger_price:
                    order.order_type = "MARKET"
                    filled = True
                    
            if filled:
                fill_price = self._get_fill_price(order.side, tick.ltp)
                self._process_fill(order, fill_price, tick.timestamp, order_id)
                order.status = "FILLED"
                orders_to_remove.append(order_id)
                
        for oid in orders_to_remove:
            del self._pending_orders[oid]

    def _process_positions(self, tick: Tick) -> None:
        symbols_to_close = []
        for symbol, pos in self._positions.items():
            # Update trailing stop
            if pos.trailing_stop is not None:
                if pos.side == "LONG":
                    new_sl = tick.ltp - pos.trailing_stop
                    if new_sl > pos.stop_loss:
                        pos.stop_loss = new_sl
                else:
                    new_sl = tick.ltp + pos.trailing_stop
                    if new_sl < pos.stop_loss:
                        pos.stop_loss = new_sl

            # Check exits
            if pos.side == "LONG":
                if tick.ltp <= pos.stop_loss or tick.ltp >= pos.target:
                    symbols_to_close.append((symbol, tick.ltp, "SL/Target Hit"))
            else:
                if tick.ltp >= pos.stop_loss or tick.ltp <= pos.target:
                    symbols_to_close.append((symbol, tick.ltp, "SL/Target Hit"))

        for symbol, exit_price, reason in symbols_to_close:
            pos = self._positions.get(symbol)
            if pos:
                class MockReq:
                    pass
                req = MockReq()
                req.side = "SELL" if pos.side == "LONG" else "BUY"
                req.signal = pos.signal
                req.reason = reason
                self._close_position_full(pos, req, exit_price, tick.timestamp, "AUTO_EXIT")

    def _calculate_pnl(self, side: str, entry_price: float, exit_price: float, quantity: int) -> float:
        if side == "LONG":
            return (exit_price - entry_price) * quantity
        return (entry_price - exit_price) * quantity

    def _calculate_charges(self, side: str, quantity: int, price: float) -> float:
        turnover = quantity * price
        brokerage = min(self._config.brokerage_fixed, turnover * self._config.brokerage_percent)
        stt = turnover * self._config.stt_percent if side == "SELL" else 0.0
        exchange_charges = turnover * self._config.exchange_charges_percent
        gst = (brokerage + exchange_charges) * self._config.gst_percent
        sebi = (turnover / 10000000.0) * self._config.sebi_charges_per_cr
        stamp_duty = turnover * self._config.stamp_duty_percent if side == "BUY" else 0.0
        
        return brokerage + stt + exchange_charges + gst + sebi + stamp_duty

    def _record_trade(self, pos: _Position, req: Any, exit_price: float, timestamp: datetime, 
                      qty: int, gross_pnl: float, charges: float, net_pnl: float) -> None:
        trade = _TradeRecord(
            trade_id=uuid.uuid4().hex,
            symbol=pos.symbol,
            side=pos.side,
            entry_time=pos.entry_time,
            exit_time=timestamp,
            entry_price=pos.avg_price,
            exit_price=exit_price,
            quantity=qty,
            signal=pos.signal,
            reason=req.reason if req else "SQUARE_OFF",
            stop_loss=pos.stop_loss,
            target=pos.target,
            gross_pnl=gross_pnl,
            charges=charges,
            net_pnl=net_pnl,
            duration_seconds=(timestamp - pos.entry_time).total_seconds()
        )
        self._trade_history.append(trade)

    def _update_equity_curve(self, timestamp: datetime) -> None:
        # Throttle equity curve updates to avoid memory bloat
        if not self._equity_curve or (timestamp - self._equity_curve[-1][0]).total_seconds() > 60:
            unrealized = sum(self._calculate_pnl(p.side, p.avg_price, p.avg_price, p.quantity) for p in self._positions.values())
            self._equity_curve.append((timestamp, self._capital + unrealized))

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _position_to_dict(self, pos: _Position) -> Dict[str, Any]:
        return {
            "symbol": pos.symbol,
            "side": pos.side,
            "quantity": pos.quantity,
            "avg_price": pos.avg_price,
            "stop_loss": pos.stop_loss,
            "target": pos.target,
            "trailing_stop": pos.trailing_stop,
            "entry_time": pos.entry_time.isoformat(),
            "signal": pos.signal,
            "reason": pos.reason
        }

    def _order_to_dict(self, order: _Order) -> Dict[str, Any]:
        return {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "order_type": order.order_type,
            "quantity": order.quantity,
            "price": order.price,
            "trigger_price": order.trigger_price,
            "status": order.status,
            "timestamp": order.timestamp.isoformat()
        }

    def _trade_to_dict(self, trade: _TradeRecord) -> Dict[str, Any]:
        return {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat(),
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "quantity": trade.quantity,
            "signal": trade.signal,
            "reason": trade.reason,
            "gross_pnl": trade.gross_pnl,
            "charges": trade.charges,
            "net_pnl": trade.net_pnl,
            "duration_seconds": trade.duration_seconds
        }