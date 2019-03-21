import random
import sc2
import asyncio
from sc2bot.managers.interfaces import WorkerManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from random import randint
from typing import List, Dict, Set, Tuple, Any, Optional, Union # mypy type checking
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.data import ActionResult
from sc2.units import Units


class RepairJob:

    def __init__(self, building):
        self.workers = []
        self.building = building
        self.done = False


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
        self.repair_jobs = []

    async def run(self):

        for idle_worker in self.bot.units(UnitTypeId.SCV).idle:
            minerals = self.bot.state.units.mineral_field.closest_to(self.bot.start_location)
            self.actions.append(idle_worker.gather(minerals))

        if self.bot.iteration % 100 == 0:
            await self.distribute()

        for building in self.bot.units.structure.ready:
            if building.health < building.health_max:
                found = False
                for repair_job in self.repair_jobs:
                    if repair_job.building.tag == building.tag:
                        found = True
                        break
                if not found:
                    self.repair_jobs.append(RepairJob(building))

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
                if build_job.worker is not None:
                    minerals = self.bot.state.units.mineral_field.closest_to(self.bot.start_location)
                    self.actions.append(build_job.worker.gather(minerals))
                continue

            # Worker died
            if build_job.worker is None:
                build_job.worker = self._get_builder(build_job.location)
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

        # print(len(self.repair_jobs), "repair jobs")
        for repair_job in self.repair_jobs:
            # print("-", repair_job.building.type_id)

            # Check if done
            if repair_job.building is None or repair_job.building.health * 1.05 >= repair_job.building.health_max:
                repair_job.done = True

            # Job cancelled or completed
            if repair_job.done:
                #for worker in repair_job.workers:
                    #if worker is not None:
                        #minerals = self.bot.state.units.mineral_field.closest_to(worker)
                        #self.actions.append(worker.gather(minerals))
                await self.distribute()
                continue

            # Worker died
            for worker in repair_job.workers:
                if worker is None:
                    w = self._get_repairer(repair_job)
                    if w is not None:
                        repair_job.workers.append(w)
                        self.actions.append(w.repair(repair_job.building))
                else:
                    self.actions.append(worker.repair(repair_job.building))

            repair_job.workers = [worker for worker in repair_job.workers if worker is not None]

            # Need extra workers
            if len(repair_job.workers) < 3 and repair_job.building.type_id in [UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND,
                                       UnitTypeId.PLANETARYFORTRESS, UnitTypeId.BUNKER]:
                w2 = self._get_repairer(repair_job)
                if w2 is not None:
                    repair_job.workers.append(w2)
                    self.actions.append(w2.repair(repair_job.building))

            # No worker
            if len(repair_job.workers) == 0:
                w = self._get_repairer(repair_job)
                if w is not None:
                    repair_job.workers.append(w)
                    self.actions.append(w.repair(repair_job.building))

        self.repair_jobs = [repair_job for repair_job in self.repair_jobs if not repair_job.done]

        # await self.bot.do_actions(self.combinedActions)
        # self.combinedActions = []

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
                    if building == UnitTypeId.SUPPLYDEPOT and self.bot.units(UnitTypeId.BUNKER).amount == 0:
                        placement_positions = self.bot.main_base_ramp.corner_depots
                        if depots:
                            placement_positions = {d for d in placement_positions if
                                                         depots.closest_distance_to(d) > 1}
                    elif building == UnitTypeId.BARRACKS and self.bot.units(UnitTypeId.BARRACKS).amount + self.bot.already_pending(UnitTypeId.BARRACKS) == 0:
                        placement_positions = [self.bot.main_base_ramp.barracks_correct_placement]

                    if len(placement_positions) == 0:
                        if building == UnitTypeId.SUPPLYDEPOT:
                            loc = await self.find_placement(building, self.bot.start_location, placement_step=2)
                        elif building == UnitTypeId.BUNKER:
                            if self.bot.townhalls.amount == 1:
                                loc = await self.find_placement(building, list(self.bot.main_base_ramp.corner_depots)[1],
                                                                placement_step=1)
                            else:
                                loc = await self.find_placement(building,
                                                                list(self.bot.townhalls)[1].position,
                                                                placement_step=1)
                        elif self.bot.units(UnitTypeId.BARRACKS).exists:
                            loc = await self.find_placement(building, self.bot.units(UnitTypeId.BARRACKS)[0].position, placement_step=7, random_alternative=False)
                        else:
                            loc = await self.find_placement(building, self.bot.units.structure[0].position,
                                                            placement_step=7)
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
        '''
        for w in self.bot.workers:
            self.actions.append(w.attack(location))
        '''
        pass

    async def defend(self, location):
        for w in self.bot.workers:
            self.actions.append(w.attack(location))

    def _get_builder(self, location=None):
        ws = self.bot.workers.gathering
        if ws:  # if workers found
            not_scouts = Units([w for w in ws if self.scouting_worker is None or w.tag != self.scouting_worker.tag], self.bot.game_data())
            if not_scouts.amount > 0:
                if location is None:
                    return not_scouts.furthest_to(not_scouts.center)
                else:
                    return not_scouts.closest_to(location)
        return None

    def _get_repairer(self, repair_job):
        ws = self.bot.workers.gathering
        if ws:  # if workers found
            not_scouts = Units([w for w in ws if self.scouting_worker is None or w.tag != self.scouting_worker.tag], self.bot.game_data())
            not_reparing = []
            for repair_job in self.repair_jobs:
                tags = [worker.tag for worker in repair_job.workers if worker is not None]
                for worker in not_scouts:
                    if worker.tag not in tags:
                        not_reparing.append(worker)
            not_reparing = Units(not_reparing, self.bot.game_data())
            if not_reparing.amount > 0:
                return ws.closest_to(repair_job.building)
        return None

    async def distribute(self):
        self.distribute_workers()

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

    def has_unstarted_plan(self):
        for build_job in self.build_jobs:
            if build_job.building is None:
                return True
        return False

    async def find_placement(self, building: UnitTypeId, near: Union[Unit, Point2, Point3], max_distance: int=20, random_alternative: bool=True, placement_step: int=2) -> Optional[Point2]:
        """Finds a placement location for building."""

        assert isinstance(building, (AbilityId, UnitTypeId))
        assert isinstance(near, Point2)

        if isinstance(building, UnitTypeId):
            building = self.bot.game_data().units[building.value].creation_ability
        else:  # AbilityId
            building = self.bot.game_data().abilities[building.value]

        if await self.bot.can_place(building, near):
            return near

        if max_distance == 0:
            return None

        for distance in range(placement_step, max_distance, placement_step):

            possible_positions = [Point2(p).offset(near).to2 for p in (
                    [(dx, int(-distance/2)) for dx in range(-distance, distance + 1, placement_step)] +
                    [(dx, int(distance/2)) for dx in range(-distance, distance + 1, placement_step)] +
                    [(-distance, int(dy/2)) for dy in range(-distance, distance + 1, placement_step)] +
                    [(distance, int(dy/2)) for dy in range(-distance, distance + 1, placement_step)]
            )]
            if building == UnitTypeId.FACTORY:
                possible_positions = [pos for pos in possible_positions if self.bot.main_base_ramp.bottom_center.distance_to(pos) > 5]
            possible_positions = [pos for pos in possible_positions if pos.x != near.x]

            res = await self.bot.client().query_building_placement(building, possible_positions)
            possible = [p for r, p in zip(res, possible_positions) if r == ActionResult.Success]

            if not possible:
                continue

            if building in [AbilityId.TERRANBUILD_BARRACKS, AbilityId.TERRANBUILD_FACTORY, AbilityId.TERRANBUILD_STARPORT]:
                #add_on = self.bot.game_data().units[building.value].creation_ability
                add_on = AbilityId.TERRANBUILD_COMMANDCENTER
                possible_positions_add_on = [(pos.x+4, pos.y+1) for pos in possible]
                res_add_on = await self.bot.client().query_building_placement(add_on, possible_positions_add_on)
                possible = [possible[i] for i in range(len(possible)) if res_add_on[i] == ActionResult.Success]

            if random_alternative:
                return random.choice(possible)
            else:
                return min(possible, key=lambda p: p.distance_to(near))

        return None

    async def on_building_construction_started(self, building):
        for build_job in self.build_jobs:
            if building.type_id == build_job.building_type:
                build_job.under_construction = True
                build_job.building = building

    async def on_building_construction_complete(self, building):
        for build_job in self.build_jobs:
            if build_job.building is not None and building.tag == build_job.building.tag:
                build_job.under_construction = False
                build_job.done = True
        self.distribute_workers()

    async def on_unit_destroyed(self, unit_tag):
        if self.scouting_worker is not None and self.scouting_worker.tag == unit_tag:
            self.scouting_worker = None

        # Check if
        for repair_job in self.repair_jobs:
            for i in range(len(repair_job.workers)):
                worker = repair_job.workers[i]
                if worker is not None and worker.tag == unit_tag:
                    repair_job.workers[i] = None
                    break
            if repair_job.building.tag == unit_tag:
                repair_job.done = True
                break

        for build_job in self.build_jobs:
            if build_job.worker is not None and build_job.worker.tag == unit_tag:
                build_job.worker = None
                break
            if build_job.building is not None and build_job.building.tag == unit_tag:
                build_job.building = None
                build_job.done = True
                break
