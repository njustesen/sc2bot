from sc2bot.managers.interfaces import ArmyManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class SimpleArmyManager(ArmyManager):

    def __init__(self, bot):
        super().__init__(bot)

    async def run(self):
        pass

    async def attack(self, location, unit_types=None):
        if self.bot.iteration % 20 != 0:
            return
        if unit_types is not None:
            units = []
            for unit_type in unit_types:
                units += self.bot.units(unit_type)
            for unit in units:
                await self.bot.do(unit.attack(location))
        else:
            for unit in self.bot.units:
                if unit.type_id != UnitTypeId.SCV:
                    await self.bot.do(unit.attack(location))

    async def defend(self, location, unit_types=None):
        await self.attack(location, unit_types)
