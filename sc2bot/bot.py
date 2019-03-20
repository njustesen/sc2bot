
"""
A modular StarCraft II bot.
"""

import math
import sc2
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer
from sc2bot.managers.army.simple_army_manager import SimpleArmyManager
from sc2bot.managers.army.advanced_army_manager import AdvancedArmyManager
from sc2bot.managers.building.simple_building_manager import SimpleBuildingManager
from sc2bot.managers.production.marine_production_manager import MarineProductionManager
from sc2bot.managers.production.reaper_marine_production_manager import ReaperMarineProductionManager
from sc2bot.managers.production.orbital_production_manager import OrbitalProductionManager
from sc2bot.managers.production.mlp_production_manager import MLPProductionManager
from sc2bot.managers.production.mlp_model import Net
from sc2bot.managers.scouting.simple_scouting_manager import SimpleScoutingManager
from sc2bot.managers.assault.simple_assault_manager import SimpleAssaultManager
from sc2bot.managers.assault.value_based_assault_manager import ValueBasedAssaultManager
from sc2bot.managers.worker.simple_worker_manager import SimpleWorkerManager


class TerranBot(sc2.BotAI):

    def __init__(self):
        super().__init__()
        self.iteration = 0
        self.worker_manager = SimpleWorkerManager(self)
        self.army_manager = AdvancedArmyManager(self)
        self.assault_manager = ValueBasedAssaultManager(self, self.army_manager, self.worker_manager)
        self.building_manager = SimpleBuildingManager(self, self.worker_manager)
        self.production_manager = MLPProductionManager(self, self.worker_manager, self.building_manager, "models_without_time/TvZ_3x256_no_frame_id_1552989984_state_dict")
        # self.production_manager = MLPProductionManager(self, self.worker_manager, self.building_manager, "TvZ_3x256_features_2D_1552906112", features=[0.5, 0.5])
        # self.production_manager = MarineProductionManager(self, self.worker_manager, self.building_manager)
        # self.production_manager = ReaperMarineProductionManager(self, self.worker_manager, self.building_manager)
        # self.production_manager = OrbitalProductionManager(self, self.worker_manager, self.building_manager)
        self.scouting_manager = SimpleScoutingManager(self, self.worker_manager, self.building_manager)
        self.managers = [self.scouting_manager, self.production_manager, self.building_manager, self.assault_manager, self.army_manager, self.worker_manager]
        self.enemy_units = {}
        self.own_units = {}
        print("Bot is ready")

    async def on_step(self, iteration):
        '''
        Calls
        :param iteration:
        :return:
        '''

        #print("Step: ", self.state.observation.game_loop)

        for unit in self.known_enemy_units | self.known_enemy_structures:
            self.enemy_units[unit.tag] = unit

        self.iteration += 1
        # print("-- Production Manager")
        await self.production_manager.execute()
        # print("-- Scouting Manager")
        await self.scouting_manager.execute()
        # print("-- Assault Manager")
        await self.assault_manager.execute()
        # print("-- Army Manager")
        await self.army_manager.execute()
        # print("-- Worker Manager")
        await self.worker_manager.execute()
        # print("-- Building Manager")
        await self.building_manager.execute()

    def game_data(self):
        return self._game_data

    def client(self):
        return self._client

    async def get_next_expansion(self):
        """Find next expansion location."""

        closest = None
        distance = math.inf
        for el in self.expansion_locations:
            def is_near_to_expansion(t):
                return t.position.distance_to(el) < self.EXPANSION_GAP_THRESHOLD

            if any(map(is_near_to_expansion, self.townhalls)):
                # already taken
                continue

            startp = self._game_info.player_start_location
            d = startp.distance_to(el)
            if d is None:
                continue

            if d < distance:
                distance = d
                closest = el

        return closest

    async def on_unit_destroyed(self, unit_tag):
        if unit_tag in self.own_units:
            del self.own_units[unit_tag]
        if unit_tag in self.enemy_units:
            del self.enemy_units[unit_tag]
        for manager in self.managers:
            await manager.on_unit_destroyed(unit_tag)

    async def on_unit_created(self, unit):
        self.own_units[unit.tag] = unit
        for manager in self.managers:
            await manager.on_unit_created(unit)

    async def on_building_construction_started(self, unit):
        self.own_units[unit.tag] = unit
        for manager in self.managers:
            await manager.on_building_construction_started(unit)

    async def on_building_construction_complete(self, unit):
        for manager in self.managers:
            await manager.on_building_construction_complete(unit)


def main():
    # Multiple difficulties for enemy bots available https://github.com/Blizzard/s2client-api/blob/ce2b3c5ac5d0c85ede96cef38ee7ee55714eeb2f/include/sc2api/sc2_gametypes.h#L30
    sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
        Bot(Race.Terran, TerranBot()),
        Computer(Race.Zerg, Difficulty.Medium)
    ], realtime=False)


if __name__ == '__main__':
    main()
