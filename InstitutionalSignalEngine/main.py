"""
Main entry point and orchestrator for the Institutional Signal Intelligence Engine.

This module wires together all decoupled components using Dependency Injection,
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

# Signal Registry
from signal.signal_registry import SignalRegistry

# Execution & Paper Trading
from paper_trading.paper_trade_manager import PaperTradeManager
from models import Tick  # Assuming your packet decoder outputs a Tick-like dict or object


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

        # 5. Signal Registry
        self._signal_registry = SignalRegistry()
        self._register_signal_providers()

        # 6. Execution (Paper Trading)
        self._paper_trade_manager = PaperTradeManager()

        # Setup graceful shutdown handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _register_feature_calculators(self) -> None:
        """Registers all feature calculators with the FeatureEngine."""
        healthy_calc = HealthyCandleCalculator()
        self._feature_engine.register_calculator("healthy_candle", healthy_calc)
        
        # Inject healthy candle calculator into institutional score to avoid circular dependency
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
        """Registers signal providers with the SignalRegistry."""
        # NOTE: In Phase 2, we will wrap the existing signal generators here 
        # so they implement the SignalProvider Protocol.
        self._logger.info("✅ Signal providers registered.")

    def start(self) -> None:
        """Starts the engine, connects to the broker, and begins streaming."""
        self._logger.info("🚀 Starting Institutional Signal Intelligence Engine...")
        self._running = True

        try:
            # 1. Authenticate
            self._logger.info("Authenticating with broker...")
            self._market_data.connect()

            # 2. Start WebSocket Stream
            self._logger.info("Connecting to live market data stream...")
            self._market_data.connect_websocket()

            # Example: Subscribe to NIFTY spot (Replace with actual config SIDs)
            # self._market_data.subscribe(scrip_id=13, exchange="NSE", scrip_type="INDEX", mode="FULL")
            
            self._logger.info("✅ Engine is running. Waiting for market data...")
            
            # Keep main thread alive while background WebSocket thread runs
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
        # Optional: Save final paper trading state or generate end-of-day report here
        
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
            # TODO (Phase 2/3): Wire the actual data flow here.
            # 1. Convert packet dict to Tick / OptionChainSnapshot models
            # 2. self._candle_builder.add_tick(tick)
            # 3. self._snapshot_builder.update_tick(tick)
            # 4. snapshot = self._snapshot_builder.build_snapshot()
            # 5. features = self._feature_engine.calculate(snapshot)
            # 6. Evaluate signals via self._signal_registry.get_enabled()
            # 7. self._paper_trade_manager.process_tick(tick) # Checks for auto-exits
            
            pass 
            
        except Exception as e:
            # Isolate errors so one bad packet doesn't crash the WebSocket
            self._logger.error(f"Error processing market data packet: {e}", exc_info=True)


if __name__ == "__main__":
    # Configure root logger for the entire application
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    orchestrator = EngineOrchestrator()
    orchestrator.start()