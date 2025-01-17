"""Config flow for Wolf SmartSet Service integration."""

import logging

from httpcore import ConnectError
import voluptuous as vol
from wolf_comm.models import Device
from wolf_comm.token_auth import InvalidAuth
from wolf_comm.wolf_client import WolfClient

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DEVICE_GATEWAY, DEVICE_ID, DEVICE_NAME, DOMAIN, LOCALE

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(LOCALE): str,
    }
)


class WolfLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wolf SmartSet Service."""

    VERSION = 1
    MINOR_VERSION = 2

    fetched_systems: list[Device]

    def __init__(self) -> None:
        """Initialize with empty username and password."""
        self.username: str | None = None
        self.password: str | None = None
        self.locale: str = "en"

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step to get connection parameters."""
        errors = {}
        if user_input is not None:
            wolf_client = WolfClient(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            await wolf_client.load_localized_json(user_input[LOCALE])
            try:
                self.fetched_systems = await wolf_client.fetch_system_list()
            except ConnectError:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.username = user_input[CONF_USERNAME]
                self.password = user_input[CONF_PASSWORD]
                self.locale = user_input[LOCALE]
                return await self.async_step_device()
        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_device(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Allow user to select device from devices connected to specified account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            device_name = user_input[DEVICE_NAME]
            system = [
                device for device in self.fetched_systems if device.name == device_name
            ]
            device_id = system[0].id
            await self.async_set_unique_id(str(device_id))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[DEVICE_NAME],
                data={
                    CONF_USERNAME: self.username,
                    CONF_PASSWORD: self.password,
                    DEVICE_NAME: device_name,
                    DEVICE_GATEWAY: system[0].gateway,
                    DEVICE_ID: device_id,
                    LOCALE: self.locale,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(DEVICE_NAME): vol.In(
                    [info.name for info in self.fetched_systems]
                )
            }
        )
        return self.async_show_form(
            step_id="device", data_schema=data_schema, errors=errors
        )
