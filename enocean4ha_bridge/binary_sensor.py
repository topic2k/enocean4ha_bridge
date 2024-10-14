import logging

from enocean.protocol.constants import RORG
from enocean.utils import to_hex_string
from enocean.protocol.packet import RadioPacket


from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.binary_sensor')


class EO4HABinarySensor:
    def __init__(self, gateway, dev_id: list[int], eep: list[int], button: str | None, loglevel=logging.NOTSET):
        LOGGER.setLevel(loglevel)
        self.gateway = gateway
        self.dev_id = dev_id
        self.eep = EEPInfo(*eep)
        self.button = ["A1", "A0", "B1", "B0"].index(button.upper()) if button else 4
        LOGGER.debug(f"EO4HABinarySensor, {repr(self.eep)}, Device-ID: {to_hex_string(dev_id)}, Button: {button}")

    def parse_packet(self, packet: RadioPacket, actual_which, actual_onoff, shortcut: str):
        """ This method is called when there is an incoming packet
            associated with this platform.

            Example packet data:
                - 2nd button pressed
                    ['0xF6', '0x10', '0x00', '0x2d', '0xcf', '0x45', '0x30']
                - button released
                    ['0xF6', '0x00', '0x00', '0x2d', '0xcf', '0x45', '0x20']
        """
        LOGGER.debug(repr(self.eep))

        match packet.rorg:
            case RORG.RPS:
                return self._parse_f6_packet(packet)
            case RORG.BS1:
                return self._parse_d5_packet(packet)
            case RORG.BS4:
                return self._parse_a5_packet(packet, shortcut)

        # TODO: following is for compatibility with integration before 2024.
        #       Maybe deprecate and remove in future release? (topic2k, Oct 2024)
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

        return {
            "legacy": (pushed, which, onoff),
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

    def _parse_f6_packet(self, packet: RadioPacket):
        func = self.eep.func
        func_type = self.eep.func_type
        packet.parse_eep(rorg_func=func, rorg_type=func_type)
        parsed = packet.parsed
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x01 and func_type == 0x01:
            result["status"] = parsed["PB"]["raw_value"]
        elif func == 0x02 and func_type in [0x01, 0x02] and self.button < 4:
            if (
                    parsed["R1"]["raw_value"] == self.button
                    and parsed["T21"]["raw_value"] == 1
                    and parsed["NU"]["raw_value"] == 1
            ):
                result["status"] = parsed["EB"]["raw_value"]
        elif func == 0x02 and func_type == 0x03 and self.button < 4:
            if parsed["T21"]["raw_value"] == 1 and parsed["NU"]["raw_value"] == 1:
                result["status"] = 0
                if "RA" in parsed:
                    buttons = {
                        0x10: 0,
                        0x30: 1,
                        0x50: 2,
                        0x70: 3
                    }
                    if buttons[parsed["RA"]["raw_value"]] == self.button:
                        result["status"] = 1
        elif func == 0x02 and func_type == 0x03 and self.button < 4:
            key = ("RAI", "RA0", "RBI", "RB0")[self.button]
            result["status"] = parsed[key]["raw_value"]
        elif func == 0x04 and func_type == 0x01 and self.button < 4:
            if "KC" in parsed:
            #     if parsed["T21"]["raw_value"] == 1 and parsed["NU"]["raw_value"] == 1:
            #         print("ON")
            #         result["status"] = 1
            #     elif parsed["T21"]["raw_value"] == 1 and parsed["NU"]["raw_value"] == 0:
            #         result["status"] = 0
            #         print("OFF")
                result["status"] = 1 if parsed["KC"]["value"] == "inserted" else 0
        return result

    def _parse_d5_packet(self, packet: RadioPacket):
        func = self.eep.func
        func_type = self.eep.func_type
        packet.parse_eep(rorg_func=func, rorg_type=func_type)
        parsed = packet.parsed
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }
        if func == 0x00 and func_type == 0x01:
            if "CO" in parsed:
                result["status"] = not bool(parsed["CO"]["raw_value"])
        return result

    def _parse_a5_packet(self, packet: RadioPacket, shortcut: str):
        func = self.eep.func
        func_type = self.eep.func_type
        parsed = packet.parsed
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }
        if func == 0x07 and func_type == 0x03:
            packet.parse_eep(rorg_func=func, rorg_type=func_type)
            if "PIRS" in parsed:
                result["status"] = bool(parsed["PIRS"]["raw_value"])
        elif func == 0x20 and func_type == 0x06:
            packet.parse_eep(rorg_func=func, rorg_type=func_type, direction=1)
            if shortcut in packet.parsed:
                result["status"] = packet.parsed[shortcut]["raw_value"]
                result["extra_state_attr"]["raw_value"] = packet.parsed[shortcut]["raw_value"]

        return result
