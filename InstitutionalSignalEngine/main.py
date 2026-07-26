"""
Main entry point and orchestrator for the Institutional Signal Intelligence Engine.

Wires together all decoupled components using Dependency Injection,
starts the market data stream, and routes live packets through the entire 
processing, feature, signal, and execution pipeline.
"""

import logging
import signal
import sys
import time
from typing import Any, Dict

# Core & Config
from config import config
from core.logger import LoggerFactory

# Authentication & Market Data
from auth.authentication import AuthenticationManager
from execution.market_data.paytm_market_data_adapter import PaytmMarketDataAdapter

# Processing Builders
from processing.candle_builder import CandleBuilder
from processing.option_chain_builder import OptionChainBuilder
from processing.market_snapshot_builder import MarketSnapshotBuilder

# Feature Engine & Calculators
from features.feature_engine import FeatureEngine
from features.healthy_candle import HealthyCandleCalculator
from features.institutional_score import InstitutionalScoreCalculator
from features.strike_migration import StrikeMigrationCalculator
from features.momentum_center import MomentumCenterCalculator
from features.breadth_engine import BreadthCalculator
from features.dominance_engine import DominanceCalculator

# Signal Layer (Unified)
from signal.signal_registry import SignalRegistry
from signals.signal_provider_adapter import SignalProviderAdapter
from signals.multi_factor_aggregator import MultiFactorAggregator

# Legacy Signal Generators (Wrapped by Adapter)
from signals.healthy_candle_signal import HealthyCandleSignalGenerator
from signals.momentum_signal import MomentumSignalGenerator
from signals.strike_migration_signal import StrikeMigrationSignalGenerator
from signals.breadth_signal import BreadthSignalGenerator
from signals.dominance_signal import DominanceSignalGenerator
from signals.institutional_signal import InstitutionalSignalGenerator

# Execution & Paper Trading
from paper_trading.paper_trade_manager import PaperTradeManager
from execution.position_sizer import PositionSizer
from models import Tick


class EngineOrchestrator:
    """
    Central orchestrator that manages the lifecycle of the Institutional Signal Engine.
    """

    def __init__(self) -> None:
        self._logger = LoggerFactory().get_logger(__name__)
        self._running = False

        # 1. Authentication
        self._auth_manager = AuthenticationManager()

        # 2. Market Data Adapter (includes WebSocket & REST)
        self._market_data = PaytmMarketDataAdapter(
            auth_manager=self._auth_manager,
            on_packet_callback=self._on_market_data_packet
        )

        # 3. Processing Builders
        self._candle_builder = CandleBuilder()
        self._option_chain_builder = OptionChainBuilder()
        self._snapshot_builder = MarketSnapshotBuilder()

        # 4. Feature Engine
        self._feature_engine = FeatureEngine()
        self._register_feature_calculators()

        # 5. Signal Registry & Aggregator
        self._signal_registry = SignalRegistry()
        self._register_signal_providers()
        self._signal_aggregator = MultiFactorAggregator(self._signal_registry)

        # 6. Execution (Paper Trading & Sizing)
        self._paper_trade_manager = PaperTradeManager()
        self._position_sizer = PositionSizer(
            base_risk_per_trade=0.01,  # 1% base risk
            max_position_size=500      # Hard cap to prevent fat-finger errors
        )

        # Setup graceful shutdown handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _register_feature_calculators(self) -> None:
        """Registers all feature calculators with the FeatureEngine."""
        healthy_calc = HealthyCandleCalculator()
        self._feature_engine.register_calculator("healthy_candle", healthy_calc)
        
        self._feature_engine.register_calculator(
            "institutional_score", 
            InstitutionalScoreCalculator(healthy_candle_calculator=healthy_calc)
        )
        
        self._feature_engine.register_calculator("strike_migration", StrikeMigrationCalculator())
        self._feature_engine.register_calculator("momentum_center", MomentumCenterCalculator())
        self._feature_engine.register_calculator("breadth", BreadthCalculator())
        self._feature_engine.register_calculator("dominance", DominanceCalculator())
        self._logger.info("✅ Feature calculators registered.")

    def _register_signal_providers(self) -> None:
        """Registers signal providers (wrapped in adapters) with the SignalRegistry."""
        providers_to_register = [
            (HealthyCandleSignalGenerator(), weight=1.0),
            (MomentumSignalGenerator(), weight=1.5),
            (StrikeMigrationSignalGenerator(), weight=1.2),
            (BreadthSignalGenerator(), weight=1.0),
            (DominanceSignalGenerator(), weight=1.0),
            (InstitutionalSignalGenerator(), weight=1.5),
        ]
        
        for generator, weight in providers_to_register:
            adapter = SignalProviderAdapter(generator, weight=weight)
            self._signal_registry.register(adapter)
            
        self._logger.info(f"✅ {len(providers_to_register)} Signal providers registered and adapted.")

    def start(self) -> None:
        """Starts the engine, connects to the broker, and begins streaming."""
        self._logger.info("🚀 Starting Institutional Signal Intelligence Engine...")
        self._running = True

        try:
            self._logger.info("Authenticating with broker...")
            self._market_data.connect()

            self._logger.info("Connecting to live market data stream...")
            self._market_data.connect_websocket()

            self._logger.info("✅ Engine is running. Waiting for market data...")
            
            while self._running:
                time.sleep(1)
                
        except Exception as e:
            self._logger.error(f"Fatal engine error: {e}", exc_info=True)
            self.stop()

    def stop(self) -> None:
        """Gracefully shuts down the engine and all components."""
        self._logger.info("🛑 Initiating graceful shutdown...")
        self._running = False
        
        self._market_data.disconnect()
        
        # Print final paper trading summary
        state = self._paper_trade_manager.get_account_state()
        history = self._paper_trade_manager.get_trade_history()
        self._logger.info("="*50)
        self._logger.info(f"FINAL ACCOUNT STATE: Capital: ₹{state['current_capital']:,.2f} | Daily PnL: ₹{state['daily_pnl']:,.2f}")
        self._logger.info(f"TOTAL TRADES EXECUTED: {len(history)}")
        self._logger.info("="*50)
        
        self._logger.info("✅ Engine shutdown complete.")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handles OS signals (Ctrl+C) for graceful shutdown."""
        self._logger.info(f"Received shutdown signal {signum}.")
        self.stop()
        sys.exit(0)

    def _on_market_data_packet(self, packet: Dict[str, Any]) -> None:
        """
        The central callback for all incoming raw market data packets.
        Routes the packet through the entire processing pipeline.
        """
        if not self._running:
            return

        try:
            # 1. Convert packet dict to Tick model
            tick = Tick(
                timestamp=packet.get("last_trade_time") or time.time(),
                index_name="NIFTY", # TODO: Derive dynamically from security_id mapping
                ltp=float(packet.get("last_price", 0.0)),
                volume=int(packet.get("volume_traded", 0))
            )

            # 2. Feed to builders
            self._candle_builder.add_tick(tick)
            self._snapshot_builder.update_tick(tick)

            # 3. Build Snapshot
            snapshot = self._snapshot_builder.build_snapshot()

            # 4. Calculate Features
            features = self._feature_engine.calculate(snapshot)

            # 5. Aggregate Signals
            final_signal = self._signal_aggregator.aggregate(features)

            # 6. Execute via Paper Trading (if signal is actionable and no conflicting position)
            if final_signal.decision.name in ["BUY", "SELL"]:
                current_pos = self._paper_trade_manager.get_position("NIFTY")
                
                # Simple logic: only enter if we don't already have an opposing position
                can_enter = True
                if current_pos and current_pos["side"] != final_signal.decision.name:
                    can_enter = False # Prevent reversing without explicit logic (can be enhanced later)

                if can_enter:
                    self._logger.info(f"🚨 ACTIONABLE SIGNAL: {final_signal.decision.name} | Conf: {final_signal.confidence:.1f}%")
                    
                    # Dynamic Position Sizing
                    stop_loss_distance = tick.ltp * 0.005 # Example: 0.5% SL distance
                    quantity = self._position_sizer.calculate_quantity(
                        available_capital=self._paper_trade_manager.get_account_state()["current_capital"],
                        current_price=tick.ltp,
                        signal_confidence=final_signal.confidence,
                        stop_loss_distance=stop_loss_distance
                    )
                    
                    if quantity > 0:
                        order_request = {
                            "symbol": "NIFTY",
                            "side": final_signal.decision.name,
                            "order_type": "MARKET",
                            "quantity": quantity,
                            "price": tick.ltp,
                            "stop_loss": tick.ltp - stop_loss_distance if final_signal.decision.name == "BUY" else tick.ltp + stop_loss_distance,
                            "target": tick.ltp + (stop_loss_distance * 2), # 1:2 Risk/Reward
                            "signal": final_signal.decision.name,
                            "reason": final_signal.reason_summary
                        }
                        
                        self._paper_trade_manager.place_order(order_request)
                    else:
                        self._logger.warning("Signal ignored: Calculated quantity is 0 (insufficient capital/confidence).")

            # 7. Always process tick for open position management (SL/Target/Trailing checks)
            self._paper_trade_manager.process_tick(tick)
            
        except Exception as e:
            # Isolate errors so one bad packet doesn't crash the WebSocket
            self._logger.error(f"Error processing market data packet: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    orchestrator = EngineOrchestrator()
    orchestrator.start()