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
        # load all the column names and the data.
        self.model = model
        # self.game_info = bot.game_info
    
    def prepare_input(self):
        state = self.bot.state

        # print(self.game_info)

        observation = state.observation

        row = {}
        row["frame_id"] = observation.game_loop

        row["resources"] = {
        "minerals": observation.player_common.minerals,
        "vespene": observation.player_common.vespene,
        }

        row["supply"] = {
            "used": observation.player_common.food_used,
            "total": observation.player_common.food_cap,
            "army": observation.player_common.food_army,
            "workers": observation.player_common.food_workers,
        }

        allied_units = [
            unit for unit in observation.raw_data.units if unit.alliance == 1
        ]

        allied_unit_types = set([unit.unit_type for unit in allied_units])
        
        row["units"] = {
            unit_type: len([
                unit.tag for unit in allied_units if unit.unit_type == unit_type
            ]) for unit_type in allied_unit_types
        }

        # state_doc["supply"] = observation.player_common.food_used
        # print(observation.player_common.supply)

    async def run(self):
        print(self.bot.units)
        # x = self.prepare_input()
        # action = self.model.evaluate(x)

        