
import logging
import voluptuous as vol
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.valve import ValveDeviceClass
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_MAXIMUM,
    CONF_MINIMUM,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    EntityCategory,
    Platform
)
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode
)
from homeassistant.components.enocean.const import (
    CONF_BUTTON,
    CONF_BUTTONS_AB,
    CONF_COLOR_MODE,
    CONF_DEVICE_TYPE,
    CONF_EEP,
    CONF_MANUFACTURER,
    CONF_MEASUREMENT_MODE,
    CONF_REPORT_MEASUREMENT,
    DEVICE_CLASS_WINDOWHANDLE,
    CONF_CHANNEL_COUNT,
    CONF_CMD_OR_DIR, CONF_PROFILE_SHORTCUT,
    DEVICE_CLASS_PROFILE_SHORTCUT,
)
from homeassistant.components.input_number import CONF_STEP
from homeassistant.components.light import ColorMode
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.data_entry_flow import section


_LOGGER = logging.getLogger(__package__)

binary_device_classes = ['<None>', ]
binary_device_classes.extend(BinarySensorDeviceClass._member_names_)
_binary_device_class_schema_data = {
    vol.Required(CONF_DEVICE_CLASS): SelectSelector(
        SelectSelectorConfig(
            mode=SelectSelectorMode.DROPDOWN,
            multiple=False,
            options=binary_device_classes,
            translation_key=CONF_DEVICE_CLASS,
            sort=True
        ),
    )
}

sensor_device_classes = ['<None>', ]
sensor_device_classes.extend(SensorDeviceClass._member_names_)
_sensor_device_class_schema_data = {
    vol.Required(CONF_DEVICE_CLASS): SelectSelector(
        SelectSelectorConfig(
            mode=SelectSelectorMode.DROPDOWN,
            multiple=False,
            options=sensor_device_classes,
            translation_key=CONF_DEVICE_CLASS,
            sort=True
        ),
    )
}


# noinspection PyUnresolvedReferences
class EO4HAFlowHandler:

    async def get_device_options_schema(self):
        match self._user_input[CONF_EEP]:
            case [0xD2, 0x01, _]:
                return await _get_options_schema_eep_d2_01_all()
            case [0xA5, 0x02 | 0x04 | 0x08, _] | [0xA5, 0x07, 0x03] | [0xA5, 0x20, 0x06] | [0xF6, 0x10, 0x00]:
                return None
            case [0xF6, 0x01, 0x01] | [0xF6, 0x04, 0x01] | [0xD5, 0x00, 0x01]:
                return _binary_device_class_schema_data
            case [0xF6, 0x02, _]:
                return await _get_options_schema_eep_f6_02_all()
            case _:
                raise ValueError(f"EEP {self._user_input[CONF_EEP]} is not yet supported")

    async def get_entry_options_data(self, user_input):
        data = {
            CONF_NAME: self._user_input[CONF_NAME],
            CONF_ID: self._user_input[CONF_ID],
            CONF_EEP: self._user_input[CONF_EEP],
            CONF_MANUFACTURER: '',
        }
        if CONF_MANUFACTURER in self._user_input:
            data[CONF_MANUFACTURER] = self._user_input[CONF_MANUFACTURER]

        match self._user_input[CONF_EEP]:
            case [0xD2, 0x01, _]:
                return await _get_options_data_eep_d2_01_all(data, user_input)
            case [0xA5, 0x02, _]:
                return await _get_options_data_eep_a5_02_all(data)
            case [0xA5, 0x04, _]:
                return await _get_options_data_eep_a5_04_all(data)
            case [0xA5, 0x07, 0x03]:
                return await _get_options_data_eep_a5_07_03(data)
            case [0xA5, 0x08, _]:
                return await _get_options_data_eep_a5_08_all(data)
            case [0xA5, 0x20, 0x06]:
                return await _get_options_data_eep_a5_20_06(data)
            case [0xF6, 0x01, 0x01] | [0xF6, 0x04, 0x01] | [0xD5, 0x00, 0x01]:
                return await _get_options_data_eep_f6_01_01__f6_04_01__d5_00_01(data, user_input)
            case [0xF6, 0x02, _]:
                return await _get_options_data_eep_f6_02_all(data, user_input)
            case [0xF6, 0x10, 0x00]:
                return await _get_options_data_eep_f6_10_00(data)
            case _:
                return self.async_abort(reason=f"No options data for EEP {self._user_input[CONF_EEP]}")


async def _get_options_schema_eep_d2_01_all():
    rm_options = [
        SelectOptionDict(value='0', label="Query only"),
        SelectOptionDict(value='1', label="Query and auto reporting"),
    ]
    ep_options = [
        SelectOptionDict(value='0', label="Energy measurement"),
        SelectOptionDict(value='1', label="Power measurement"),
    ]
    rm_options = [
        SelectOptionDict(value='0', label="Query only"),
        SelectOptionDict(value='1', label="Query and auto reporting"),
    ]
    ep_options = [
        SelectOptionDict(value='0', label="Energy measurement"),
        SelectOptionDict(value='1', label="Power measurement"),
    ]
    data = {
        vol.Required(CONF_DEVICE_TYPE): vol.In([Platform.SWITCH, Platform.LIGHT]),
        vol.Required(CONF_CHANNEL_COUNT): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Required(CONF_REPORT_MEASUREMENT, default='1'): SelectSelector(
            SelectSelectorConfig(
                mode=SelectSelectorMode.DROPDOWN,
                multiple=False,
                options=rm_options,
                translation_key=CONF_REPORT_MEASUREMENT,
                sort=False
            ),
        ),
        vol.Required(CONF_MEASUREMENT_MODE, default='1'): SelectSelector(
            SelectSelectorConfig(
                mode=SelectSelectorMode.DROPDOWN,
                multiple=False,
                options=ep_options,
                translation_key=CONF_MEASUREMENT_MODE,
                sort=False
            ),
        ),
        'light_options': section(
            schema={vol.Optional(CONF_COLOR_MODE): bool},
            options={'collapsed': False}
        ),
    }
    return data

async def _get_options_schema_eep_f6_02_all():
    buttons = [
        SelectOptionDict(value="A0", label="Button A0"),
        SelectOptionDict(value="A1", label="Button A1"),
        SelectOptionDict(value="B0", label="Button B0"),
        SelectOptionDict(value="B1", label="Button B1"),
    ]
    data = _binary_device_class_schema_data
    data.update({
        vol.Required(CONF_BUTTONS_AB): SelectSelector(
            SelectSelectorConfig(
                mode=SelectSelectorMode.LIST,
                multiple=True,
                options=buttons,
                translation_key=CONF_BUTTONS_AB,
            ),
        ),
    })
    return data

async def _get_options_data_eep_d2_01_all(data, user_input):
    data[CONF_CHANNEL_COUNT] = user_input[CONF_CHANNEL_COUNT]
    data[CONF_REPORT_MEASUREMENT] = user_input[CONF_REPORT_MEASUREMENT]
    data[CONF_MEASUREMENT_MODE] = user_input[CONF_MEASUREMENT_MODE]
    if user_input[CONF_DEVICE_TYPE] == Platform.LIGHT:
        colormode = ColorMode.BRIGHTNESS if user_input[CONF_COLOR_MODE] else ColorMode.ONOFF
        data[CONF_ENTITIES] = {Platform.LIGHT: [{CONF_COLOR_MODE: colormode}, ], }
    else:
        data[CONF_ENTITIES] = {Platform.SWITCH: [{CONF_DEVICE_CLASS: SwitchDeviceClass.SWITCH}], }
    data[CONF_ENTITIES].update({
        Platform.BUTTON: [
            # {CONF_NAME: 'Query Actuator Measurement', CONF_COMMAND: {"CMD": 6}},
            {CONF_PROFILE_SHORTCUT: "RE", CONF_CMD_OR_DIR: {"command": 5}},
        ],
        Platform.NUMBER: [
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "AOT",
             CONF_CMD_OR_DIR: {"command": 13}, CONF_MINIMUM: 0.0, CONF_MAXIMUM: 6553.5, CONF_STEP: 0.1,
             CONF_UNIT_OF_MEASUREMENT: 's'},
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "DOT",
             CONF_CMD_OR_DIR: {"command": 13}, CONF_MINIMUM: 0.0, CONF_MAXIMUM: 6553.5, CONF_STEP: 0.1,
             CONF_UNIT_OF_MEASUREMENT: 's'},
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "MAT",
             CONF_CMD_OR_DIR: {"command": 5}, CONF_MINIMUM: 0, CONF_MAXIMUM: 2550, CONF_STEP: 1,
             CONF_UNIT_OF_MEASUREMENT: 's'},
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "MIT",
             CONF_CMD_OR_DIR: {"command": 5}, CONF_MINIMUM: 0, CONF_MAXIMUM: 255, CONF_STEP: 1,
             CONF_UNIT_OF_MEASUREMENT: 's'},
        ],
        Platform.SELECT: [
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 11},
             CONF_PROFILE_SHORTCUT: "EBM"},
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 11},
             CONF_PROFILE_SHORTCUT: "SWT"},
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 5},
             CONF_PROFILE_SHORTCUT: "RM", 'default': user_input[CONF_REPORT_MEASUREMENT]},
            {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 5},
             CONF_PROFILE_SHORTCUT: "ep", 'default': user_input[CONF_MEASUREMENT_MODE]},
        ],
        Platform.SENSOR: [
            {CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_DEVICE_CLASS: SensorDeviceClass.ENERGY},
            {CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_DEVICE_CLASS: SensorDeviceClass.POWER},
        ],
    })
    return data

async def _get_options_data_eep_a5_02_all(data):
    data[CONF_ENTITIES] = {
        Platform.SENSOR: [{CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE}],
    }
    return data

async def _get_options_data_eep_a5_04_all(data):
    data[CONF_ENTITIES] = {
        Platform.SENSOR: [
            {CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
            {CONF_DEVICE_CLASS: SensorDeviceClass.HUMIDITY}
        ],
    }
    return data

async def _get_options_data_eep_a5_07_03(data):
    data[CONF_ENTITIES] = {
        Platform.SENSOR: [{CONF_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE}],
        Platform.BINARY_SENSOR: [{CONF_DEVICE_CLASS: BinarySensorDeviceClass.MOTION}]
    }
    return data

async def _get_options_data_eep_a5_08_all(data):
    data[CONF_ENTITIES] = {
        Platform.SENSOR: [
            {CONF_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE},
            {CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
        ],
        Platform.BINARY_SENSOR: [
            {CONF_DEVICE_CLASS: BinarySensorDeviceClass.MOTION},
            {CONF_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY},
        ]
    }
    return data

async def _get_options_data_eep_a5_20_06(data):
    data[CONF_ENTITIES] = {
        Platform.VALVE: [
            {CONF_DEVICE_CLASS: ValveDeviceClass.WATER},
        ],
        Platform.SENSOR: [
            {CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "LOM"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "LO"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "TSL"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "ENIE"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "ES"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "RCE"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "RSS"},
            {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
             CONF_PROFILE_SHORTCUT: "ACO"},
        ],
        Platform.BINARY_SENSOR: [
            {CONF_DEVICE_CLASS: BinarySensorDeviceClass.WINDOW, CONF_PROFILE_SHORTCUT: "DWO"},
        ],
    }
    return data

async def _get_options_data_eep_f6_01_01__f6_04_01__d5_00_01(data, user_input):
    data[CONF_ENTITIES] = {
        Platform.BINARY_SENSOR: [{CONF_DEVICE_CLASS: user_input[CONF_DEVICE_CLASS]}]
    }
    return data

async def _get_options_data_eep_f6_02_all(data, user_input):
    data[CONF_ENTITIES] = {
        Platform.BINARY_SENSOR: [
            {CONF_DEVICE_CLASS: None, CONF_BUTTON: "A0", CONF_ENABLED: "A0" in user_input[CONF_BUTTONS_AB]},
            {CONF_DEVICE_CLASS: None, CONF_BUTTON: "A1", CONF_ENABLED: "A1" in user_input[CONF_BUTTONS_AB]},
            {CONF_DEVICE_CLASS: None, CONF_BUTTON: "B0", CONF_ENABLED: "B0" in user_input[CONF_BUTTONS_AB]},
            {CONF_DEVICE_CLASS: None, CONF_BUTTON: "B1", CONF_ENABLED: "B1" in user_input[CONF_BUTTONS_AB]},
        ],
    }
    return data

async def _get_options_data_eep_f6_10_00(data):
    data[CONF_ENTITIES] = {
        Platform.SENSOR: [{CONF_DEVICE_CLASS: DEVICE_CLASS_WINDOWHANDLE}, ],
    }
    return data
