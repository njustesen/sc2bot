from sc2bot.managers.interfaces import ScoutingManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
import math


class SimpleScoutingManager(ScoutingManager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot, worker_manager, building_manager)
        self.scanning_queue = []
        self.scans = []

    async def run(self):
        # Initialize scanning positions
        if len(self.scanning_queue) == 0:
            for position in self.bot.expansion_locations:
                self.scanning_queue.append(position)

        # Worker scouting?
        if self.bot.iteration % 50 == 0 and self.bot.known_enemy_structures.amount == 0 and self.bot.units(UnitTypeId.SUPPLYDEPOT):
            target = self.bot.known_enemy_structures.random_or(self.bot.enemy_start_locations[0]).position
            # print("ScoutingManager: scouting ", target)
            await self.worker_manager.scout(target)

        # Scanner scouting?
        if self.bot.iteration % 20 == 0:
            for oc in self.bot.units(UnitTypeId.ORBITALCOMMAND):
                if oc.build_progress == 1 and oc.energy >= 60:
                    best_scan = None
                    scan_value = 0
                    if self.bot.known_enemy_structures.exists:
                        for scan in self.scanning_queue:
                            distance_to_a = self.bot.enemy_start_locations[0].distance_to(scan)
                            distance_to_b = self.bot.known_enemy_structures.closest_to(scan).distance_to(scan)
                            times = self.scans.count(scan)
                            value = (math.log(1+distance_to_a) / (1+distance_to_b)) / (1+times)**2
                            if value > scan_value:
                                best_scan = scan
                                scan_value = value
                        self.scans.append(best_scan)
                        await self.building_manager.scan(best_scan)
                    else:
                        await self.building_manager.scan(self.bot.enemy_start_locations[0])
                    return
