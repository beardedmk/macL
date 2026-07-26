"""
Packet decoder module for the Institutional Signal Intelligence Engine.

Decodes raw binary WebSocket frames from the market data provider into 
structured dictionaries. Strictly isolated from connection management.
"""

import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class PacketDecoder:
    """
    Stateless decoder for Paytm Money binary WebSocket packets.
    """

    def __init__(self) -> None:
        self._packet_sizes = {61: 23, 62: 67, 63: 175, 64: 23, 65: 43, 66: 39}
        self._paytm_epoch = int(datetime(1980, 1, 1, tzinfo=timezone.utc).timestamp())

    def decode(self, frame: bytes) -> List[Dict[str, Any]]:
        """
        Parses a binary WebSocket frame into a list of decoded packet dictionaries.
        
        Args:
            frame: The raw bytes received from the WebSocket.
            
        Returns:
            A list of decoded packet dictionaries.
        """
        packets = []
        pos = 0
        while pos < len(frame):
            ptype = frame[pos]
            size = self._packet_sizes.get(ptype)
            if not size or pos + size > len(frame):
                break
            
            packet = self._decode_packet(ptype, frame[pos:pos + size])
            if packet:
                packets.append(packet)
            pos += size
        return packets

    def _decode_packet(self, ptype: int, buffer: bytes) -> Optional[Dict[str, Any]]:
        try:
            if ptype in [61, 64]:
                return {
                    "security_id": self._read_int(buffer, 9),
                    "last_price": self._read_float(buffer, 1),
                    "last_trade_time": self._convert_epoch(self._read_int(buffer, 5)),
                    "volume_traded": 0
                }
            if ptype in [62, 65]:
                return {
                    "security_id": self._read_int(buffer, 9),
                    "last_price": self._read_float(buffer, 1),
                    "last_trade_time": self._convert_epoch(self._read_int(buffer, 5)),
                    "volume_traded": self._read_int(buffer, 23)
                }
            if ptype in [63, 66]:
                offset_id = 109 if ptype == 63 else 5
                offset_price = 101 if ptype == 63 else 1
                offset_time = 105 if ptype == 63 else 35
                offset_vol = 123 if ptype == 63 else 0
                
                return {
                    "security_id": self._read_int(buffer, offset_id),
                    "last_price": self._read_float(buffer, offset_price),
                    "last_trade_time": self._convert_epoch(self._read_int(buffer, offset_time)),
                    "volume_traded": self._read_int(buffer, offset_vol)
                }
        except Exception:
            # Silently ignore malformed packets to prevent stream disruption
            pass
            
        return None

    def _read_float(self, buffer: bytes, offset: int) -> float:
        return struct.unpack_from("<f", buffer, offset)[0]

    def _read_int(self, buffer: bytes, offset: int) -> int:
        return struct.unpack_from("<i", buffer, offset)[0]

    def _convert_epoch(self, seconds: int) -> Optional[datetime]:
        if seconds == 0:
            return None
        return datetime.fromtimestamp(self._paytm_epoch + seconds, tz=timezone.utc)