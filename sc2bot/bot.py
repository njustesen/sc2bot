
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

    def __init__(self, features, verbose=True, model_name=None):
        super().__init__()
        self.iteration = 0
        self.builds = {}
        self.verbose = verbose
        self.worker_manager = SimpleWorkerManager(self)
        self.army_manager = AdvancedArmyManager(self)
        self.assault_manager = ValueBasedAssaultManager(self, self.army_manager, self.worker_manager)
        self.building_manager = SimpleBuildingManager(self, self.worker_manager)
        # self.production_manager = MLPProductionManager(self, self.worker_manager, self.building_manager, features=features, model_name=model_name)
        # self.production_manager = MLPProductionManager(self, self.worker_manager, self.building_manager, "old/TvZ_3x128_features_None_1552640939", features=[0.5, 0.5])
        self.production_manager = MarineProductionManager(self, self.worker_manager, self.building_manager)
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
            print("TERRAN BOT:", err)

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

def run_game(features, opp, cluster_id=None, comment=""):

    #return np.mean(features) - random.random()*0.1
    replay_name = f"replays/sc2bot_{int(time.time())}.sc2replay"
    if cluster_id is not None:
        tbot = TerranBot(features=features, verbose=False, model_name=f'cluster{cluster_id}')
    else:
        tbot = TerranBot(features=features, verbose=False)
    # Multiple difficulties for enemy bots available https://github.com/Blizzard/s2client-api/blob/ce2b3c5ac5d0c85ede96cef38ee7ee55714eeb2f/include/sc2api/sc2_gametypes.h#L30
    if cluster_id is not None:
        tbot = TerranBot(features=features, verbose=False, model_name=f'cluster{cluster_id}')
    else:
        tbot = TerranBot(features=features, verbose=False)
    try:
        if opp == "easy":
            opponent = Computer(Race.Zerg, Difficulty.Easy)
        elif opp == "hydra":
            opponent = Bot(Race.Zerg, Hydralisk())
        elif opp == "zerg":
            opponent = Bot(Race.Zerg, ZergRushBot())

        result = sc2.run_game(sc2.maps.get("(2)CatalystLE"),
                                players=[Bot(Race.Terran, tbot), opponent],
                                save_replay_as=replay_name,
                                realtime=False)
        return 0 if result[0].name == "Defeat" else (1 if result[0].name == "Victory" else 0.5), tbot
    except Exception as e:
        # raise e
        print(e)
        return 0, tbot


class Option:

    def __init__(self, cluster_id, features):
        self.cluster_id = cluster_id
        self.features = features
        self.n = 0
        self.wins = 0
        self.draws = 0
        self.builds = []

    def to_json(self):
        return {
            "cluster_id": self.cluster_id,
            "features": self.features,
            "n": self.n,
            "wins": self.wins,
            "draws": self.draws,
            "builds": self.builds
        }



def main(n, comment=""):
    if True:
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

        #options = [Option(10000, no_features)]

        #optinons = [Option(10, features_10)]

        for i in range(n):
            for option in options:
                result, bot = run_game(option.features, "easy", comment=comment)
                print(result)
                option.builds.append(bot.builds)
                option.wins += 1 if result > 0 else 0
                option.draws += 0.5 if result == 0.5 else 0
                option.n += 1
                print(json.dumps(option.builds))

            pickle.dump(options, open(f"options_{n}_no_features.p", "wb"))
            with open(f"options_{n}_no_features.json", "w") as f:
                f.write(str([option.to_json() for option in options]))

    options = pickle.load(open(f"options_{n}_no_features.p", "rb"))
    for option in options:
        print("Cluster ID", option.cluster_id)
        print("Wins", option.wins)
        all_builds = {}
        for b_dict in option.builds:
            for build, c in b_dict.items():
                if build not in all_builds:
                    all_builds[build] = 0
                all_builds[build] += c

        sorted_builds = reversed(sorted(all_builds, key=all_builds.get))
        for build in sorted_builds:
            if build != "SCV":
                print(f"\t{build}: {(all_builds[build] / option.n)}")

def analyse(n):
    options = pickle.load(open(f"options_{n}_no_features.p", "rb"))
    builds = []
    option_builds = {}
    for option in options:
        print("Cluster ID", option.cluster_id)
        #print("Wins", option.wins)
        all_builds = {}
        for b_dict in option.builds:
            for build, c in b_dict.items():
                if build not in all_builds:
                    all_builds[build] = []
                if build not in builds:
                    builds.append(build)
                all_builds[build].append(c)
        print(all_builds)
        option_builds[option.cluster_id] = all_builds

    sorted_builds = list(sorted(builds))
    option_mean_builds = {}
    for option in options:
        option_mean_builds[option.cluster_id] = {}
        avgs = []
        stds = []
        print("Cluster ID", option.cluster_id)
        for build in sorted_builds:
            if build in ["SCV", "MULE"]:
                continue
            if build in option_builds[option.cluster_id]:
                arr = option_builds[option.cluster_id][build]
                arr = np.concatenate((arr, np.zeros(n-len(arr))))
                m = np.mean(arr)
                s = np.std(arr)
                print(f"{build}: {m} +/- {s}")
                avgs.append(m)
                stds.append(s)
                option_mean_builds[option.cluster_id][build] = m
        #print(avgs)
        #print(stds)
        builds = option_mean_builds[option.cluster_id]
        print(json.dumps(builds))


def analyse_ucb(n, name):
    options = pickle.load(open(f"ucb_{name}_options_{n}.p", "rb"))
    builds = []
    all_builds = {}
    for option in options:
        print("Cluster ID", option.cluster_id)
        print(f"Wins/Draws/Losses/Games {option.wins}/{option.draws}/{option.n-option.wins-option.draws}/{option.n}")

        for b_dict in option.builds:
            for build, c in b_dict.items():
                if build not in all_builds:
                    all_builds[build] = []
                    builds.append(build)
                all_builds[build].append(c)
        print(all_builds)

    sorted_builds = list(sorted(builds))

    avgs = []
    stds = []
    for build in sorted_builds:
        if build in ["SCV", "MULE"]:
            continue
        arr = all_builds[build]
        arr = np.concatenate((arr, np.zeros(n - len(arr))))
        m = np.mean(arr)
        s = np.std(arr)
        print(build)
        print(f"Mean: {m}")
        print(f"Mean: {s}")
        avgs.append(m)
        stds.append(s)
    print(avgs)
    print(stds)

def ind_max(x):
    m = max(x)
    return x.index(m)


class UCB1():
    def __init__(self):
        return

    def initialize(self, n_arms):
        self.counts = [0 for col in range(n_arms)]
        self.values = [0.0 for col in range(n_arms)]
        return

    def select_arm(self):
        n_arms = len(self.counts)
        for arm in range(n_arms):
            if self.counts[arm] == 0:
                return arm

        ucb_values = [0.0 for arm in range(n_arms)]
        total_counts = sum(self.counts)
        for arm in range(n_arms):
            bonus = math.sqrt((2 * math.log(total_counts)) / float(self.counts[arm]))
            ucb_values[arm] = self.values[arm] + bonus
        return ind_max(ucb_values)

    def update(self, chosen_arm, reward):
        self.counts[chosen_arm] = self.counts[chosen_arm] + 1
        n = self.counts[chosen_arm]

        value = self.values[chosen_arm]
        new_value = ((n - 1) / float(n)) * value + (1 / float(n)) * reward
        self.values[chosen_arm] = new_value
        return

def ucb(n, opp):
    # Cluster 10 units
    # ['Hellion', 'Cyclone', 'Marine', 'WidowMine', 'Reaper', 'Thor', 'SiegeTank', 'Liberator', 'Banshee', 'Raven', 'Medivac', 'Marauder', 'VikingFighter']
    # Centroid of cluster 10 with position (0.02123669907450676,0.5240920186042786)
    features_10 = [0.02123669907450676, 0.5240920186042786]

    # Cluster 11 units
    # ['Marine', 'WidowMine', 'Medivac']
    # Centroid of cluster 11 with position (0.5667153596878052,0.01560366153717041)
    features_11 = [0.5667153596878052, 0.01560366153717041]

    # Cluster 30 units
    # ['Marine', 'Marauder', 'WidowMine', 'Medivac', 'Reaper', 'Liberator', 'Hellion', 'SiegeTank', 'VikingFighter', 'Thor', 'Banshee', 'Cyclone', 'Raven', 'Ghost']
    # Centroid of cluster 30 with position (0.8493908047676086,0.44843146204948425)
    features_30 = [0.8493908047676086, 0.44843146204948425]

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

    # options = [Option(10000, no_features)]

    results = []

    ucb1 = UCB1()
    ucb1.initialize(len(options))

    for i in range(n):
        option_idx = ucb1.select_arm()
        option = options[option_idx]
        result, bot = run_game(option.features, opp=opp)
        print(result)
        option.builds.append(bot.builds)
        option.wins += 1 if result > 0 else 0
        option.draws += 0.5 if result == 0.5 else 0
        results.append(result)
        option.n += 1
        ucb1.update(option_idx, result)
        print(json.dumps(option.builds))

        pickle.dump(options, open(f"ucb_{opp}_options_{n}.p", "wb"))
        with open(f"ucb_{opp}_options_{n}.json", "w") as f:
            f.write(str([option.to_json() for option in options]))

    print(results)
    print(np.mean(results))

    options = pickle.load(open(f"ucb_{opp}_options_{n}.p", "rb"))
    for option in options:
        print("Cluster ID", option.cluster_id)
        print("Wins", option.wins)
        all_builds = {}
        for b_dict in option.builds:
            for build, c in b_dict.items():
                if build not in all_builds:
                    all_builds[build] = 0
                all_builds[build] += c

        sorted_builds = reversed(sorted(all_builds, key=all_builds.get))
        for build in sorted_builds:
            if build != "SCV":
                print(f"\t{build}: {(all_builds[build] / option.n)}")

def clusters(n):

    options = [
        Option(10, []),
        Option(11, []),
        Option(30, []),
        Option(32, [])
    ]

    wins = 0

    for i in range(n):
        for option in options:
            result, bot = run_game(option.features, option.cluster_id)
            print(result)
            option.builds.append(bot.builds)
            option.wins += 1 if result > 0 else 0
            option.n += 1
            print(json.dumps(option.builds))

        pickle.dump(options, open(f"options_{n}_clusters.p", "wb"))
        with open(f"options_{n}_no_features.json", "w") as f:
            f.write(str([option.to_json() for option in options]))

    options = pickle.load(open(f"options_{n}_clusters.p", "rb"))
    for option in options:
        print("Cluster ID", option.cluster_id)
        print("Wins", option.wins)
        all_builds = {}
        for b_dict in option.builds:
            for build, c in b_dict.items():
                if build not in all_builds:
                    all_builds[build] = 0
                all_builds[build] += c

        sorted_builds = reversed(sorted(all_builds, key=all_builds.get))
        for build in sorted_builds:
            if build != "SCV":
                print(f"\t{build}: {(all_builds[build] / option.n)}")

if __name__ == '__main__':
    # main(1, comment="test")
    # analyse(100)
    # ucb(100, "hydra")
    #ucb(100, "zerg")
    #analyse_ucb(100, "hydra")
    #clusters(100)
    result = sc2.run_game(sc2.maps.get("(2)CatalystLE"),
                            players=[Bot(Race.Zerg, Hydralisk()), Computer(Race.Zerg, Difficulty.Easy)],
                            save_replay_as="two_bots",
                            realtime=False)