import sc2
import asyncio
from sc2bot.managers.interfaces import WorkerManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from random import randint


class BuildJob:

    def __init__(self, worker, building_type, location):
        self.worker = worker
        self.building_type = building_type
        self.location = location
        self.under_construction = False
        self.building = None
        self.done = False


class SimpleWorkerManager(WorkerManager):

    def __init__(self, bot):
        super().__init__(bot)
        self.scouting_worker = None
        self.scouting_location = None
        self.last_scouting_location = None
        self.build_jobs = []

    async def run(self):

        if self.bot.iteration % 20 == 0:
            for idle_worker in self.bot.workers.idle:
                if self.scouting_worker is None or self.scouting_worker.tag != idle_worker.tag:
                    mf = self.bot.state.mineral_field.closest_to(idle_worker)
                    self.actions.append(idle_worker.gather(mf))

        if self.scouting_worker is not None:
            for unit in self.bot.known_enemy_units.not_structure:
                if unit.distance_to(self.scouting_worker) < unit.ground_range * 1.2:
                    self.actions.append(self.scouting_worker.move(self.bot.start_location))
                    return
                elif self.scouting_worker.is_idle or self.scouting_worker.is_collecting:
                    if self.scouting_worker.distance_to(self.last_scouting_location) < 200:
                        self.last_scouting_location = self.scouting_location.random_on_distance(randint(10, 30))
                    self.actions.append(self.scouting_worker.move(self.last_scouting_location))

        for build_job in self.build_jobs:

            # Job cancelled or completed
            if build_job.done:
                minerals = self.bot.state.units.mineral_field.closest_to(self.bot.start_location)
                self.actions.append(build_job.worker.gather(minerals))
                continue

            # Worker died
            if build_job.worker is None:
                build_job.worker = self._get_builder()
                if build_job.worker is not None:
                    if build_job.under_construction:
                        self.actions.append(build_job.worker.repair(build_job.location))
                    else:
                        self.actions.append(build_job.worker.build(build_job.building_type, build_job.location))
                continue

            # Move or build with worker
            if not build_job.under_construction:
                if self.bot.can_afford(build_job.building_type):
                    self.actions.append(build_job.worker.build(build_job.building_type, build_job.location))
                else:
                    self.actions.append(build_job.worker.move(build_job.location))
                continue

        self.build_jobs = [build_job for build_job in self.build_jobs if not build_job.done]

        # await self.bot.do_actions(self.combinedActions)
        # self.combinedActions = []

    async def distribute(self):
        await self.bot.distribute_workers()

    async def build(self, building, location=None):

        # Remove all un-started build jobs
        add_new = True
        for build_job in self.build_jobs:
            if not build_job.under_construction:
                if build_job.building_type != building:
                    build_job.done = True
                else:
                    if location is not None:
                        build_job.location = location
                    add_new = False
        if not add_new:
            return

        #print("WorkerManager: building ", building)
        w = self._get_builder()
        placement_steps = 2 if building == UnitTypeId.SUPPLYDEPOT else 4
        if w:  # if worker found
            assert self.scouting_worker is None or w.tag != self.scouting_worker.tag
            if location is None:
                if building == UnitTypeId.COMMANDCENTER:
                    # loc = await self.bot.find_placement(building, w.position, placement_step=3)
                    loc = await self.bot.get_next_expansion()
                elif building == UnitTypeId.REFINERY:
                    loc = self.get_next_geyser()
                else:
                    # Wall-in
                    depots = self.bot.units(UnitTypeId.SUPPLYDEPOT) | self.bot.units(UnitTypeId.SUPPLYDEPOTLOWERED)
                    placement_positions = []
                    if building == UnitTypeId.SUPPLYDEPOT:
                        placement_positions = self.bot.main_base_ramp.corner_depots
                        if depots:
                            placement_positions = {d for d in placement_positions if
                                                         depots.closest_distance_to(d) > 1}
                    elif building == UnitTypeId.BARRACKS and self.bot.units(UnitTypeId.BARRACKS).amount + self.bot.already_pending(UnitTypeId.BARRACKS) == 0:
                        placement_positions = [self.bot.main_base_ramp.barracks_correct_placement]

                    if len(placement_positions) == 0:
                        loc = await self.bot.find_placement(building, w.position, placement_step=placement_steps)
                    else:
                        loc = placement_positions.pop()
            else:
                loc = location
            if loc:  # if a placement location was found
                # build exactly on that location
                self.build_jobs.append(BuildJob(w, building, loc))

    def get_next_geyser(self):
        for th in self.bot.townhalls:
            vgs = self.bot.state.vespene_geyser.closer_than(20, th)
            for vg in vgs:
                if self.bot.units(UnitTypeId.REFINERY).closer_than(1.0, vg).exists:
                    break
                return vg
        return None

    async def scout(self, location):
        if self.scouting_worker is None:
            self.scouting_location = location
            self.last_scouting_location = location
            w = self._get_builder()
            if w:  # if worker found
                #print("WorkerManager: scouting ", location)
                self.scouting_worker = w
                self.actions.append(w.move(location))

    async def rush(self, location):
        for w in self.bot.workers:
            self.actions.append(w.attack(location))

    async def defend(self, location):
        for w in self.bot.workers:
            self.actions.append(w.attack(location))

    def _get_builder(self):
        ws = self.bot.workers.gathering
        if ws:  # if workers found
            if self.scouting_worker in ws:
                ws.remove(self.scouting_worker)
            if ws.amount > 0:
                return ws.furthest_to(ws.center)
        return None

    def distribute_workers(self, performanceHeavy=True, onlySaturateGas=False):
        # expansion_locations = self.expansion_locations
        # owned_expansions = self.owned_expansions


        mineralTags = [x.tag for x in self.bot.state.units.mineral_field]
        # gasTags = [x.tag for x in self.state.units.vespene_geyser]
        geyserTags = [x.tag for x in self.bot.geysers]

        workerPool = self.bot.units & []
        workerPoolTags = set()

        # find all geysers that have surplus or deficit
        deficitGeysers = {}
        surplusGeysers = {}
        for g in self.bot.geysers.filter(lambda x:x.vespene_contents > 0):
            # only loop over geysers that have still gas in them
            deficit = g.ideal_harvesters - g.assigned_harvesters
            if deficit > 0:
                deficitGeysers[g.tag] = {"unit": g, "deficit": deficit}
            elif deficit < 0:
                surplusWorkers = self.bot.workers.closer_than(10, g).filter(lambda w:w not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_GATHER] and w.orders[0].target in geyserTags)
                # workerPool.extend(surplusWorkers)
                for i in range(-deficit):
                    if surplusWorkers.amount > 0:
                        w = surplusWorkers.pop()
                        workerPool.append(w)
                        workerPoolTags.add(w.tag)
                surplusGeysers[g.tag] = {"unit": g, "deficit": deficit}

        # find all townhalls that have surplus or deficit
        deficitTownhalls = {}
        surplusTownhalls = {}
        if not onlySaturateGas:
            for th in self.bot.townhalls:
                deficit = th.ideal_harvesters - th.assigned_harvesters
                if deficit > 0:
                    deficitTownhalls[th.tag] = {"unit": th, "deficit": deficit}
                elif deficit < 0:
                    surplusWorkers = self.bot.workers.closer_than(10, th).filter(lambda w:w.tag not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_GATHER] and w.orders[0].target in mineralTags)
                    # workerPool.extend(surplusWorkers)
                    for i in range(-deficit):
                        if surplusWorkers.amount > 0:
                            w = surplusWorkers.pop()
                            workerPool.append(w)
                            workerPoolTags.add(w.tag)
                    surplusTownhalls[th.tag] = {"unit": th, "deficit": deficit}

            if all([len(deficitGeysers) == 0, len(surplusGeysers) == 0, len(surplusTownhalls) == 0 or deficitTownhalls == 0]):
                # cancel early if there is nothing to balance
                return

        # check if deficit in gas less or equal than what we have in surplus, else grab some more workers from surplus bases
        deficitGasCount = sum(gasInfo["deficit"] for gasTag, gasInfo in deficitGeysers.items() if gasInfo["deficit"] > 0)
        surplusCount = sum(-gasInfo["deficit"] for gasTag, gasInfo in surplusGeysers.items() if gasInfo["deficit"] < 0)
        surplusCount += sum(-thInfo["deficit"] for thTag, thInfo in surplusTownhalls.items() if thInfo["deficit"] < 0)

        if deficitGasCount - surplusCount > 0:
            # grab workers near the gas who are mining minerals
            for gTag, gInfo in deficitGeysers.items():
                if workerPool.amount >= deficitGasCount:
                    break
                workersNearGas = self.bot.workers.closer_than(10, gInfo["unit"]).filter(lambda w:w.tag not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_GATHER] and w.orders[0].target in mineralTags)
                while workersNearGas.amount > 0 and workerPool.amount < deficitGasCount:
                    w = workersNearGas.pop()
                    workerPool.append(w)
                    workerPoolTags.add(w.tag)

        # now we should have enough workers in the pool to saturate all gases, and if there are workers left over, make them mine at townhalls that have mineral workers deficit
        for gTag, gInfo in deficitGeysers.items():
            if performanceHeavy:
                # sort furthest away to closest (as the pop() function will take the last element)
                workerPool.sort(key=lambda x:x.distance_to(gInfo["unit"]), reverse=True)
            for i in range(gInfo["deficit"]):
                if workerPool.amount > 0:
                    w = workerPool.pop()
                    if len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_RETURN]:
                        self.actions.append(w.gather(gInfo["unit"], queue=True))
                    else:
                        self.actions.append(w.gather(gInfo["unit"]))

        if not onlySaturateGas:
            # if we now have left over workers, make them mine at bases with deficit in mineral workers
            for thTag, thInfo in deficitTownhalls.items():
                if performanceHeavy:
                    # sort furthest away to closest (as the pop() function will take the last element)
                    workerPool.sort(key=lambda x:x.distance_to(thInfo["unit"]), reverse=True)
                for i in range(thInfo["deficit"]):
                    if workerPool.amount > 0:
                        w = workerPool.pop()
                        mf = self.bot.state.mineral_field.closer_than(10, thInfo["unit"]).closest_to(w)
                        if len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_RETURN]:
                            self.actions.append(w.gather(mf, queue=True))
                        else:
                            self.actions.append(w.gather(mf))

    def is_building(self, building_type):
        for build_job in self.build_jobs:
            if building_type == build_job.building_type:
                return True
        return False

    async def on_building_construction_started(self, building):
        for build_job in self.build_jobs:
            if building.type_id == build_job.building_type:
                build_job.under_construction = True
                build_job.building = building

    async def on_building_construction_complete(self, building):
        if building.type_id in [UnitTypeId.COMMANDCENTER, UnitTypeId.REFINERY]:
            self.distribute_workers()
        for build_job in self.build_jobs:
            if build_job.building is not None and building.tag == build_job.building.tag:
                build_job.under_construction = False
                build_job.done = True

    async def on_unit_destroyed(self, unit_tag):
        if self.scouting_worker is not None and self.scouting_worker.tag == unit_tag:
            self.scouting_worker = None
        for build_job in self.build_jobs:
            if build_job.worker is not None and build_job.worker.tag == unit_tag:
                build_job.worker = None
                return
            if build_job.building is not None and build_job.building.tag == unit_tag:
                build_job.building = None
                build_job.done = True
                return
