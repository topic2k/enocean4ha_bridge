import logging

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string
from homeassistant.const import STATE_CLOSED, STATE_OPEN

from enocean4ha_bridge import EnOceanGateway
from .common import EEPInfo
from .constants import STATE_TILT

LOGGER = logging.getLogger('enocean.ha.sensor')


class EO4HASensor:
    """ Base class for all EO4HA sensors """
    channel: int
    dev_id: list[int]
    eep: EEPInfo
    gateway: EnOceanGateway

    def parse_packet(self, packet: RadioPacket):
        pass

    async def async_query_actuator_measurement(self, query: [0|1]):
        # 0 = query energy
        # 1 = query power
        if self.eep.rorg == RORG.VLD and self.eep.func == 0x1:
            self.gateway.send_command(
                packet_type=PACKET.RADIO_ERP1,
                rorg=self.eep.rorg,
                rorg_func=self.eep.func,
                rorg_type=self.eep.func_type,
                command=0x6,
                destination=self.dev_id,
                IO=self.channel,
                qu=query,
            )


class EO4HAEnergySensor(EO4HASensor):
    channel: int

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"energy_sensor, {repr(self.eep)}")
        match packet.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)
            case RORG.VLD:
                return self._parse_d2_packet(packet)

    def _parse_a5_packet(self, packet):
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func == 0x12 and self.eep.func_type == 0x01:
            if packet.parsed["DT"]["raw_value"] == 1:
                # this packet reports the current value
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                result["status"] =  raw_val / (10.0**divisor)
        return result

    def _parse_d2_packet(self, packet):
        func = self.eep.func
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x01 and packet.data[1] == 0x7:
            packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type, command=packet.data[1])
            channel = packet.parsed["IO"]["raw_value"]
            if channel == self.channel and packet.parsed["UN"]["raw_value"] in [0x00, 0x01, 0x02]:
                result["status"] = packet.parsed["MV"]["value"]
                result["extra_state_attr"]["unit"] = packet.parsed["UN"]["value"]
        return result


class EO4HAHumiditySensor(EO4HASensor):

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"humidity, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        match self.eep.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)

    def _parse_a5_packet(self, packet):
        func = self.eep.func
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func  in [0x04, 0x10]:
            result["status"] = packet.parsed["HUM"]["value"]

        return result


class EO4HAIlluminanceSensor(EO4HASensor):

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"illuminance_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        match self.eep.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)

    def _parse_a5_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        match func:
            case 0x08 | 0x07 if func_type == 0x03:
                result["status"] = packet.parsed["ILL"]["value"]

        return result


class EO4HAPowerSensor(EO4HASensor):
    channel: int

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"power_sensor, {repr(self.eep)}")
        match packet.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)
            case RORG.VLD:
                return self._parse_d2_packet(packet)

    def _parse_a5_packet(self, packet):
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        if self.eep.func == 0x12 and self.eep.func_type == 0x01:
            if packet.parsed["DT"]["raw_value"] == 1:
                # this packet reports the current value
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                result["status"] = raw_val / (10.0**divisor)
        return result

    def _parse_d2_packet(self, packet):
        func = self.eep.func
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }
        if func == 0x01 and packet.data[1] == 0x7:
            packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type, command=packet.data[1])
            channel = packet.parsed["IO"]["raw_value"]
            if channel == self.channel and packet.parsed["UN"]["raw_value"] in [0x03, 0x04]:
                result["status"] = packet.parsed["MV"]["value"]
                result["extra_state_attr"]["unit"] = packet.parsed["UN"]["value"]
        return result


class EO4HATemperatureSensor(EO4HASensor):

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"temperature_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        match self.eep.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)

    def _parse_a5_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func in [0x02, 0x08] or (func == 0x04 and func_type in [0x03, 0x04]) or (func == 0x10 and func_type in [*range(0x01,0x1E), *range(0x20,0x23)]):
            packet.parse_eep(rorg_func=func, rorg_type=func_type)
            result["status"] = packet.parsed["TMP"]["value"]
        elif func == 0x04 and func_type in [0x01, 0x02]:
            packet.parse_eep(rorg_func=func, rorg_type=func_type)
            if packet.parsed["TSN"]["raw_value"] == 1:
                result["status"] = packet.parsed["TMP"]["value"]
        elif func == 0x10 and func_type == 0x1F:
            packet.parse_eep(rorg_func=func, rorg_type=func_type)
            if packet.parsed["TMP_F"]["raw_value"] == 1:
                result["status"] = packet.parsed["TMP"]["value"]
        elif func == 0x20 and func_type == 0x06:
            packet.parse_eep(rorg_func=func, rorg_type=func_type, direction=1)
            if packet.parsed["TSL"]["raw_value"] == 0:
                range_min = 0.0; range_max = 80.0
                scale_min =0.0; scale_max = 40.0
            else:
                range_min = 0.0; range_max = 16.0
                scale_min = 0.0; scale_max = 80.0
            temp_scale = float(scale_max - scale_min)
            temp_range = float(range_max - range_min)
            result["status"] = (temp_scale / temp_range) * (float(packet.parsed["TMP"]["raw_value"]) - range_min) + scale_min

        return result


class EO4HAWindowHandleSensor(EO4HASensor):

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"window_handle_sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        packet.parse_eep(rorg_func=self.eep.func, rorg_type=self.eep.func_type)
        match self.eep.rorg:
            case RORG.RPS:
                return self._parse_f6_packet(packet)

    def _parse_f6_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x10:
            action = (packet.data[1] & 0x70) >> 4
            if action == 0x07:
                result["status"] = STATE_CLOSED
            elif action in (0x04, 0x06):
                result["status"] = STATE_OPEN
            elif action == 0x05:
                result["status"] = STATE_TILT

        return result


class EO4HAShortcutSensor(EO4HASensor):

    shortcut: str|None = None

    def parse_packet(self, packet: RadioPacket):
        LOGGER.debug(f"Shortcut-Sensor, {repr(self.eep)}, Device-ID: {to_hex_string(self.dev_id)}")
        match packet.rorg:
            case RORG.BS4:
                return self._parse_a5_packet(packet)

    def _parse_a5_packet(self, packet):
        func = self.eep.func
        func_type = self.eep.func_type
        result = {
            "extra_state_attr": {
                "dBm": packet.dBm,
                "repeater_count": packet.repeater_count
            }
        }

        if func == 0x20 and func_type == 0x06:
            packet.parse_eep(rorg_func=func, rorg_type=func_type, direction=1)
            if self.shortcut in packet.parsed:
                if self.shortcut == "LO" and packet.parsed["LOM"]["raw_value"] == 1:
                    range_min = 0.0
                    range_max = 80.0
                    scale_min = 0.0
                    scale_max = 40.0
                    temp_scale = float(scale_max - scale_min)
                    temp_range = float(range_max - range_min)
                    val = (temp_scale / temp_range) * (
                                float(packet.parsed["LO"]["raw_value"]) - range_min) + scale_min
                    result["status"] = f"{val} °C"
                elif self.shortcut == "LO" and packet.parsed["LOM"]["raw_value"] == 0:
                    val = packet.parsed["LO"]["raw_value"]
                    result["status"] = f"{val if val <= 5 else val - 128} °C"
                else:
                    result["status"] = packet.parsed[self.shortcut]["value"]
                result["extra_state_attr"]["raw_value"] = packet.parsed[self.shortcut]["raw_value"]

        return result
