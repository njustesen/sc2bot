
"""
A modular StarCraft II bot.
"""

import random
import time
import math
import sc2
import json
import pickle
from sc2 import Race, Difficulty, UnitTypeId, AbilityId
from s2clientprotocol import sc2api_pb2 as sc_pb
from sc2.player import Bot, Computer
from sc2bot.managers.army.simple_army_manager import SimpleArmyManager
from sc2bot.managers.army.advanced_army_manager import AdvancedArmyManager
from sc2bot.managers.building.simple_building_manager import SimpleBuildingManager
from sc2bot.managers.production.marine_production_manager import MarineProductionManager
from sc2bot.managers.production.reaper_marine_production_manager import ReaperMarineProductionManager
from sc2bot.managers.production.orbital_production_manager import OrbitalProductionManager
from sc2bot.managers.production.MLP_production_manager import MLPProductionManager
from sc2bot.managers.production.mlp_model import Net
from sc2bot.managers.scouting.simple_scouting_manager import SimpleScoutingManager
from sc2bot.managers.assault.simple_assault_manager import SimpleAssaultManager
from sc2bot.managers.assault.value_based_assault_manager import ValueBasedAssaultManager
from sc2bot.managers.worker.simple_worker_manager import SimpleWorkerManager
#from bayes_opt import BayesianOptimizationBayesianOptimization
#from bayes_opt import UtilityFunction
import numpy as np
import pickle
import enum

import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib import cm
from matplotlib import mlab


class TerranBot(sc2.BotAI):
    def __init__(self, features, verbose=True, model_path=None, model_name=None, timestamp=None, comment=""):
        super().__init__()
        self.iteration = 0
        self.builds = {}
        self.outputs = {}
        self.last_max_seen_enemy_units = None
        self.max_seen_enemy_units = {}
        self.last_max_allied_units = None
        self.max_allied_units = {}
        self.verbose = verbose
        self.worker_manager = SimpleWorkerManager(self)
        self.army_manager = AdvancedArmyManager(self)
        self.assault_manager = ValueBasedAssaultManager(self, self.army_manager, self.worker_manager)
        self.building_manager = SimpleBuildingManager(self, self.worker_manager)
        self.production_manager = MLPProductionManager(self,
            self.worker_manager,
            self.building_manager,
            features=features,
            model_path=model_path,
            model_name=model_name,
            timestamp=timestamp,
            comment=comment
        )
        # self.production_manager = MarineProductionManager(self, self.worker_manager, self.building_manager)
        self.scouting_manager = SimpleScoutingManager(self, self.worker_manager, self.building_manager)
        self.managers = [self.scouting_manager, self.production_manager, self.building_manager, self.assault_manager, self.army_manager, self.worker_manager]
        self.enemy_units = {}
        self.own_units = {}
        # print("Bot is ready")

    def print(self, str):
        if self.verbose:
            print(str)

    async def on_step(self, iteration):
        '''
        Calls
        :param iteration:
        :return:
        '''

        #print("Step: ", self.state.observation.game_loop)

        for unit in self.known_enemy_units | self.known_enemy_structures:
            self.enemy_units[unit.tag] = unit

        if self.last_max_seen_enemy_units:
            enemy_units = self.last_max_seen_enemy_units.copy()
        else:
            enemy_units = {}

        for unit in self.known_enemy_units:
            amount = len(list(filter(
                lambda x: x.name == unit.name, 
                self.known_enemy_units)
            ))
            if unit.name not in enemy_units:
                enemy_units[unit.name] = amount

            enemy_units[unit.name] = max(amount, enemy_units[unit.name])

        if enemy_units != self.last_max_seen_enemy_units:
            self.max_seen_enemy_units[self.state.observation.game_loop] = enemy_units
            self.last_max_seen_enemy_units = enemy_units


        self.iteration += 1

        # print(self.main_base_ramp.corner_depots)

        # try:
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
        # except Exception as err:
        #     print("TERRAN BOT:", err)

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
        if unit is not None and unit.tag not in self.own_units:
            if unit.name not in self.builds.keys():
                self.builds[unit.name] = 0
            self.builds[unit.name] += 1
        self.own_units[unit.tag] = unit

        if self.last_max_allied_units:
            allied_units = self.last_max_allied_units.copy()
        else:
            allied_units = {}

        for unit in self.units:
            amount = len(list(filter(
                lambda x: x.name == unit.name, 
                self.units)
            ))
            if unit.name not in allied_units:
                allied_units[unit.name] = amount

            allied_units[unit.name] = max(amount, allied_units[unit.name])

        if allied_units != self.max_allied_units:
            self.max_allied_units[self.state.observation.game_loop] = allied_units
            self.last_max_allied_units = allied_units

        for manager in self.managers:
            await manager.on_unit_created(unit)

    async def on_building_construction_started(self, unit):
        self.own_units[unit.tag] = unit
        for manager in self.managers:
            await manager.on_building_construction_started(unit)

    async def on_building_construction_complete(self, unit):
        for manager in self.managers:
            await manager.on_building_construction_complete(unit)


class ZergRushBot(sc2.BotAI):
    def __init__(self):
        self.drone_counter = 0
        self.extractor_started = False
        self.spawning_pool_started = False
        self.moved_workers_to_gas = False
        self.moved_workers_from_gas = False
        self.queeen_started = False
        self.mboost_started = False
        self.search = False
        self.s = 0
        self.searching = None

    def select_target(self):
        if self.known_enemy_structures.exists:
            return random.choice(self.known_enemy_structures).position

        if self.search:
            if self.s % 50 == 0:
                self.searching = self.enemy_start_locations[0].random_on_distance(50)
            self.s += 1
            print(self.searching)
            return self.searching

        return self.enemy_start_locations[0]

    async def on_step(self, iteration):

        if self.units(UnitTypeId.ZERGLING).exists and self.units(UnitTypeId.ZERGLING).closest_distance_to(self.enemy_start_locations[0]) < 10 and not self.known_enemy_structures.exists:
            self.search = True
            print("Searching")

        if iteration == 0:
            await self.chat_send("(glhf)")

        if not self.units(UnitTypeId.HATCHERY).ready.exists:
            for unit in self.workers | self.units(UnitTypeId.ZERGLING) | self.units(UnitTypeId.QUEEN):
                await self.do(unit.attack(self.select_target()))
            return

        hatchery = self.units(UnitTypeId.HATCHERY).ready.first
        larvae = self.units(UnitTypeId.LARVA)

        if self.units(UnitTypeId.ZERGLING).amount > 12:
            for zl in self.units(UnitTypeId.ZERGLING).idle:
                await self.do(zl.attack(self.select_target()))

        if self.vespene >= 100:
            '''
            sp = self.units(UnitTypeId.SPAWNINGPOOL).ready
            if sp.exists and self.minerals >= 100 and not self.mboost_started:
                await self.do(sp.first(RESEARCH_ZERGLINGMETABOLICBOOST))
                self.mboost_started = True
            '''
            if not self.moved_workers_from_gas:
                self.moved_workers_from_gas = True
                for drone in self.workers:
                    m = self.state.mineral_field.closer_than(10, drone.position)
                    await self.do(drone.gather(m.random, queue=True))

        if self.supply_left < 2:
            if self.can_afford(UnitTypeId.OVERLORD) and larvae.exists:
                await self.do(larvae.random.train(UnitTypeId.OVERLORD))

        if self.units(UnitTypeId.EXTRACTOR).ready.exists and not self.moved_workers_to_gas:
            self.moved_workers_to_gas = True
            extractor = self.units(UnitTypeId.EXTRACTOR).first
            for drone in self.workers.random_group_of(3):
                await self.do(drone.gather(extractor))

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
            if larvae.exists and larvae.amount >= 3 and self.can_afford(UnitTypeId.ZERGLING):
                if iteration % 100 == 0:
                    await self.do(larvae.random.train(UnitTypeId.ZERGLING))

        '''
        if self.drone_counter < 3:
            if self.can_afford(UnitTypeId.DRONE):
                self.drone_counter += 1
                await self.do(larvae.random.train(UnitTypeId.DRONE))
        '''
        if not self.extractor_started:
            if self.can_afford(UnitTypeId.EXTRACTOR) and self.workers.exists:
                drone = self.workers.random
                target = self.state.vespene_geyser.closest_to(drone.position)
                err = await self.do(drone.build(UnitTypeId.EXTRACTOR, target))
                if not err:
                    self.extractor_started = True

        elif not self.spawning_pool_started:
            if self.can_afford(UnitTypeId.SPAWNINGPOOL) and self.workers.exists:
                for d in range(4, 15):
                    pos = hatchery.position.to2.towards(self.game_info.map_center, d)
                    if await self.can_place(UnitTypeId.SPAWNINGPOOL, pos):
                        drone = self.workers.closest_to(pos)
                        err = await self.do(drone.build(UnitTypeId.SPAWNINGPOOL, pos))
                        if not err:
                            self.spawning_pool_started = True
                            break

        elif not self.queeen_started and self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
            if self.can_afford(UnitTypeId.QUEEN):
                r = await self.do(hatchery.train(UnitTypeId.QUEEN))
                if not r:
                    self.queeen_started = True


class Hydralisk(sc2.BotAI):
    def __init__(self):
        super().__init__()
        self.search = False
        self.s = 0
        self.searching = None

    def select_target(self):
        if self.known_enemy_structures.exists:
            return random.choice(self.known_enemy_structures).position

        if self.search:
            if self.s % 50 == 0:
                self.searching = self.enemy_start_locations[0].random_on_distance(50)
            self.s += 1
            return self.searching

        return self.enemy_start_locations[0]

    async def on_step(self, iteration):
        larvae = self.units(UnitTypeId.LARVA)
        forces = self.units(UnitTypeId.ZERGLING) | self.units(UnitTypeId.HYDRALISK)

        if self.units(UnitTypeId.HYDRALISK).exists and self.units(UnitTypeId.HYDRALISK).closest_distance_to(self.enemy_start_locations[0]) < 10 and not self.known_enemy_structures.exists:
            self.search = True

        if self.units(UnitTypeId.HYDRALISK).amount > 6 and iteration % 50 == 0:
            for unit in forces.idle:
                await self.do(unit.attack(self.select_target()))

        if self.supply_left < 2:
            if self.can_afford(UnitTypeId.OVERLORD) and larvae.exists:
                await self.do(larvae.random.train(UnitTypeId.OVERLORD))
                return

        if not self.townhalls.exists:
            for unit in self.units(UnitTypeId.DRONE) | self.units(UnitTypeId.QUEEN) | forces:
                await self.do(unit.attack(self.enemy_start_locations[0]))
            return
        else:
            hq = self.townhalls.first

        if hq.assigned_harvesters < hq.ideal_harvesters:
            if self.can_afford(UnitTypeId.DRONE) and larvae.exists:
                larva = larvae.random
                await self.do(larva.train(UnitTypeId.DRONE))
                return

        if not self.townhalls.amount < 2:
            if self.can_afford(UnitTypeId.HATCHERY):
                loc = await self.get_next_expansion()
                await self.build(UnitTypeId.HATCHERY, near=loc)
                return

        if not (self.units(UnitTypeId.SPAWNINGPOOL).exists or self.already_pending(UnitTypeId.SPAWNINGPOOL)):
            if self.can_afford(UnitTypeId.SPAWNINGPOOL):
                await self.build(UnitTypeId.SPAWNINGPOOL, near=hq.position)

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
            if not self.units(UnitTypeId.LAIR).exists and hq.noqueue:
                if self.can_afford(UnitTypeId.LAIR):
                    await self.do(hq.build(UnitTypeId.LAIR))

        if self.units(UnitTypeId.LAIR).ready.exists:
            if not (self.units(UnitTypeId.HYDRALISKDEN).exists or self.already_pending(UnitTypeId.HYDRALISKDEN)):
                if self.can_afford(UnitTypeId.HYDRALISKDEN):
                    await self.build(UnitTypeId.HYDRALISKDEN, near=hq.position)

        if self.units(UnitTypeId.EXTRACTOR).amount < 2 and not self.already_pending(UnitTypeId.EXTRACTOR):
            if self.can_afford(UnitTypeId.EXTRACTOR):
                drone = self.workers.random
                target = self.state.vespene_geyser.closest_to(drone.position)
                err = await self.do(drone.build(UnitTypeId.EXTRACTOR, target))

        if self.units(UnitTypeId.HYDRALISKDEN).ready.exists:
            if self.can_afford(UnitTypeId.HYDRALISK) and larvae.exists:
                await self.do(larvae.random.train(UnitTypeId.HYDRALISK))
                return

        '''
        if hq.assigned_harvesters < hq.ideal_harvesters:
            if self.can_afford(UnitTypeId.DRONE) and larvae.exists:
                larva = larvae.random
                await self.do(larva.train(UnitTypeId.DRONE))
                return
        '''
        for a in self.units(UnitTypeId.EXTRACTOR):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
            if not self.units(UnitTypeId.QUEEN).exists and hq.is_ready and hq.noqueue:
                if self.can_afford(UnitTypeId.QUEEN):
                    await self.do(hq.train(UnitTypeId.QUEEN))

        if self.units(UnitTypeId.ZERGLING).amount < 4 and self.minerals > 1000:
            if larvae.exists and self.can_afford(UnitTypeId.ZERGLING):
                await self.do(larvae.random.train(UnitTypeId.ZERGLING))
