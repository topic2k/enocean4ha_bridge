import logging
from typing import Any

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string

from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.switch')


class EO4HASwitch:
    def __init__(self, gateway, dev_id: list[int], eep: list[int], channel: int, loglevel=logging.NOTSET):
        LOGGER.setLevel(loglevel)
        self.gateway = gateway
        self.dev_id = dev_id
        self.eep = EEPInfo(*eep)
        self.channel = channel
        LOGGER.debug(f"EO4HASwitch, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    # noinspection PyUnusedLocal
    def turn_on(self, **kwargs: Any) -> None:
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

    def parse_packet(self, packet: RadioPacket, actual_state):
        if packet.rorg not in [RORG.BS4, RORG.VLD]:
            raise ValueError
        LOGGER.debug(f"switch, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if packet.rorg == RORG.BS4:  # A5
            return self._parse_bs4(packet)
        elif packet.rorg == RORG.VLD:  # D2
            return self._parse_vld(packet)
        raise LookupError

    def _parse_bs4(self, packet):  # A5
        if self.eep.func == 0x12 and self.eep.func_type == 0x01:
            if packet.parsed["DT"]["raw_value"] == 1:  # ==> means meter reading is current value
                watts = packet.parsed["MR"]["raw_value"] / (10 ** packet.parsed["DIV"]["raw_value"])
                if watts > 1:
                    return True, { 'current_value': watts}
                else:
                    return False, { 'current_value': watts}
        raise LookupError

    def _parse_vld(self, packet):  # D2
        if self.eep.func == 0x01:
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    extra_attr = {
                        "error_level": packet.parsed["EL"]["value"],
                        "error_level_raw": packet.parsed["EL"]["raw_value"],
                        "over_current": packet.parsed["OC"]["value"],
                        "over_current_raw": packet.parsed["OC"]["raw_value"],
                        "power_failure": packet.parsed["PF"]["value"],
                        "power_failure_raw": packet.parsed["PF"]["raw_value"],
                        "power_failure_detection": packet.parsed["PFD"]["value"],
                        "power_failure_detection_raw": packet.parsed["PFD"]["raw_value"]
                    }
                    return bool(output > 0), extra_attr
        raise LookupError
