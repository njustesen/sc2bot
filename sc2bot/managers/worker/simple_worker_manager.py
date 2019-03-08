import sc2
import asyncio
from sc2bot.managers.interfaces import WorkerManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class SimpleWorkerManager(WorkerManager):

    def __init__(self, bot):
        super().__init__(bot)
        self.scouting_worker = None

    async def run(self):
        for idle_worker in self.bot.workers.idle:
            mf = self.bot.state.mineral_field.closest_to(idle_worker)
            await self.bot.do(idle_worker.gather(mf))

    async def distribute(self):
         await self.bot.distribute_workers()

    async def build(self, building, location=None):
        print("WorkerManager: building ", building)
        w = self._get_worker()
        if w:  # if worker found
            loc = await self.bot.find_placement(building, w.position, placement_step=3)
            if loc:  # if a placement location was found
                # build exactly on that location
                await self.bot.do(w.build(building, loc))

    async def scout(self, location):
        if self.scouting_worker is None:
            w = self._get_worker()
            if w:  # if worker found
                print("WorkerManager: scouting ", location)
                self.scouting_worker = w
                await self.bot.do(w.move(location))

    async def rush(self, location):
        for w in self.bot.workers:
            await self.bot.do(w.attack(location))

    async def defend(self, location):
        for w in self.bot.workers:
            await self.bot.do(w.attack(location))

    def _get_worker(self):
        ws = self.bot.workers.gathering
        if ws:  # if workers found
            return ws.furthest_to(ws.center)
        return None
