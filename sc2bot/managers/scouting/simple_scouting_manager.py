from sc2bot.managers.interfaces import ScoutingManager


class SimpleScoutingManager(ScoutingManager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot, worker_manager, building_manager)

    async def run(self):
        if self.bot.known_enemy_structures.amount == 0:
            target = self.bot.known_enemy_structures.random_or(self.bot.enemy_start_locations[0]).position
            #print("ScoutingManager: scouting ", target)
            await self.worker_manager.scout(target)
