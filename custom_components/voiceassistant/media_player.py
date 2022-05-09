"""Voice Assistant Media Player representation."""

from __future__ import annotations

import logging
import random

import homeassistant.helpers.config_validation as cv
import vassapi
import voluptuous as vol
from homeassistant.components.media_player import (
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES, CONF_HOST, CONF_NAME, CONF_TOKEN, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform

from .const import (
    ATTR_CACHE,
    ATTR_MESSAGE,
    ATTR_MESSAGE_LIST,
    CONF_UUID,
    DOMAIN,
    SERVICE_RELOAD,
    SERVICE_SAY,
    SERVICE_SAY_RANDOM,
    SERVICE_TRIGGER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
):
    """Set up media player entity and related custom services."""
    async_add_devices(
        [
            VoiceAssistantEntity(
                name=conf[CONF_NAME],
                host=conf[CONF_HOST],
                token=conf[CONF_TOKEN],
                uuid=conf[CONF_UUID],
            )
            for conf in config_entry.data[CONF_DEVICES]
        ]
    )

    platform = async_get_current_platform()
    platform.async_register_entity_service(SERVICE_RELOAD, {}, "async_reload")
    platform.async_register_entity_service(SERVICE_TRIGGER, {}, "async_trigger")
    platform.async_register_entity_service(
        SERVICE_SAY,
        {
            vol.Required(ATTR_MESSAGE): cv.string,
            vol.Required(ATTR_CACHE): cv.boolean,
        },
        "async_say",
    )
    platform.async_register_entity_service(
        SERVICE_SAY_RANDOM,
        {
            vol.Required(ATTR_MESSAGE_LIST): cv.ensure_list,
            vol.Required(ATTR_CACHE): cv.boolean,
        },
        "async_say_random",
    )


class VoiceAssistantEntity(MediaPlayerEntity):
    """Represent Voice Assistant Entity."""

    def __init__(self, name: str, uuid: str, host: str, token: str) -> None:
        """Initialize entity."""
        self._client = vassapi.Client(host, token)
        self._name = name
        self._unique_id = f"{uuid}-media_player"

        self._state = STATE_ON
        self._volume = 1
        self._muted = False

        try:
            info = self._client.device_info()
            self._vass_info = {
                "sw_version": info.version,
                "language": info.language,
                "suggested_area": info.area,
            }
            self._available = True
        except vassapi.HTTPError:
            self._vass_info = {}
            self._available = False

    @property
    def unique_id(self):
        """Return unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self._available

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
        } | self._vass_info

    @property
    def device_class(self):
        """Return device class."""
        return MediaPlayerDeviceClass.SPEAKER

    @property
    def supported_features(self):
        """Return supported features."""
        return (
            SUPPORT_VOLUME_SET
            | SUPPORT_VOLUME_MUTE
            | SUPPORT_TURN_ON
            | SUPPORT_TURN_OFF
        )

    @property
    def icon(self) -> str:
        """Return entity icon."""
        return "mdi:surround-sound"

    @property
    def state(self) -> str:
        """Return current state."""
        return self._state

    @property
    def volume_level(self) -> float | None:
        """Get voice assistant host device volume (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self) -> bool | None:
        """Check if voice assistant host device volume is muted."""
        return self._muted

    async def async_turn_on(self) -> None:
        """Turn on microphone."""
        self._state = STATE_ON
        await self._client.async_set_input_mute(False)

    async def async_turn_off(self) -> None:
        """Turn off microphone."""
        self._state = STATE_OFF
        await self._client.async_set_input_mute(True)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute voice assistant host device volume."""
        await self._client.async_set_output_mute(mute)
        self._muted = True

    async def async_set_volume_level(self, volume: float) -> None:
        """Set voice assistant host device volume (0..1)."""
        self._volume = volume
        await self._client.async_set_output_volume(int(volume * 100))

    async def async_update(self) -> None:
        """Update states."""
        try:
            states = await self._client.async_states()
            self._available = True
            _LOGGER.debug(f"{self.name}'s states: {states}")
        except vassapi.HTTPError:
            _LOGGER.debug(f"{self.name} is unavailable")
            self._available = False
            return

        if states.output_volume is not None:
            self._volume = states.output_volume / 100

        if states.output_muted is not None:
            self._muted = states.output_muted

        if self._state is not None:
            self._state = STATE_OFF if states.input_muted else STATE_ON

    # custom services
    async def async_reload(self) -> None:
        """Call reload service."""
        await self._client.async_reload()

    async def async_trigger(self) -> None:
        """Call trigger service."""
        await self._client.async_trigger()

    async def async_say(self, message: str, cache: bool) -> None:
        """Call say service."""
        await self._client.async_say(message, cache)

    async def async_say_random(self, message_list: list[str], cache: bool) -> None:
        """Call say random service."""
        message = random.choice(message_list)
        await self.async_say(message, cache)
