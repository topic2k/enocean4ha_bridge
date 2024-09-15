import logging
from typing import Any

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket

LOGGER = logging.getLogger('enocean.ha.switch')

class EO4HASwitch:
    def __init__(self, controller, dev_id: list[int], channel: int):
        self.controller = controller
        self.dev_id = dev_id
        self.channel = channel

    # noinspection PyUnusedLocal
    def turn_on(self, **kwargs: Any) -> None:
        self.controller.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=RORG.VLD,
            rorg_func=0x01,
            rorg_type=0x0F,
            command=0x1,
            destination=self.dev_id,
            DV=0x00,  # Dim value. 0x00 = switch to new value
            IO=self.channel,  # 0x1E = all supported channels
            OV=0x64,  # Output value. 0x64 = ON (=100%)
        )

    # noinspection PyUnusedLocal
    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        self.controller.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=RORG.VLD,
            rorg_func=0x01,
            rorg_type=0x0F,
            command=0x1,
            destination=self.dev_id,
            DV=0x00,  # Dim value. 0x00 = switch to new value
            IO=self.channel,  # 0x1E = all supported channels
            OV=0x00,  # Output value. 0x00 = OFF
        )

    # def send_command(self, packet_type, rorg, rorg_func, rorg_type, command, **kwargs):
    #     """Send a command via the EnOcean dongle."""
    #     packet = Packet.create(
    #         packet_type=packet_type,
    #         rorg=rorg,
    #         rorg_func=rorg_func,
    #         rorg_type=rorg_type,
    #         command=command,
    #         sender=self.controller.sender_id,
    #         destination=self.dev_id,
    #         **kwargs
    #     )
    #     self.controller.send_packet(packet)

    def parse_packet(self, packet: RadioPacket, actual_state):
        new_state = actual_state
        if packet.rorg == RORG.BS4:
            packet.parse_eep(rorg_func=0x12, rorg_type=0x01)
            if packet.parsed["DT"]["raw_value"] == 1:
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                watts = raw_val / (10**divisor)
                if watts > 1:
                    new_state = True
        elif packet.rorg == RORG.VLD:
            packet.parse_eep(rorg_func=0x01, rorg_type=0x01)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    new_state = output > 0
        return new_state