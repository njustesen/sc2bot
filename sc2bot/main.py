import random
import time
import math
import sc2
import json
import pickle
import os
from sc2 import Race, Difficulty, UnitTypeId, AbilityId
from s2clientprotocol import sc2api_pb2 as sc_pb
from sc2.player import Bot, Computer
from data_utils import Option
from bot import Hydralisk, ZergRushBot, TerranBot

os.environ['SC2PATH'] = "/media/mgd/DATA/new_sc2"

def run_game(features, opp, cluster_id=None, comment="", timestamp=int(time.time())):
    #return np.mean(features) - random.random()*0.1
    replay_name = f"replays/{timestamp}_sc2bot_{comment}.sc2replay"

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

        result = sc2.run_game(sc2.maps.get("CatalystLE"),
                                players=[Bot(Race.Terran, tbot), opponent],
                                save_replay_as=replay_name,
                                realtime=False)
        return 0 if result[0].name == "Defeat" else (1 if result[0].name == "Victory" else 0.5), tbot
    except Exception as e:
        # raise e
        print(e)
        return 0, tbot


def main(n, comment="", timestamp=int(time.time())):
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
            # Option(10, features_10)
            # Option(11, features_11),
            Option(30, features_30),
            # Option(32, features_32)
        ]

        #options = [Option(10000, no_features)]

        #optinons = [Option(10, features_10)]

        for i in range(n):
            for option in options:
                result, bot = run_game(option.features, "easy", comment=comment, timestamp=timestamp)
                print(result)
                option.builds.append(bot.builds)
                option.wins += 1 if result > 0 else 0
                option.draws += 0.5 if result == 0.5 else 0
                option.n += 1
                print(json.dumps(option.builds))

            pickle.dump(options, open(f"./pickled_data/{timestamp}_options_{n}_{comment}.p", "wb"))
            with open(f"./pickled_data/{timestamp}_options_{n}_{comment}.p", "w") as f:
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

    for _ in range(n):
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
    timestamp = int(time.time())
    main(1, comment="test", timestamp=timestamp)
    # analyse(100)
    # ucb(100, "hydra")
    #ucb(100, "zerg")
    #analyse_ucb(100, "hydra")
    #clusters(100)
    # result = sc2.run_game(sc2.maps.get("(2)CatalystLE"),
    #                         players=[Bot(Race.Zerg, Hydralisk()), Computer(Race.Zerg, Difficulty.Easy)],
    #                         save_replay_as="two_bots",
    #                         realtime=False)
