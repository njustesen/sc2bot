import random
from sc2bot.managers.interfaces import ProductionManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class SimpleProductionManager(ProductionManager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot, worker_manager, building_manager)

    async def run(self):
        if self.bot.supply_left < 2:
            await self.worker_manager.build(UnitTypeId.SUPPLYDEPOT)
        elif random.random() > 0.75:
            print("ProductionManager: train SCV.")
            await self.building_manager.train(UnitTypeId.SCV)
        elif len(self.bot.units(UnitTypeId.BARRACKS)) == 0:
            print("ProductionManager: build Barracks.")
            await self.worker_manager.build(UnitTypeId.BARRACKS)
        else:
            print("ProductionManager: train Marine.")
            await self.building_manager.train(UnitTypeId.MARINE)
