
"""
A modular StarCraft II bot.
"""

import random
import time
import math
import sc2
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

AIBuild = enum.Enum("AIBuild", sc_pb.AIBuild.items())


class TerranBot(sc2.BotAI):

    builds = {}

    def __init__(self, features, verbose=True):
        super().__init__()
        builds = {}
        self.iteration = 0
        self.verbose = verbose
        self.worker_manager = SimpleWorkerManager(self)
        self.army_manager = AdvancedArmyManager(self)
        self.assault_manager = ValueBasedAssaultManager(self, self.army_manager, self.worker_manager)
        self.building_manager = SimpleBuildingManager(self, self.worker_manager)
        self.production_manager = MLPProductionManager(self, self.worker_manager, self.building_manager, features=features)
        # self.production_manager = MLPProductionManager(self, self.worker_manager, self.building_manager, "old/TvZ_3x128_features_None_1552640939", features=[0.5, 0.5])
        # self.production_manager = MarineProductionManager(self, self.worker_manager, self.building_manager)
        # self.production_manager = ReaperMarineProductionManager(self, self.worker_manager, self.building_manager)
        # self.production_manager = OrbitalProductionManager(self, self.worker_manager, self.building_manager)
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


        self.iteration += 1

        try:
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
        except Exception as err:
            print(err)

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
        if unit.name not in TerranBot.builds:
            TerranBot.builds[unit.name] = 0
        TerranBot.builds[unit.name] += 1
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


class Hydralisk(sc2.BotAI):
    def select_target(self):
        if self.known_enemy_structures.exists:
            return random.choice(self.known_enemy_structures).position

        return self.enemy_start_locations[0]

    async def on_step(self, iteration):
        larvae = self.units(UnitTypeId.LARVA)
        forces = self.units(UnitTypeId.ZERGLING) | self.units(UnitTypeId.HYDRALISK)

        if self.units(UnitTypeId.HYDRALISK).amount > 10 and iteration % 50 == 0:
            for unit in forces.idle:
                await self.do(unit.attack(self.select_target()))

        if self.supply_left < 2:
            if self.can_afford(UnitTypeId.OVERLORD) and larvae.exists:
                await self.do(larvae.random.train(UnitTypeId.OVERLORD))
                return

        if self.units(UnitTypeId.HYDRALISKDEN).ready.exists:
            if self.can_afford(UnitTypeId.HYDRALISK) and larvae.exists:
                await self.do(larvae.random.train(UnitTypeId.HYDRALISK))
                return

        if not self.townhalls.exists:
            for unit in self.units(UnitTypeId.DRONE) | self.units(UnitTypeId.QUEEN) | forces:
                await self.do(unit.attack(self.enemy_start_locations[0]))
            return
        else:
            hq = self.townhalls.first

        for queen in self.units(UnitTypeId.QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(queen(AbilityId.EFFECT_INJECTLARVA, hq))

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

        if hq.assigned_harvesters < hq.ideal_harvesters:
            if self.can_afford(UnitTypeId.DRONE) and larvae.exists:
                larva = larvae.random
                await self.do(larva.train(UnitTypeId.DRONE))
                return

        for a in self.units(UnitTypeId.EXTRACTOR):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        if self.units(UnitTypeId.SPAWNINGPOOL).ready.exists:
            if not self.units(UnitTypeId.QUEEN).exists and hq.is_ready and hq.noqueue:
                if self.can_afford(UnitTypeId.QUEEN):
                    await self.do(hq.train(UnitTypeId.QUEEN))

        if self.units(UnitTypeId.ZERGLING).amount < 20 and self.minerals > 1000:
            if larvae.exists and self.can_afford(UnitTypeId.ZERGLING):
                await self.do(larvae.random.train(UnitTypeId.ZERGLING))

def run_game(features):

    #return np.mean(features) - random.random()*0.1
    replay_name = f"replays/sc2bot_{int(time.time())}.sc2replay"
    # Multiple difficulties for enemy bots available https://github.com/Blizzard/s2client-api/blob/ce2b3c5ac5d0c85ede96cef38ee7ee55714eeb2f/include/sc2api/sc2_gametypes.h#L30
    try:
        result = sc2.run_game(sc2.maps.get("(2)CatalystLE"),
                                players=[Bot(Race.Terran, TerranBot(features=features, verbose=True)), Bot(Race.Zerg, Hydralisk())],
                                save_replay_as=replay_name,
                                realtime=False)
        return 0 if result.name == "Defeat" else (1 if result.name == "Victory" else 0.5)
    except Exception as e:
        print(e)
        return 0


class Option:

    def __init__(self, cluster_id, features):
        self.cluster_id = cluster_id
        self.features = features
        self.n = 0
        self.wins = 0
        self.builds = []


def main():

    # Cluster 10 units
    # ['Hellion', 'Cyclone', 'Marine', 'WidowMine', 'Reaper', 'Thor', 'SiegeTank', 'Liberator', 'Banshee', 'Raven', 'Medivac', 'Marauder', 'VikingFighter']
    # Centroid of cluster 10 with position (0.02123669907450676,0.5240920186042786)
    features_10 = [0.02123669907450676, 0.5240920186042786]

    # Cluster 11 units
    # ['Marine', 'WidowMine', 'Medivac']
    # Centroid of cluster 11 with position (0.5667153596878052,0.01560366153717041)
    features_11 = [0.5667153596878052,0.01560366153717041]

    # Cluster 30 units
    # ['Marine', 'Marauder', 'WidowMine', 'Medivac', 'Reaper', 'Liberator', 'Hellion', 'SiegeTank', 'VikingFighter', 'Thor', 'Banshee', 'Cyclone', 'Raven', 'Ghost']
    # Centroid of cluster 30 with position (0.8493908047676086,0.44843146204948425)
    features_30 = [0.8493908047676086,0.44843146204948425]

    # Cluster 32 units
    # ['Reaper', 'Marine', 'Hellion', 'SiegeTank', 'WidowMine', 'Banshee', 'Cyclone', 'Marauder', 'Medivac']
    # Centroid of cluster 32 with position (0.6273395419120789,0.977607786655426)
    features_32 = [0.6273395419120789, 0.977607786655426]

    no_features = []

    options = [
        Option(10, features_10),
        Option(11, features_11),
        Option(30, features_30),
        Option(32, features_32)
    ]

    for i in range(1):
        for option in options:
            result = run_game(option.features)
            print(result)
            option.builds.append(TerranBot.builds)
            option.wins += 1 if result > 0 else 0
            option.n += 1

    print(result)

if __name__ == '__main__':
    main()
