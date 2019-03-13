from sc2bot.managers.interfaces import BuildingManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class SimpleBuildingManager(BuildingManager):

    def __init__(self, bot):
        super().__init__(bot)
        self.trained_at = {
            UnitTypeId.SCV: UnitTypeId.COMMANDCENTER,
            UnitTypeId.MARINE: UnitTypeId.BARRACKS,
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKS
        }
        self.add_on_at = {
            UnitTypeId.BARRACKSTECHLAB: UnitTypeId.BARRACKS,
            UnitTypeId.FACTORYTECHLAB: UnitTypeId.FACTORY
        }
        self.researched_at = {
            UpgradeId.COMBATSHIELD: UnitTypeId.BARRACKSTECHLAB,
            UpgradeId.SIEGETECH: UnitTypeId.FACTORYTECHLAB
        }

    async def run(self):
        pass

    async def train(self, unit):
        # print("BuildingManager: training ", unit)
        for building in self.bot.units(self.trained_at[unit]).ready.noqueue:
            if not self.bot.can_afford(unit):
                break
            await self.bot.do(building.train(unit))

    async def add_on(self, add_on):
        for rax in self.bot.units(self.add_on_at[add_on]).ready:
            if rax.add_on_tag == 0:
                await self.bot.do(rax.build(UnitTypeId.BARRACKSTECHLAB))

    async def research(self, upgrade):
        for lab in self.bot.units(self.researched_at[upgrade]).ready:
            await self.bot.do(lab.research(upgrade))
