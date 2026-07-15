---
source: Context7 API
library: Home Assistant Developers Docs
package: home-assistant-core
topic: config flow (multi-step), OptionsFlow, reconfigure flow
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
---

## Multi-step ConfigFlow

Return next step handler's result to chain steps:

```python
class ExampleConfigFlow(data_entry_flow.FlowHandler):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            valid = await is_valid(user_input)
            if valid:
                self.init_info = user_input
                return await self.async_step_account()
        ...
```

## OptionsFlow (basic)

First step MUST be `async_step_init`. Use `add_suggested_values_to_schema` to prefill current options.

```python
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import ConfigFlowResult
import voluptuous as vol

OPTIONS_SCHEMA = vol.Schema({vol.Required("show_things"): bool})

class OptionsFlowHandler(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
```

Register options flow in ConfigFlow:

```python
@staticmethod
@callback
def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
    return OptionsFlowHandler()
```

`OptionsFlowWithReload` subclass auto-reloads integration on options change (no manual update listener needed):

```python
from homeassistant.config_entries import OptionsFlowWithReload

class MyOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
```

## Reconfigure flow

Add `async_step_reconfigure`; use `async_update_reload_and_abort` + `_get_reconfigure_entry()` + `_abort_if_unique_id_mismatch`:

```python
class MyConfigFlow(ConfigFlow, domain=DOMAIN):
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input:
            client = MyClient(user_input[CONF_HOST], user_input[CONF_API_TOKEN])
            try:
                user_id = await client.check_connection()
            except MyException:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates=user_input,
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): TextSelector(),
                vol.Required(CONF_API_TOKEN): TextSelector(),
            }),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input:
            client = MyClient(user_input[CONF_HOST], user_input[CONF_API_TOKEN])
            try:
                user_id = await client.check_connection()
            except MyException:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="MyIntegration", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): TextSelector(),
                vol.Required(CONF_API_TOKEN): TextSelector(),
            }),
            errors=errors,
        )
```

Dev command to iterate on `strings.json` for config flow: `python3 -m script.translations develop`
