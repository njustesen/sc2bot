
"""
A modular StarCraft II bot.
"""

import sc2
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer
from sc2bot.managers.army.simple_army_manager import SimpleArmyManager
from sc2bot.managers.building.simple_building_manager import SimpleBuildingManager
from sc2bot.managers.production.simple_production_manager import SimpleProductionManager
from sc2bot.managers.scouting.simple_scouting_manager import SimpleScoutingManager
from sc2bot.managers.assault_manager.simple_assault_manager import SimpleAssaultManager
from sc2bot.managers.worker.simple_worker_manager import SimpleWorkerManager


class TerranBot(sc2.BotAI):

    def __init__(self):
        super().__init__()
        self.iteration = 0
        self.worker_manager = SimpleWorkerManager(self)
        self.army_manager = SimpleArmyManager(self)
        self.assault_manager = SimpleAssaultManager(self, self.army_manager, self.worker_manager)
        self.building_manager = SimpleBuildingManager(self)
        self.production_manager = SimpleProductionManager(self, self.worker_manager, self.building_manager)
        self.scouting_manager = SimpleScoutingManager(self, self.worker_manager, self.building_manager)

    async def on_step(self, iteration):
        '''
        Calls
        :param iteration:
        :return:
        '''
        self.iteration = iteration
        print("-- Production Manager")
        await self.production_manager.run()
        print("-- Scouting Manager")
        await self.scouting_manager.run()
        print("-- Assault Manager")
        await self.assault_manager.run()
        print("-- Army Manager")
        await self.army_manager.run()
        print("-- Worker Manager")
        await self.worker_manager.run()
        print("-- Building Manager")
        await self.building_manager.run()


def main():
    # Multiple difficulties for enemy bots available https://github.com/Blizzard/s2client-api/blob/ce2b3c5ac5d0c85ede96cef38ee7ee55714eeb2f/include/sc2api/sc2_gametypes.h#L30
    sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
        Bot(Race.Terran, TerranBot()),
        Computer(Race.Zerg, Difficulty.VeryHard)
    ], realtime=False)


if __name__ == '__main__':
    main()
