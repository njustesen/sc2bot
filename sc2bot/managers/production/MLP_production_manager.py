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
        self.seen_enemy_units_max = {}
        # self.game_info = bot.game_info
    
    def prepare_input(self):
        state = self.bot.state

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

        allied_unit_types = set([unit.name for unit in self.bot.units])
        
        row["units"] = {
            name: len([
                unit.tag for unit in self.bot.units if unit.name == name and unit.build_progress == 1
            ]) for name in allied_unit_types
        }

        row["units_in_progress"] = {
            name: len([
                unit.tag for unit in self.bot.units if unit.name == name and unit.build_progress < 1 
            ]) for name in allied_unit_types
        } # If this is implemented using the API, only buildings will appear.

        row["highest_progress"] = {
            name: max([
                unit.build_progress for unit in self.bot.units if unit.name == name and unit.build_progress < 1
            ]) for name in row["units_in_progress"]
        }

        enemy_unit_types = set([unit.name for unit in self.bot.known_enemy_units | self.bot.known_enemy_structures])
        row["visible_enemy_units"] = {
            name: len([
                unit.tag for unit in self.bot.units if unit.name == name
            ]) for name in enemy_unit_types
        }

        seen_max = self.seen_enemy_units_max.copy()
        for name in row["visible_enemy_units"]:
            if name not in seen_max:
                seen_max[name] = row["visible_enemy_units"][name]
            if name in seen_max:
                seen_max[name] = max(
                    seen_max[name], row["visible_enemy_units"][name]
                )
        self.seen_enemy_units = seen_max.copy()

        print(row)


    async def run(self):
        x = self.prepare_input()
        print(f"Bot's units: {self.bot.units}")
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

        # print(f"Bot's known enemy units: {self.bot.known_enemy_units | self.bot.known_enemy_structures}")
        
        