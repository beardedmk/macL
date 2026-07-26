"""
Candle storage module for the Institutional Signal Intelligence Engine.

Handles the high-performance, thread-safe persistence of completed OHLCV 
Candle data to disk in Parquet format. Strictly isolated from candle 
generation, indicator calculation, and signal logic.
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config import config
from core.exceptions import StorageError
from core.logger import LoggerFactory
from models import Candle


class CandleStore:
    """
    Thread-safe storage engine for persisting completed market candles.
    Utilizes in-memory batching and automatic time-based flushing 
    to optimize disk I/O operations.
    """

    def __init__(self) -> None:
        """
        Initializes the candle store, sets up storage directories,
        and starts the background flush thread.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        
        self._base_path: Path = config.storage.base_path / config.storage.candles_dir
        self._compression: str = config.storage.compression
        self._batch_size: int = config.storage.batch_size
        self._flush_interval: int = config.storage.flush_interval_seconds
        
        self._buffer: List[Dict] = []
        self._lock = threading.Lock()
        
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        
        try:
            self._base_path.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"Candle storage initialized at: {self._base_path}")
        except OSError as e:
            raise StorageError(f"Failed to create candle storage directory: {e}") from e

        self._flush_thread.start()
        self._logger.info("Background candle flush thread started.")

    def add_candle(self, candle: Candle) -> None:
        """
        Adds a completed candle to the in-memory buffer. Triggers an immediate 
        flush if the batch size threshold is reached.
        
        Args:
            candle: The strongly typed Candle object to persist.
            
        Raises:
            StorageError: If the candle cannot be processed or buffered.
        """
        try:
            candle_dict = {
                "start_time": candle.start_time,
                "end_time": candle.end_time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume
            }
        except Exception as e:
            raise StorageError(f"Failed to serialize candle to dictionary: {e}") from e

        should_flush = False
        with self._lock:
            self._buffer.append(candle_dict)
            if len(self._buffer) >= self._batch_size:
                should_flush = True

        if should_flush:
            self.flush()

    def flush(self) -> None:
        """
        Forces an immediate write of the in-memory buffer to disk.
        Clears the buffer after a successful write.
        
        Raises:
            StorageError: If the disk write operation fails.
        """
        with self._lock:
            if not self._buffer:
                return
            data_to_write = self._buffer
            self._buffer = []

        try:
            df = pd.DataFrame(data_to_write)
            table = pa.Table.from_pandas(df)
            
            file_path = self._get_daily_file_path()
            
            if file_path.exists():
                existing_table = pq.read_table(file_path)
                table = pa.concat_tables([existing_table, table])
                
            pq.write_table(table, file_path, compression=self._compression)
            self._logger.debug(f"Flushed {len(data_to_write)} candles to {file_path.name}")
            
        except Exception as e:
            self._logger.error(f"Failed to flush candles to disk: {e}")
            # Re-add failed data to the front of the buffer to prevent data loss
            with self._lock:
                self._buffer = data_to_write + self._buffer
            raise StorageError(f"Failed to persist candles to Parquet: {e}") from e

    def close(self) -> None:
        """
        Stops the background flush thread and performs a final flush 
        of any remaining data in the buffer.
        """
        self._logger.info("Shutting down candle store...")
        self._stop_event.set()
        
        if self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
            
        try:
            self.flush()
            self._logger.info("Candle store closed successfully.")
        except StorageError as e:
            self._logger.error(f"Error during final flush on close: {e}")

    def _flush_loop(self) -> None:
        """
        Background thread target that automatically triggers a flush 
        at the configured interval.
        """
        while not self._stop_event.is_set():
            self._stop_event.wait(self._flush_interval)
            if not self._stop_event.is_set():
                try:
                    self.flush()
                except StorageError:
                    self._logger.warning("Automatic candle flush failed. Will retry on next interval.")

    def _get_daily_file_path(self) -> Path:
        """
        Generates the file path for the current day's candle data.
        
        Returns:
            Path object pointing to the daily Parquet file.
        """
        date_str = datetime.now().strftime("%Y%m%d")
        file_name = f"candles_{date_str}.parquet"
        return self._base_path / file_name