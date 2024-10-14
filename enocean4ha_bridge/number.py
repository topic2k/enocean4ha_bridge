import logging

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string

from . import EnOceanGateway
from .common import EEPInfo

LOGGER = logging.getLogger('enocean')


class EO4HANumber:
    eep: EEPInfo
    dev_id: list[int]
    channel: int
    gateway: EnOceanGateway
    shortcut: str
    _attr_native_value: float|None

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"switch, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        match packet.rorg:
            case RORG.VLD:
                return self._parse_d2_packet(packet)

    def _parse_d2_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x01:
            packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type, command=packet.data[1])
            if packet.parsed["CMD"]["raw_value"] == 13:
                channel = packet.parsed["IO"]["raw_value"]
                if channel == self.channel and self.shortcut in packet.parsed:
                    result["status"] = packet.parsed[self.shortcut]["raw_value"]

        return result

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            if self.shortcut == "AOT":
                aot = int(value * 10)
                dot = 0xFFFF
            else:
                aot =  0xFFFF
                dot =  int(value * 10)
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0xB,
                destination=self.dev_id,
                IO=self.channel,
                AOT=aot,
                DOT=dot,
            )

    async def async_query_actuator_external_interface_settings(self):
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0xC,
                destination=self.dev_id,
                IO=self.channel,
            )

    async def async_query_actuator_status(self):
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0x3,
                destination=self.dev_id,
                IO=self.channel,
            )
