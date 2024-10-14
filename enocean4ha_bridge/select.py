import logging


from enocean.utils import to_hex_string
from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket

from . import EnOceanGateway
from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.select')


class EO4HASelect:
    _attr_current_option: str|None
    channel: int|None
    dev_id: list[int]
    eep: EEPInfo
    gateway: EnOceanGateway
    select_options_dict: dict
    shortcut: str|None

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"select, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        match self.eep.rorg:
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

        if func == 0x01 and func_type == 0x12 and packet.data[1] == 13:
            packet.parse_eep(rorg_func=func, rorg_type=func_type, command=13)
            if self.shortcut in packet.parsed and self.channel == packet.parsed["IO"]["raw_value"]:
                result["status"] = packet.parsed[self.shortcut]["value"]

        return result

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0xB,
                destination=self.dev_id,
                IO=self.channel,
                **{self.shortcut: self.select_options_dict[option]}
            )

    async def async_query_external_interface_settings(self):
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

    async def async_query_status(self):
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

    async def set_measurement(self, report, mode) -> None:
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            try:
                rm = int(report)
            except ValueError:
                rm = rm
            try:
                ep = int(mode)
            except ValueError:
                ep = mode

            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0x5,
                destination=self.dev_id,
                IO=self.channel,  # 0x1E = all supported channels
                RM=rm,
                ep=ep,
            )

    async def async_query_measurement(self):
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0x6,
                destination=self.dev_id,
                IO=self.channel,
                qu=1
            )
