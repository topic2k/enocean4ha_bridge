import logging
import math
from typing import Any

from enocean.protocol.constants import RORG, PACKET
from homeassistant.components.light import ATTR_BRIGHTNESS

LOGGER = logging.getLogger('enocean.ha.switch')

class EO4HALight:
    def __init__(self, controller, dev_id: list[int], channel: int):
        self.controller = controller
        self.dev_id = dev_id
        self.channel = channel

    def turn_on(self, actual_brightness, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, actual_brightness)

        bval = math.floor(brightness / 256.0 * 100.0)
        if bval == 0:
            bval = 1

        self.controller.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=RORG.VLD,
            rorg_func=0x01,
            rorg_type=0x12,
            command=0x01,
            destination=self.dev_id,
            DV=0x00,
            IO=self.channel,
            OV=bval,
        )

    # noinspection PyUnusedLocal
    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light source off."""
        self.controller.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=RORG.VLD,
            rorg_func=0x01,
            rorg_type=0x12,
            command=0x01,
            destination=self.dev_id,
            DV=0x00,
            IO=self.channel,
            OV=0x00,
        )

    def parse_packet(self, packet, brightness, is_on):
        """ Dimmer devices like Eltako FUD61 send telegram in different RORGs.
            We only care about the 4BS (0xA5).
        """
        if packet.rorg == RORG.BS4 and packet.data[1] == 0x02:
            val = packet.data[2]
            brightness = math.floor(val / 100.0 * 256.0)
            is_on = bool(val != 0)
        if packet.rorg == RORG.VLD:
            packet.parse_eep(rorg_func=0x01, rorg_type=0x12)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    brightness = math.floor(output / 100.0 * 256.0)
                    is_on = output > 0
        return brightness, is_on
