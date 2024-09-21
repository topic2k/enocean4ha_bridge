import logging
from os.path import basename, normpath

from enocean.communicators import SerialCommunicator
from enocean.protocol.constants import PACKET, RETURN_CODE
from enocean.protocol.packet import RadioPacket, ResponsePacket, Packet
from enocean.utils import to_hex_string
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send

from .constants import SIGNAL_SEND_MESSAGE, SIGNAL_RECEIVE_MESSAGE

LOGGER = logging.getLogger('enocean.ha.gateway')


class EnOceanGateway:
    """Representation of an EnOcean dongle.

    The dongle is responsible for receiving the EnOcean frames,
    creating devices if needed, and dispatching messages to platforms.
    """

    def __init__(self, hass, serial_path, loglevel=logging.NOTSET):
        """Initialize the EnOcean dongle."""
        LOGGER.setLevel(loglevel)
        self._communicator = SerialCommunicator(port=serial_path, callback=self.callback, loglevel=loglevel)
        LOGGER.setLevel(loglevel)
        # self.serial_path = serial_path
        # self.identifier = basename(normpath(serial_path))
        self.hass = hass
        self.dispatcher_disconnect_handle = None

    @property
    def sender_id(self):
        return self._communicator.base_id

    @property
    def sender_id_str(self):
        return to_hex_string(self._communicator.base_id)

    async def async_setup(self):
        """Finish the setup of the bridge and supported platforms."""
        self._communicator.start()
        self.dispatcher_disconnect_handle = async_dispatcher_connect(
            self.hass, SIGNAL_SEND_MESSAGE, self._send_message_callback
        )
        # the following triggers a command to get the base id of the dongle
        _ = self._communicator.base_id

    def unload(self):
        """Disconnect callbacks established at init time."""
        if self.dispatcher_disconnect_handle:
            self.dispatcher_disconnect_handle()
            self.dispatcher_disconnect_handle = None

    def _send_message_callback(self, command):
        """Send a command through the EnOcean dongle."""
        self._communicator.send(command)

    def callback(self, packet):
        """Handle EnOcean device's callback.

        This is the callback function called by python-enocan whenever there
        is an incoming packet.
        """

        if isinstance(packet, RadioPacket):
            dispatcher_send(self.hass, SIGNAL_RECEIVE_MESSAGE, packet)
        elif isinstance(packet, ResponsePacket):
            if (
                packet.packet_type == PACKET.RESPONSE
                and packet.response == RETURN_CODE.OK
                and len(packet.response_data) == 4
            ):
                # Base ID is set from the response data.
                self._communicator.base_id = packet.response_data
                LOGGER.info(f"gateway id: {to_hex_string(self._communicator.base_id)}")

    def send_command(self, packet_type, rorg, rorg_func, rorg_type, command, **kwargs):
        """Send a command via the EnOcean dongle."""
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