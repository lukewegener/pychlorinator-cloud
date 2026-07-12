"""Switch platform for the AstralPool Halo Cloud integration.

Provides on/off control for GPO outlets on the Halo Xpand / Connect ports.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HaloCloudCoordinator
from .entity import HaloCloudEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AstralPool Halo Cloud switch entities."""
    coordinator: HaloCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(HaloGpoSwitch(coordinator, n) for n in range(1, 5))


class HaloGpoSwitch(HaloCloudEntity, SwitchEntity):
    """On/off switch for a GPO outlet on an Xpand/Connect port.

    Turning on/off sets the GPO mode to On/Off via the equipment action path.
    The reported state reflects the physical output, so a GPO switched on by
    its Auto timer also shows as on here.
    """

    _attr_icon = "mdi:power-socket-au"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: HaloCloudCoordinator, gpo_number: int) -> None:
        self._gpo_number = gpo_number
        super().__init__(
            coordinator,
            SwitchEntityDescription(
                key=f"gpo_{gpo_number}_switch",
                name=f"GPO {gpo_number}",
            ),
        )

    @property
    def available(self) -> bool:
        """Available once the equipment-mode readback shows this GPO is fitted."""
        return (
            super().available
            and self.coordinator.client.data.connected
            and self._gpo_number in self.coordinator.client.data.gpo_modes
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None:
            return None
        output_on = data.gpo_output_on.get(self._gpo_number)
        if output_on is not None:
            return output_on
        mode = data.gpo_modes.get(self._gpo_number)
        return mode == "On" if mode is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        data = self.coordinator.client.data
        return {
            "mode": data.gpo_modes.get(self._gpo_number),
            "configured_name": data.gpo_names.get(self._gpo_number),
        }

    async def async_turn_on(self, **kwargs: object) -> None:
        await self._set_mode("On")

    async def async_turn_off(self, **kwargs: object) -> None:
        await self._set_mode("Off")

    async def _set_mode(self, mode: str) -> None:
        client = self.coordinator.client
        if not client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")
        await client.set_gpo_mode(self._gpo_number, mode)
        self.coordinator.async_set_updated_data(client.data)
