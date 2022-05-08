"""Handle config entry flow."""

import logging
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
import vassapi
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_DEVICES, CONF_HOST, CONF_NAME, CONF_TOKEN

from .const import CONF_UUID, DOMAIN, GREETING_SPEECH

_LOGGER = logging.getLogger(__name__)


def input_schema() -> vol.Schema:
    """Get user input schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST): cv.string,
            vol.Required(CONF_TOKEN): cv.string,
        }
    )


class VoiceAssistantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Voice Assistant config flow."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Set up a config entry for Voice Assistant."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("")
            client = vassapi.Client(user_input[CONF_HOST], user_input[CONF_TOKEN])
            try:
                is_running = await client.async_is_running()
            except vassapi.HTTPError:
                is_running = False

            if not is_running:
                errors = {"base": "invalid_auth"}

            if not errors:
                await client.async_say(GREETING_SPEECH)
                info = await client.async_device_info()
                additional_info = {
                    CONF_NAME: info.name,
                    CONF_UUID: info.uuid,
                }
                data = {CONF_DEVICES: [user_input | additional_info]}

                return self.async_create_entry(title=info.name, data=data)

        return self.async_show_form(
            step_id="user", data_schema=input_schema(), errors=errors
        )
