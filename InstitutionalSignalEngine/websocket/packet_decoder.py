"""
Packet decoder module for the Institutional Signal Intelligence Engine.

Decodes raw websocket JSON/dictionary packets into strongly typed 
market data models. Strictly handles parsing and validation without 
any connection, storage, or business logic.
"""

from datetime import datetime
from typing import Any, Dict, List

from core.exceptions import PacketDecodeError
from core.logger import LoggerFactory
from models import OptionChainSnapshot, OptionTick, Tick


class PacketDecoder:
    """
    Decodes raw market data packets into domain-specific dataclass models.
    All methods validate required fields and enforce strict type casting.
    """

    def __init__(self) -> None:
        """Initializes the decoder with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def _validate_fields(self, packet: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validates that all required fields are present in the raw packet.
        
        Args:
            packet: The raw dictionary packet.
            required_fields: List of keys that must exist.
            
        Raises:
            PacketDecodeError: If any required fields are missing.
        """
        missing = [field for field in required_fields if field not in packet]
        if missing:
            self._logger.error(f"Missing fields in packet: {missing}")
            raise PacketDecodeError(f"Missing required fields in packet: {missing}")

    def _parse_datetime(self, value: Any) -> datetime:
        """
        Parses a value into a timezone-aware or naive datetime object.
        Supports datetime objects, unix timestamps (int/float), and ISO strings.
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        
        raise PacketDecodeError(f"Cannot parse datetime from value: {value} (type: {type(value)})")

    def _parse_float(self, value: Any, field_name: str) -> float:
        """Safely casts a value to float."""
        try:
            return float(value)
        except (TypeError, ValueError):
            raise PacketDecodeError(f"Invalid float value for '{field_name}': {value}")

    def _parse_int(self, value: Any, field_name: str) -> int:
        """Safely casts a value to int."""
        try:
            return int(value)
        except (TypeError, ValueError):
            raise PacketDecodeError(f"Invalid int value for '{field_name}': {value}")

    def decode_tick(self, raw_packet: Dict[str, Any]) -> Tick:
        """
        Decodes a raw index tick packet into a Tick model.
        
        Args:
            raw_packet: Dictionary containing index tick data.
            
        Returns:
            A strongly typed Tick dataclass.
            
        Raises:
            PacketDecodeError: If validation or type casting fails.
        """
        self._validate_fields(raw_packet, ["timestamp", "index_name", "ltp", "volume"])
        
        try:
            return Tick(
                timestamp=self._parse_datetime(raw_packet["timestamp"]),
                index_name=str(raw_packet["index_name"]),
                ltp=self._parse_float(raw_packet["ltp"], "ltp"),
                volume=self._parse_int(raw_packet["volume"], "volume")
            )
        except PacketDecodeError:
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error decoding tick: {e}")
            raise PacketDecodeError(f"Failed to decode tick: {e}") from e

    def decode_option_tick(self, raw_packet: Dict[str, Any]) -> OptionTick:
        """
        Decodes a raw option contract packet into an OptionTick model.
        
        Args:
            raw_packet: Dictionary containing option contract data.
            
        Returns:
            A strongly typed OptionTick dataclass.
            
        Raises:
            PacketDecodeError: If validation or type casting fails.
        """
        self._validate_fields(
            raw_packet, 
            ["strike", "option_type", "ltp", "oi", "oi_change", "volume"]
        )
        
        try:
            return OptionTick(
                strike=self._parse_float(raw_packet["strike"], "strike"),
                option_type=str(raw_packet["option_type"]),
                ltp=self._parse_float(raw_packet["ltp"], "ltp"),
                oi=self._parse_int(raw_packet["oi"], "oi"),
                oi_change=self._parse_int(raw_packet["oi_change"], "oi_change"),
                volume=self._parse_int(raw_packet["volume"], "volume")
            )
        except PacketDecodeError:
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error decoding option tick: {e}")
            raise PacketDecodeError(f"Failed to decode option tick: {e}") from e

    def decode_option_chain(self, raw_packet: Dict[str, Any]) -> OptionChainSnapshot:
        """
        Decodes a raw option chain packet into an OptionChainSnapshot model.
        
        Args:
            raw_packet: Dictionary containing the full option chain snapshot.
            
        Returns:
            A strongly typed OptionChainSnapshot dataclass.
            
        Raises:
            PacketDecodeError: If validation or type casting fails.
        """
        self._validate_fields(
            raw_packet, 
            ["timestamp", "index_name", "expiry", "atm_strike", "options"]
        )
        
        try:
            raw_options = raw_packet["options"]
            if not isinstance(raw_options, list):
                raise PacketDecodeError("Field 'options' must be a list.")
                
            decoded_options: List[OptionTick] = [
                self.decode_option_tick(opt) for opt in raw_options
            ]
            
            return OptionChainSnapshot(
                timestamp=self._parse_datetime(raw_packet["timestamp"]),
                index_name=str(raw_packet["index_name"]),
                expiry=self._parse_datetime(raw_packet["expiry"]),
                atm_strike=self._parse_float(raw_packet["atm_strike"], "atm_strike"),
                options=decoded_options
            )
        except PacketDecodeError:
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error decoding option chain: {e}")
            raise PacketDecodeError(f"Failed to decode option chain: {e}") from e