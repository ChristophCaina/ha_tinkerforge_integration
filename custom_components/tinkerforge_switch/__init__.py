"""Support for Tinkerforge Remote Switch."""
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (CONF_HOST, CONF_PORT,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP)
from tinkerforge.bricklet_remote_switch_v2 import BrickletRemoteSwitchV2
from tinkerforge.ip_connection import IPConnection

DOMAIN = 'tinkerforge_switch'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

CONF_REPEATS = 'repeats'
CONF_UID = 'uid'
CONF_REMOTE_TYPE = 'remote_type'

_LOGGER = logging.getLogger(__name__)

TINKERFORGE_PLATFORMS = ['switch']

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST, default='localhost'): cv.string,
                vol.Optional(CONF_PORT, default=4223): cv.port,
                vol.Required(CONF_UID): cv.string,
                vol.Required(CONF_REMOTE_TYPE): vol.All(
                    cv.string,
                    vol.Any('A', 'B', 'C'),
                ),
                vol.Optional(CONF_REPEATS, default=5): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set up the tinkerforge component."""
    conf = config[DOMAIN]

    def cleanup(event):
        """Stuff to do before stopping."""
        _LOGGER.debug(DOMAIN + ' Cleanup')
        ipcon.disconnect()

    def prepare(event):
        """Stuff to do when Home Assistant starts."""
        _LOGGER.debug(DOMAIN + ' Prepare')
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, cleanup)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, prepare)
    host = conf[CONF_HOST]
    port = conf[CONF_PORT]
    repeats = conf[CONF_REPEATS]
    uid = conf[CONF_UID]

    remote_types = {
        'A': BrickletRemoteSwitchV2.REMOTE_TYPE_A,
        'B': BrickletRemoteSwitchV2.REMOTE_TYPE_B,
        'C': BrickletRemoteSwitchV2.REMOTE_TYPE_C
    }
    remote_type = remote_types.get(conf.get(CONF_REMOTE_TYPE))

    # Setup connection with devices: Create IP connection
    ipcon = IPConnection()
    rs = BrickletRemoteSwitchV2(uid, ipcon)  # Create device object

    ipcon.connect(host, port)  # Connect to brickd
    rs.set_repeats(repeats)

    # Verify that passed in configuration works
    if ipcon.get_connection_state() != ipcon.CONNECTION_STATE_CONNECTED:
        _LOGGER.error('Could not connect to tinkerforge hub')
        return

    hass.data[DOMAIN] = ipcon
    hass.data[DOMAIN + '_rs'] = rs
    hass.data[DOMAIN + '_remote_type'] = remote_type

    def cb_remote_status(house_code, receiver_code, switch_to, repeats):
        _LOGGER.debug(
            "Callback: "
            + str(house_code)
            + " - "
            + str(receiver_code)
            + " - "
            + str(switch_to)
        )
        switch = hass.data.get(
            DOMAIN + "_" + str(house_code) + "_" + str(receiver_code)
        )
        if not switch:
            return
        switch.set_switch_state(switch_to)

    # Configure to receive from remote type A with minimum repeats set to 1 and enable callback
    rs.set_remote_configuration(remote_type, 1, True)

    remote_callback_types = {
        BrickletRemoteSwitchV2.REMOTE_TYPE_A: BrickletRemoteSwitchV2.CALLBACK_REMOTE_STATUS_A,
        BrickletRemoteSwitchV2.REMOTE_TYPE_B: BrickletRemoteSwitchV2.CALLBACK_REMOTE_STATUS_B,
        BrickletRemoteSwitchV2.REMOTE_TYPE_C: BrickletRemoteSwitchV2.CALLBACK_REMOTE_STATUS_C,
    }

    # Register remote status a callback to function cb_remote_status_a
    rs.register_callback(remote_callback_types[remote_type], cb_remote_status)

    return True
