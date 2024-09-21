import logging

from enocean.protocol.constants import RORG
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string
from homeassistant.const import STATE_CLOSED, STATE_OPEN

from .common import EEPInfo

LOGGER = logging.getLogger('enocean.ha.sensor')


class EO4HASensor:
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        LOGGER.setLevel(loglevel)
        self.gateway = gateway
        self.dev_id = dev_id
        self.eep = EEPInfo(*eep)


class EO4HAHumiditySensor(EO4HASensor):
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        super().__init__(gateway, dev_id, eep, loglevel)
        LOGGER.debug(f"EO4HAHumiditySensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        if self.eep.rorg == RORG.BS4 and self.eep.func in [0x04, 0x10]:
            self._set_range_and_scale_from_eep()

    def _set_range_and_scale_from_eep(self):
        from enocean.protocol.eep import EEP
        all_eep = EEP()
        profile = all_eep.telegrams[self.eep.rorg][self.eep.func][self.eep.func_type]
        hum_data = profile.find(shortcut='HUM')
        hum_range = hum_data.find('range')
        self.range_min = float(hum_range.find('min').contents[0])
        self.range_max = float(hum_range.find('max').contents[0])
        hum_scale = hum_data.find('scale')
        self.scale_min = float(hum_scale.find('min').contents[0])
        self.scale_max = float(hum_scale.find('max').contents[0])

    def parse_humidity_sensor(self, packet: RadioPacket):
        if packet.rorg != RORG.BS4:
            raise ValueError
        LOGGER.debug(f"humidity, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func  in [0x04, 0x10]:
            temp_scale = self.scale_max - self.scale_min
            temp_range = self.range_max - self.range_min
            return (temp_scale / temp_range) * (packet.parsed["HUM"]["raw_value"] - self.range_min) + self.scale_min
        raise LookupError


class EO4HAIlluminanceSensor(EO4HASensor):
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        super().__init__(gateway, dev_id, eep, loglevel)
        LOGGER.debug(f"EO4HAIlluminanceSensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    def parse_illuminance_sensor(self, packet: RadioPacket):
        if packet.rorg != RORG.BS4:
            raise ValueError
        LOGGER.debug(f"illuminance_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func == 0x07 and self.eep.func_type == 0x03:
            return packet.parsed["ILL"]["value"]
        raise LookupError


class EO4HAOccupancySensor(EO4HASensor):
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        super().__init__(gateway, dev_id, eep, loglevel)
        LOGGER.debug(f"EO4HAOccupancySensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    def parse_occupancy_sensor(self, packet: RadioPacket):
        if packet.rorg != RORG.BS4:
            raise ValueError
        LOGGER.debug(f"occupancy_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func == 0x07 and self.eep.func_type == 0x03:
            return packet.parsed["PIR"]["value"], {"raw_value": packet.parsed["PIR"]["raw_value"]}
        raise LookupError


class EO4HAPowerSensor(EO4HASensor):
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        super().__init__(gateway, dev_id, eep, loglevel)
        LOGGER.info(f"EO4HAPowerSensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    def parse_power_sensor(self, packet: RadioPacket):
        if packet.rorg != RORG.BS4:
            raise ValueError
        LOGGER.debug(f"power_sensor, {repr(self.eep)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func == 0x12 and self.eep.func_type == 0x01:
            if packet.parsed["DT"]["raw_value"] == 1:
                # this packet reports the current value
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                return raw_val / (10.0**divisor)
        raise LookupError


class EO4HATemperatureSensor(EO4HASensor):
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        super().__init__(gateway, dev_id, eep, loglevel)
        LOGGER.debug(f"EO4HATemperatureSensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        if self.eep.rorg == RORG.BS4 and self.eep.func in [0x04, 0x08, 0x10]:
            self._set_range_and_scale_from_eep()

    def _set_range_and_scale_from_eep(self):
        from enocean.protocol.eep import EEP
        all_eep = EEP()
        profile = all_eep.telegrams[self.eep.rorg][self.eep.func][self.eep.func_type]
        tmp_data = profile.find(shortcut='TMP')
        tmp_range = tmp_data.find('range')
        self.range_min = float(tmp_range.find('min').contents[0])
        self.range_max = float(tmp_range.find('max').contents[0])
        tmp_scale = tmp_data.find('scale')
        self.scale_min = float(tmp_scale.find('min').contents[0])
        self.scale_max = float(tmp_scale.find('max').contents[0])

    def parse_temperature_sensor(self, packet: RadioPacket):
        if packet.rorg != RORG.BS4:  # A5
            raise ValueError
        LOGGER.debug(f"temperature_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func == 0x02:
            return packet.parsed["TMP"]["value"]
        elif self.eep.func in [0x04, 0x08, 0x10]:
            temp_scale = self.scale_max - self.scale_min
            temp_range = self.range_max - self.range_min
            return (temp_scale / temp_range) * (packet.parsed["TMP"]["raw_value"] - self.range_min) + self.scale_min
        raise LookupError


class EO4HAWindowHandleSensor(EO4HASensor):
    def __init__(self, gateway, dev_id: list[int], eep: list[int], loglevel=logging.NOTSET):
        super().__init__(gateway, dev_id, eep, loglevel)
        LOGGER.debug(f"EO4HAWindowHandleSensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")

    def parse_window_handle_sensor(self, packet: RadioPacket):
        if packet.rorg != RORG.RPS:  # F6
            raise ValueError
        LOGGER.debug(f"window_handle_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        if self.eep.func == 0x10:
            action = (packet.data[1] & 0x70) >> 4
            if action == 0x07:
                return STATE_CLOSED
            if action in (0x04, 0x06):
                return STATE_OPEN
            if action == 0x05:
                return "tilt"
        raise LookupError
