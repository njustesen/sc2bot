import random
import time
import math
import sc2
import json
import pickle
import os
import numpy as np
from sc2 import Race, Difficulty, UnitTypeId, AbilityId
from s2clientprotocol import sc2api_pb2 as sc_pb
from sc2.player import Bot, Computer
from data_utils import Option, BayesianIteration
from bot import Hydralisk, ZergRushBot, TerranBot
from bayes_opt import BayesianOptimization, UtilityFunction
from bayes_opt.observer import JSONLogger
from bayes_opt.event import Events
import matplotlib.pyplot as plt

os.environ['SC2PATH'] = "/media/mgd/DATA/new_sc2"

def run_game(features, opp, features_name, model_path, comment="", timestamp=""):
    replay_name = f"replays/{timestamp}_sc2bot_{features_name}_{comment}.sc2replay"

    # if features_name == "PCA":
    tbot = TerranBot(
        features=features,
        verbose=False,
        # model_name=f'cluster{cluster_id}',
        model_path=model_path,
        timestamp=timestamp,
        comment=comment
    )
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
        # print(result)
        # print(type(result))
        # print(dir(result))
        # print(result.name)
        # _ = input("Press enter to continue")
        print(f"Renaming from {replay_name} to {replay_name.replace('.sc2replay', result.name +  '.SC2replay')}")
        os.rename(replay_name, f"{replay_name.replace('.sc2replay', f'{result.name}.SC2replay')}")
        return 0 if result.name == "Defeat" else (1 if result.name == "Victory" else 0.5), tbot
    except Exception as e:
        # raise e
        print(e)
        return 0, tbot


def feature_experiment(n, features_name, cluster_key, cluster_centers_path, model_path, comment="", timestamp=int(time.time())):
    # Loading up the cluster centers: 
    cluster_key = str(cluster_key)

    with open(cluster_centers_path) as f:
        cluster_centers = json.load(f)[features_name]
    
    features = cluster_centers[cluster_key]
    print(f"Using features {features}, from cluster {cluster_key}'s center.")

    option = Option(features_name, comment, features)
    for i in range(n):
        print("-"*80)
        print("\n")
        print("NEW GAME")
        print("\n")
        print("-"*80)
        result, bot = run_game(option.features, "easy", features_name, model_path, comment=comment+f"_{i}_", timestamp=timestamp)
        option.builds.append(bot.builds)
        # option.enemy_builds.append(bot.max_seen_enemy_units)
        # option.max_allied_units.append(bot.max_allied_units)
        option.wins += 1 if result > 0 else 0
        option.draws += 0.5 if result == 0.5 else 0
        option.n += 1

        with open(f"./model_outputs/{timestamp}_{features_name}_outputs_{comment}_{i}.json", "w") as f:
            json.dump(bot.outputs, f)

        with open(f"./builds/{timestamp}_{features_name}_builds_{comment}_{i}.json", "w") as f:
            json.dump(bot.builds, f)
        
        with open(f"./enemy_units/{timestamp}_{features_name}_enemy_units_{comment}_{i}.json", "w") as f:
            json.dump(bot.max_seen_enemy_units, f)

        with open(f"./allied_units/{timestamp}_{features_name}_max_allied_units_{comment}_{i}.json", "w") as f:
            json.dump(bot.max_allied_units, f)

    print("-"*80)
    print("\n\n\nFINAL RESULTS\n\n\n")
    print("-"*80)
    with open(f"./options_data/{timestamp}_{features_name}_option_{comment}.json", "w") as f:
        json.dump(option.to_json(), f)

    print("Name", option.name)
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

class BasicObserver:
    def update(self, event, instance):
        """Does whatever you want with the event and `BayesianOptimization` instance."""
        # print("Event `{}` was observed".format(event))
        Z = get_Z(instance)
        fig = plt.figure()
        im = plt.imshow(Z)
        plt.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
        # plt.title(f"Mean Sample for {features_name}")
        fig.colorbar(im)
        plt.show()
        # plt.savefig(f"{timestamp}_mean_sample_{features_name}_{comment}_{iteration}.pdf", format="pdf")
        plt.close()



def objective_function(x, y, iteration, features_name, model_path, comment, timestamp):
    # I could be storing all relevant information about the bot's build here too.
    result, _ = run_game([x, y], "easy", features_name, model_path, comment=comment+f"_Bayesian_Optimization_{iteration}_", timestamp=timestamp)
    return result


def get_Z(optimizer):
    x = y = np.arange(-1.0, 1.0, 0.05)
    X, Y = np.meshgrid(x, y)
    # print(X)
    Z = np.zeros_like(X)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            Z[i,j] = optimizer._gp.sample_y(np.array([[X[i,j], Y[i,j]]]))[:, 0][0]
    print(Z)
    return Z


def run_point(xy, optimizer, iteration, features_name, bayes_log, model_path, comment, timestamp):
    target = objective_function(
        xy["x"],
        xy["y"],
        iteration,
        features_name,
        model_path,
        comment,
        timestamp
    )
    optimizer.register(params=xy, target=target)
    bayes_log[iteration] = {
        "parameters": xy,
        "target": target
    }

    with open(f"./BO_logs/{timestamp}_BO_logs_{features_name}_{comment}_.json", "w") as f:
        json.dump(bayes_log, f)

    Z = get_Z(optimizer)
    b_iteration = BayesianIteration(Z, xy, iteration)
    save_illustration(b_iteration, iteration, features_name, comment, timestamp)

    return BayesianIteration(Z, xy, iteration)


def save_illustration(b_iteration, iteration, features_name, comment, timestamp):
    """
    TODO: Implement here a function that outputs a video

    TODO: Add colorbar and a point for the b_iteration.xy
    """
    fig = plt.figure()
    # im = plt.imshow(b_iteration.Z, vmin=0, vmax=1)
    im = plt.imshow(b_iteration.Z)
    plt.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
    plt.title(f"Mean Sample for {features_name}")
    fig.colorbar(im)
    plt.savefig(f"{timestamp}_mean_sample_{features_name}_{comment}_{iteration}.pdf", format="pdf")
    plt.close()

def bayesian_optimization_experiment(n, features_name, cluster_centers_path, model_path, comment="", timestamp=int(time.time())):
    basic_observer = BasicObserver()
    with open(cluster_centers_path) as f:
        cluster_centers = json.load(f)[features_name]

    def __inner_obj_function(x, y):
        return objective_function(x, y, '', features_name, model_path, comment=comment+"_BO_", timestamp=timestamp)


    optimizer = BayesianOptimization(
        f=__inner_obj_function,
        pbounds={"x": (0,1), "y": (0,1)},
    )

    # logger = JSONLogger(path=f"./BO_logs/{timestamp}_BO_logs_{features_name}_{comment}_.json")
    # optimizer.subscribe(Events.OPTMIZATION_STEP, logger)
    optimizer.subscribe(
        event=Events.OPTMIZATION_STEP,
        subscriber=basic_observer,
        callback=None, # Will use the `update` method as callback
    )

    # utility = UtilityFunction(kind="ucb", kappa=2.5, xi=0.0)

    # bayes_log = {}
    # b_iterations = []
    # for i, v in enumerate(list(cluster_centers.values())[:2]):
    #     if i + 1 > n:
    #         break
    #     xy = {"x": v[0], "y": v[1]}
    #     b_iteration = run_point(xy, optimizer, i, features_name, bayes_log, model_path, comment, timestamp)
    #     b_iterations.append(b_iteration) 

    # final_i = i
    # for i in range(final_i + 1, n):
    #     xy = optimizer.suggest(utility)
    #     b_iteration = run_point(xy, optimizer, i, features_name, bayes_log, model_path, comment, timestamp)
    #     b_iterations.append(b_iteration)

    for v in list(cluster_centers.values())[:2]:
        optimizer.probe(params={"x": v[0], "y": v[1]})
    
    optimizer.maximize(init_points=0, n_iter=n)


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
