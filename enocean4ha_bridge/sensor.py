import logging

from enocean.protocol.constants import RORG
from enocean.protocol.packet import RadioPacket
from homeassistant.const import STATE_CLOSED, STATE_OPEN

LOGGER = logging.getLogger('enocean.ha.switch')

class EO4HASensor:
    def __init__(self, controller, dev_id: list[int]):
        self.controller = controller
        self.dev_id = dev_id
        self.scale_min = None
        self.scale_max = None
        self.range_from = None
        self.range_to = None

    @staticmethod
    def parse_illuminance_sensor(packet: RadioPacket):
        """ EEPs (EnOcean Equipment Profiles):
            - A5-07-03 (Occupancy with Supply voltage monitor and 10-bit illumination measurement)
        """
        if packet.rorg != RORG.BS4:
            raise ValueError
        packet.parse_eep(rorg_func=0x07, rorg_type=0x03)
        return packet.parsed["ILL"]["value"]

    @staticmethod
    def parse_occupancy_sensor(packet: RadioPacket):
        """ EEPs (EnOcean Equipment Profiles):
            - A5-07-03 (Automated Meter Reading, Electricity)
        """
        if packet.rorg != RORG.BS4:
            raise ValueError
        packet.parse_eep(rorg_func=0x07, rorg_type=0x03)
        return packet.parsed["PIR"]["value"]
        # return packet.parsed["PIR"]["raw_value"]

    @staticmethod
    def parse_power_sensor(packet: RadioPacket):
        """ EEPs (EnOcean Equipment Profiles):
            - A5-12-01 (Automated Meter Reading, Electricity)
        """
        if packet.rorg != RORG.BS4:
            raise ValueError
        packet.parse_eep(rorg_func=0x12, rorg_type=0x01)
        if packet.parsed["DT"]["raw_value"] == 1:
            # this packet reports the current value
            raw_val = packet.parsed["MR"]["raw_value"]
            divisor = packet.parsed["DIV"]["raw_value"]
            return raw_val / (10.0**divisor)
        raise LookupError

    def parse_temperature_sensor(self, packet: RadioPacket):
        """ EEPs (EnOcean Equipment Profiles):
            - A5-02-01 to A5-02-1B All 8 Bit Temperature Sensors of A5-02
            - A5-10-01 to A5-10-14 (Room Operating Panels)
            - A5-04-01 (Temp. and Humidity Sensor, Range 0°C to +40°C and 0% to 100%)
            - A5-04-02 (Temp. and Humidity Sensor, Range -20°C to +60°C and 0% to 100%)
            - A5-10-10 (Temp. and Humidity Sensor and Set Point)
            - A5-10-12 (Temp. and Humidity Sensor, Set Point and Occupancy Control)
            - 10 Bit Temp. Sensors are not supported (A5-02-20, A5-02-30)

        For the following EEPs the scales must be set to "0 to 250":
            - A5-04-01
            - A5-04-02
            - A5-10-10 to A5-10-14
        """
        if packet.rorg != RORG.BS4:
            raise ValueError
        temp_scale = self.scale_max - self.scale_min
        temp_range = self.range_to - self.range_from
        raw_val = packet.data[3]
        temperature = temp_scale / temp_range * (raw_val - self.range_from)
        temperature += self.scale_min
        return temperature

    @staticmethod
    def parse_humidity_sensor(packet: RadioPacket):
        """ EEPs (EnOcean Equipment Profiles):
            - A5-04-01 (Temp. and Humidity Sensor, Range 0°C to +40°C and 0% to 100%)
            - A5-04-02 (Temp. and Humidity Sensor, Range -20°C to +60°C and 0% to 100%)
            - A5-10-10 to A5-10-14 (Room Operating Panels)
        """

        if packet.rorg != RORG.BS4:
            raise ValueError
        return packet.data[2] * 100.0 / 250.0

    @staticmethod
    def parse_window_handle_sensor(packet: RadioPacket):
        """ EEPs (EnOcean Equipment Profiles):
            - F6-10-00 (Mechanical handle / Hoppe AG)
        """
        action = (packet.data[1] & 0x70) >> 4
        if action == 0x07:
            return STATE_CLOSED
        if action in (0x04, 0x06):
            return STATE_OPEN
        if action == 0x05:
            return "tilt"
        raise LookupError