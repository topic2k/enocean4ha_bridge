import logging
import math
from typing import Any

from enocean.protocol.constants import RORG, PACKET
from enocean.utils import to_hex_string
from homeassistant.components.light import ATTR_BRIGHTNESS

from .common import EEPInfo, EO4HAError, EO4HAEEPNotSupportedError

LOGGER = logging.getLogger('enocean.ha.light')


class EO4HALight:
    def __init__(self, gateway, dev_id: list[int], eep: list[int], channel: int, loglevel=logging.NOTSET):
        LOGGER.setLevel(loglevel)
        self.gateway = gateway
        self.dev_id = dev_id
        self.eep = EEPInfo(*eep)
        self.channel = channel
        LOGGER.debug(f"EO4HALight, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    def turn_on(self, actual_brightness, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, actual_brightness)

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
            DV=0x00,
            IO=self.channel,
            OV=bval,
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
            DV=0x00,
            IO=self.channel,
            OV=0x00,
        )

    def parse_packet(self, packet):
        """ Dimmer devices like Eltako FUD61 send telegram in different RORGs.
            We only care about the 4BS (0xA5).
        """
        if packet.rorg not in [RORG.BS4, RORG.VLD]:
            raise ValueError
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        # if packet.rorg == RORG.BS4:  # A5
        #     if  packet.data[1] == 0x02:
        #         val = packet.data[2]
        #         return math.floor(val / 100.0 * 256.0), bool(val != 0)
        if packet.rorg == RORG.VLD:  # D2
            if self.eep.func == 0x01 and self.eep.func_type == 0x12:
                if packet.parsed["CMD"]["raw_value"] == 4:
                    channel = packet.parsed["IO"]["raw_value"]
                    output = packet.parsed["OV"]["raw_value"]
                    if channel == self.channel:
                        return math.floor(output / 100.0 * 256.0), bool(output > 0)
                raise EO4HAError
        raise EO4HAEEPNotSupportedError(self.eep)
