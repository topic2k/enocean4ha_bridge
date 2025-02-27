""" Bridge between a Home-Assistant switch component and the enocean python package. """

import logging
from typing import Any

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string

from . import EnOceanGateway
from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.switch')


class EO4HASwitch:
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
        LOGGER.debug(f"switch, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        match packet.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)
            case RORG.VLD:
                return self._parse_d2_packet(packet)

    def _parse_a5_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x12 and func_type == 0x01:
            packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
            if packet.parsed["DT"]["raw_value"] == 1:  # ==> means meter reading is current value
                watts = packet.parsed["MR"]["raw_value"] / (10 ** packet.parsed["DIV"]["raw_value"])
                result["status"] = bool(watts > 1)
                result["extra_state_attr"].update({'current_value': watts})

        return result

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
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    result["status"] = bool(output > 0)
                    result["extra_state_attr"].update({
                        "error_level": packet.parsed["EL"]["value"],
                        "over_current": packet.parsed["OC"]["value"],
                        "power_failure": packet.parsed["PF"]["value"],
                        "power_failure_detection": packet.parsed["PFD"]["value"],
                    })
            elif packet.parsed["CMD"]["raw_value"] == 7:
                LOGGER.debug(packet.parsed)
        return result
