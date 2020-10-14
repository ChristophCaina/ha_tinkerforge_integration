"""Platform for tinkerforge remote switch integration."""
import logging
from typing import Callable, Optional, Sequence

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
# Import the device class from the component that you want to support
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (CONF_FRIENDLY_NAME, CONF_ICON, CONF_ID,
                                 CONF_SWITCHES, DEVICE_CLASS_POWER)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (ConfigType, DiscoveryInfoType,
                                          HomeAssistantType)
from homeassistant.util import slugify
from tinkerforge.bricklet_remote_switch_v2 import BrickletRemoteSwitchV2

from . import DOMAIN, ENTITY_ID_FORMAT

CONF_HOUSE_CODE = 'house_code'
CONF_RECEIVER_CODE = 'receiver_code'

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SWITCHES): vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required(CONF_ID): cv.string,
                    vol.Required(CONF_HOUSE_CODE): cv.positive_int,
                    vol.Required(CONF_RECEIVER_CODE): cv.positive_int,
                    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
                    vol.Optional(CONF_ICON): cv.string,
                }
            ],
        )
    }
)


async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, add_entities: Callable[[Sequence[Entity], bool], None],
                               discovery_info: Optional[DiscoveryInfoType] = None) -> None:
    """Set up the switch platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    rs = hass.data.get(DOMAIN + '_rs')
    if not rs:
        return False

    switches = config.get(CONF_SWITCHES)

    entities = []
    for switch_cfg in switches:
        switch = RemoteSwitch(
                switch_cfg[CONF_ID],
                rs,
                hass.data[DOMAIN + '_remote_type'],
                switch_cfg.get(CONF_HOUSE_CODE),
                switch_cfg.get(CONF_RECEIVER_CODE),
                switch_cfg.get(CONF_FRIENDLY_NAME),
                switch_cfg.get(CONF_ICON))
        hass.data[DOMAIN + '_' + str(switch_cfg.get(CONF_HOUSE_CODE)) + '_' + str(switch_cfg.get(CONF_RECEIVER_CODE))] = switch
        entities.append(switch)

    add_entities(entities, True)


class RemoteSwitch(SwitchEntity):
    """Representation of a tinkerforge switch."""

    def __init__(self, name, rs, remote_type, house_code, receiver_code, friendly_name, icon):
        """Initialize an tinkerforge switch."""
        self._name = name
        self._rs = rs
        self._remote_type = remote_type
        self._house_code = house_code
        self._receiver_code = receiver_code
        self._state = False
        self._friendly_name = friendly_name
        self._icon = icon

    @property
    def assumed_state(self):
        return True

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """Return the display name of this switch."""
        return self._name

    @property
    def friendly_name(self):
        """Return the display name of this switch."""
        return self._friendly_name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    @property
    def device_class(self):
        return DEVICE_CLASS_POWER

    def turn_on(self, **kwargs):
        """Instruct the switch to turn on.
        """
        self.__switch(BrickletRemoteSwitchV2.SWITCH_TO_ON)

    def turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        self.__switch(BrickletRemoteSwitchV2.SWITCH_TO_OFF)

    def __switch(self, switch_to):
        _LOGGER.debug('Switch: ' + str(switch_to))
        if (self._remote_type == BrickletRemoteSwitchV2.REMOTE_TYPE_A):
            self._rs.switch_socket_a(
                self._house_code, self._receiver_code, switch_to)
        elif (self._remote_type == BrickletRemoteSwitchV2.REMOTE_TYPE_B):
            self._rs.switch_socket_b(
                self._house_code, self._receiver_code, switch_to)
        elif (self._remote_type == BrickletRemoteSwitchV2.REMOTE_TYPE_C):
            self._rs.switch_socket_b(
                self._house_code, self._receiver_code, switch_to)
        self.set_switch_state(switch_to)
    
    def set_switch_state(self, switched_to):
        self._state = switched_to == BrickletRemoteSwitchV2.SWITCH_TO_ON
        self.schedule_update_ha_state()
