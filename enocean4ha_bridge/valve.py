""" Bridge between a Home-Assistant switch component and the enocean python package. """

import logging
from typing import Any

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string

from . import EnOceanGateway
from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.valve')


class EO4HAValve:
    gateway: EnOceanGateway
    channel: int|None
    eep: EEPInfo
    dev_id: list[int]

    # noinspection PyUnusedLocal
    def turn_on(self, **kwargs: Any) -> None:
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0x1,
                destination=self.dev_id,
                DV=0x00,  # Dim value. 0x00 = switch to new value
                IO=self.channel,  # 0x1E = all supported channels
                OV=0x64,  # Output value. 0x64 = ON (=100%)
            )

    # noinspection PyUnusedLocal
    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0x1,
                destination=self.dev_id,
                DV=0x00,  # Dim value. 0x00 = switch to new value
                IO=self.channel,  # 0x1E = all supported channels
                OV=0x00,  # Output value. 0x00 = OFF
            )

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"valve, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        match self.eep.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)

    def _parse_a5_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x20 and func_type == 0x06:
            packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type, direction=1)
            result["status"] = packet.parsed["CV"]["raw_value"]
            result["extra_state_attr"].update({
                "CV": packet.parsed["CV"]["raw_value"],
            })

        return result
