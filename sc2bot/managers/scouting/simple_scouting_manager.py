from sc2bot.managers.interfaces import ScoutingManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId


class SimpleScoutingManager(ScoutingManager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot, worker_manager, building_manager)

    async def run(self):
        if self.bot.iteration % 50 == 0 and self.bot.known_enemy_structures.amount == 0 and self.bot.units(UnitTypeId.SUPPLYDEPOT):
            target = self.bot.known_enemy_structures.random_or(self.bot.enemy_start_locations[0]).position
            # print("ScoutingManager: scouting ", target)
            await self.worker_manager.scout(target)

        '''
        if self.bot.iteration % 20 == 0:
            for oc in self.bot.units(UnitTypeId.ORBITALCOMMAND):
                if oc.build_progress == 1 and oc.energy >= 60:
                    if self.bot.known_enemy_structures.exists:
                        await self.building_manager.scan(self.bot.known_enemy_structures().random)
                    else:
                        await self.building_manager.scan(self.bot.enemy_start_locations[0])
        '''