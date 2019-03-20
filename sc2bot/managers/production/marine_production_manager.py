import random
from sc2bot.managers.interfaces import ProductionManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class MarineProductionManager(ProductionManager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot, worker_manager, building_manager)
        self.next_iteration = 0
        print("Production manager ready")

    async def run(self):
        '''
        vgs = []
        for th in self.bot.townhalls:
            vgs = self.bot.state.vespene_geyser.closer_than(10, th)
        if len(vgs) > 0 and self.bot.can_afford(UnitTypeId.REFINERY) and self.bot.units(
                UnitTypeId.REFINERY).amount < 2 * self.bot.units(UnitTypeId.COMMANDCENTER).amount:
            self.next_iteration += 20
            await self.worker_manager.build(UnitTypeId.REFINERY, location=vgs[0])
        '''

        if self.bot.iteration >= self.next_iteration:
            if self.bot.supply_left < self.bot.units(UnitTypeId.BARRACKS).amount + self.bot.units(UnitTypeId.COMMANDCENTER).amount:
                self.next_iteration += 40
                await self.worker_manager.build(UnitTypeId.SUPPLYDEPOT)
            elif self.bot.units(UnitTypeId.REFINERY).amount < 1:
                self.next_iteration += 2
                await self.worker_manager.build(UnitTypeId.REFINERY)
            elif self.bot.can_afford(UnitTypeId.BARRACKSTECHLAB) and self.bot.units(UnitTypeId.BARRACKSTECHLAB).amount < self.bot.units(UnitTypeId.BARRACKS).amount and self.bot.units(UnitTypeId.BARRACKS).ready.exists and self.bot.can_afford(UnitTypeId.REFINERY):
                self.next_iteration += 2
                await self.building_manager.add_on(UnitTypeId.BARRACKSTECHLAB)
            elif (self.bot.units(UnitTypeId.COMMANDCENTER).idle.exists or self.bot.units(UnitTypeId.ORBITALCOMMAND).idle.exists) and self.bot.units(UnitTypeId.SCV).amount < 20 * self.bot.units(UnitTypeId.COMMANDCENTER).amount:
                self.next_iteration += 2
                await self.building_manager.train(UnitTypeId.SCV)
            elif self.bot.can_afford(UnitTypeId.MARINE) and self.building_manager.can_train(UnitTypeId.MARINE):
                self.next_iteration += 2
                await self.building_manager.train(UnitTypeId.MARINE)
            elif self.bot.can_afford(UnitTypeId.BARRACKS) and self.bot.units(UnitTypeId.BARRACKS).amount < 2:
                self.next_iteration += 20
                await self.worker_manager.build(UnitTypeId.BARRACKS)
            elif self.bot.units(UnitTypeId.BUNKER).amount < self.bot.units(UnitTypeId.COMMANDCENTER).amount:
                self.next_iteration += 40
                await self.worker_manager.build(UnitTypeId.BUNKER)
            elif UpgradeId.STIMPACK not in self.bot.state.upgrades:
                self.next_iteration += 40
                await self.building_manager.research(UpgradeId.STIMPACK)
            elif self.bot.can_afford(UnitTypeId.COMMANDCENTER):
                self.next_iteration += 50
                await self.worker_manager.build(UnitTypeId.COMMANDCENTER)
            elif self.building_manager.can_upgrade(UnitTypeId.ORBITALCOMMAND) and self.bot.can_afford(UnitTypeId.ORBITALCOMMAND):
                self.next_iteration += 2
                await self.building_manager.upgrade(UnitTypeId.ORBITALCOMMAND)
            else:
                self.next_iteration += 1
