import logging

from enocean.utils import to_hex_string

from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.binary_sensor')


class EO4HABinarySensor:
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        LOGGER.setLevel(loglevel)
        self.gateway = gateway
        self.dev_id = dev_id
        self.eep = EEPInfo(*eep)
        LOGGER.debug(f"EO4HALight, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    def parse_packet(self, packet, actual_which, actual_onoff):
        """ This method is called when there is an incoming packet
            associated with this platform.

            Example packet data:
                - 2nd button pressed
                    ['0xf6', '0x10', '0x00', '0x2d', '0xcf', '0x45', '0x30']
                - button released
                    ['0xf6', '0x00', '0x00', '0x2d', '0xcf', '0x45', '0x20']
        """
        LOGGER.debug(repr(self.eep))
        if packet.data[6] == 0x30:
            pushed = 1
        elif packet.data[6] == 0x20:
            pushed = 0
        else:
            pushed = None

        action = packet.data[1]
        if action == 0x70:
            which = 0
            onoff = 0
        elif action == 0x50:
            which = 0
            onoff = 1
        elif action == 0x30:
            which = 1
            onoff = 0
        elif action == 0x10:
            which = 1
            onoff = 1
        elif action == 0x37:
            which = 10
            onoff = 0
        elif action == 0x15:
            which = 10
            onoff = 1
        else:
            which = actual_which
            onoff = actual_onoff

        return pushed, which, onoff