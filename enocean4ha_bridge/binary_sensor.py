import logging

LOGGER = logging.getLogger('enocean.ha.switch')

class EO4HABinarySensor:
    def __init__(self, controller, dev_id: list[int]):
        self.controller = controller
        self.dev_id = dev_id

    @staticmethod
    def parse_packet(packet, actual_which, actual_onoff):
        """ This method is called when there is an incoming packet
            associated with this platform.

            Example packet data:
                - 2nd button pressed
                    ['0xf6', '0x10', '0x00', '0x2d', '0xcf', '0x45', '0x30']
                - button released
                    ['0xf6', '0x00', '0x00', '0x2d', '0xcf', '0x45', '0x20']
        """
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