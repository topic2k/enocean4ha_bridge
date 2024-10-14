import logging
import math
from typing import Any

from enocean.protocol.constants import PACKET, RORG
from enocean.utils import to_hex_string
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.const import CONF_BRIGHTNESS, CONF_STATE

from . import EnOceanGateway
from .common import EEPInfo


class EO4HALight:
    eep: EEPInfo
    dev_id: list[int]
    channel: int
    gateway: EnOceanGateway
    _attr_brightness: int | None
    _logger: logging.Logger

    def turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness)

        if brightness is None:
            brightness = 255

        # TODO: need this to be dependent on the eep?
        bval = math.floor(brightness / 256.0 * 100.0)
        if bval == 0:
            bval = 1

        self.gateway.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=self.eep.rorg,
            rorg_func=self.eep.func,
            rorg_type=self.eep.func_type,
            command=0x01,
            destination=self.dev_id,
            DV=0x00,  # Dim value. 0x00 = switch to new value
            IO=self.channel,  # 0x1E = all supported channels
            OV=bval,  # Output value. 0x64 = ON (=100%)
        )

    # noinspection PyUnusedLocal
    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light source off."""
        self.gateway.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=self.eep.rorg,
            rorg_func=self.eep.func,
            rorg_type=self.eep.func_type,
            command=0x01,
            destination=self.dev_id,
            DV=0x00,  # Dim value. 0x00 = switch to new value
            IO=self.channel,  # 0x1E = all supported channels
            OV=0x00,  # Output value. 0x00 = OFF
        )

    def parse_packet(self, packet):
        self._logger.debug(f"light, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
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
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    result["extra_state_attr"].update({
                        "error_level": packet.parsed["EL"]["value"],
                        "over_current": packet.parsed["OC"]["value"],
                        "power_failure": packet.parsed["PF"]["value"],
                        "power_failure_detection": packet.parsed["PFD"]["value"],
                    })
                    result["status"] = {
                        CONF_BRIGHTNESS: math.floor(output / 100.0 * 256.0),
                        CONF_STATE: bool(output > 0)
                    }

        return result

