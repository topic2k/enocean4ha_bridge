import concurrent.futures
import os.path
from glob import glob
import logging
import os.path
from glob import glob

from homeassistant.components.enocean.const import CONF_EEP, CONF_MANUFACTURER
from homeassistant.const import CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery_flow
from enocean.communicators import SerialCommunicator
from enocean.protocol.packet import RadioPacket, Packet
from enocean.utils import to_hex_string
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from serial import SerialException
from serial.tools.list_ports import comports
from serial.tools.list_ports_linux import SysFS
from homeassistant import config_entries
from enocean.protocol.constants import MANUFACTURES

from .constants import DOMAIN, SIGNAL_SEND_MESSAGE, SIGNAL_RECEIVE_MESSAGE

LOGGER = logging.getLogger('enocean.ha.gateway')


class EnOceanGateway:
    """Representation of an EnOcean dongle.

    The dongle is responsible for receiving the EnOcean frames,
    creating devices if needed, and dispatching messages to platforms.
    """

    def __init__(self, hass: HomeAssistant, serial_path: str , teach_in_callback=None,  loglevel=logging.NOTSET):
        """Initialize the EnOcean dongle."""
        self._communicator = SerialCommunicator(
            port=serial_path,
            callback=self.callback,
            teach_in_callback=teach_in_callback or self.teach_in_callback,
            loglevel=loglevel
        )
        LOGGER.setLevel(loglevel)
        self.hass: HomeAssistant = hass
        self.dispatcher_disconnect_handle = None

        executor = concurrent.futures.ThreadPoolExecutor(1)
        future_file = executor.submit(SysFS, os.path.realpath(serial_path))
        future_file.add_done_callback(self._get_and_set_device_info)

    def _get_and_set_device_info(self, future_file):
        dev = future_file.result()
        self._manufacturer = dev.manufacturer
        self._product = dev.product
        self._serial_number = dev.serial_number

    @property
    def sender_id(self):
        return self._communicator.base_id

    @property
    def sender_id_str(self) -> str:
        return to_hex_string(self._communicator.base_id)

    @property
    def manufacturer(self) -> str:
        return self._manufacturer

    @property
    def product(self) -> str:
        return self._product

    @property
    def serial_number(self) -> str:
        return self._serial_number

    @property
    def teach_in(self):
        return self._communicator.teach_in

    @teach_in.setter
    def teach_in(self, value):
        self._communicator.teach_in = value

    @classmethod
    def detect(cls):
        """Return a list of candidate paths for USB ENOcean dongles.

        This method is currently a bit simplistic, it may need to be
        improved to support more configurations and OS.
        """
        found_paths = []

        for dev in comports():
            if dev.vid == 0x0403 and dev.pid == 0x6001:
                pattern = f"/dev/serial/by-id/usb-{dev.manufacturer.replace(' ', '_')}_{dev.product.replace(' ', '_')}_{dev.serial_number}-*"
                found_paths.extend(glob(pattern))
        return found_paths

    @classmethod
    def validate_path(cls, path: str):
        """Return True if the provided path points to a valid serial port, False otherwise."""
        try:
            # Creating the serial communicator will raise an exception
            # if it cannot connect
            SerialCommunicator(port=path)
        except SerialException as exception:
            LOGGER.warning(f"Dongle path {path} is invalid: {str(exception)}")
            return False
        return True

    async def load(self):
        """Finish the setup of the bridge and supported platforms."""
        self._communicator.start()
        self.dispatcher_disconnect_handle = async_dispatcher_connect(
            self.hass, SIGNAL_SEND_MESSAGE, self._send_message_callback
        )
        # the following triggers a command to get the base id of the dongle
        _ = self._communicator.base_id
        LOGGER.debug(f"EnOcean gateway id: {to_hex_string(self._communicator.base_id)}")


    def unload(self) -> bool:
        """Disconnect callbacks established at init time."""
        if self.dispatcher_disconnect_handle:
            self.dispatcher_disconnect_handle()
            self.dispatcher_disconnect_handle = None
        self._communicator.stop()
        return True

    def _send_message_callback(self, command):
        """Send a command through the EnOcean dongle."""
        self._communicator.send(command)

    def callback(self, packet):
        """Handle EnOcean device's callback.

        This is the callback function called by python-enocean whenever there
        is an incoming packet.
        """

        if isinstance(packet, RadioPacket):
            dispatcher_send(self.hass, SIGNAL_RECEIVE_MESSAGE, packet)

    def teach_in_callback(self, packet):
        response_packet = packet.create_response_packet(self._communicator.base_id)
        LOGGER.info('Sending response to UTE teach-in.')
        self._communicator.send(response_packet)
        LOGGER.info(
            f"teaching in: {packet.sender_hex}, "
            f"EEP {packet.rorg_of_eep:02X}-{packet.rorg_func:02X}-{packet.rorg_type:02X}, "
            f"Manufacturer: {MANUFACTURES[packet.rorg_manufacturer] if 
            packet.rorg_manufacturer in MANUFACTURES else 'Unknown'} (0x{packet.rorg_manufacturer:02X})"
        )
        async def trigger_discovery_flow():
            discovery_flow.async_create_flow(
                self.hass,
                DOMAIN,
                context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
                data={
                    CONF_ID: packet.sender_hex,
                    CONF_EEP: f"{packet.rorg_of_eep:02X}-{packet.rorg_func:02X}-{packet.rorg_type:02X}",
                    CONF_MANUFACTURER: f"{MANUFACTURES[packet.rorg_manufacturer] if 
                    packet.rorg_manufacturer in MANUFACTURES else 'Unknown'}"
                },
            )
        self.hass.create_task(trigger_discovery_flow())

    def send_command(self, packet_type, rorg, rorg_func, rorg_type, command, **kwargs):
        """Send a command via the EnOcean dongle."""
        LOGGER.info(f"send_command {kwargs=}")
        sender = kwargs.pop('sender', None) or self._communicator.base_id
        packet = Packet.create(
            packet_type=packet_type,
            rorg=rorg,
            rorg_func=rorg_func,
            rorg_type=rorg_type,
            command=command,
            sender=sender,
            **kwargs
        )
        dispatcher_send(self.hass, SIGNAL_SEND_MESSAGE, packet)