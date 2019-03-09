import random
from sc2bot.managers.interfaces import ProductionManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class MLPProductionManager(ProductionManager):
    '''
    This production manager transforms the observation that the bot
    is getting into the input for the model. It accepts also a pair of
    features.
    '''
    def __init__(self, bot, worker_manager, building_manager, model):
        super().__init__(bot, worker_manager, building_manager)
        self.model = model
    
    def prepare_input(self):
        state = self.bot.state
        observation = state.observation
        state_doc = {}
        state_doc["supply"] = observation.player_common.food_used
        print(observation.player_common.supply)

    async def run(self):
        x = self.prepare_input()
        action = self.model.evaluate(x)

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
