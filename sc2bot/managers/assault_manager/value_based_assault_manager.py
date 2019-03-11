from sc2bot.managers.interfaces import AssaultManager
from sc2.ids.unit_typeid import UnitTypeId


class ValueBasedAssaultManager(AssaultManager):

    def __init__(self, bot, army_manager, worker_manager):
        super().__init__(bot, army_manager, worker_manager)

    async def run(self):
        # own_value =

        target = target = self.bot.known_enemy_structures.random_or(self.bot.enemy_start_locations[0]).position
        print("AssaultManager: Attacking ", target)
        await self.army_manager.attack(target)

    #def get_own_value(self):
    #    for unit in self.bot.units():
