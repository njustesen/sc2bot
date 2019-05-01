
"""
A modular StarCraft II bot.
"""

import seaborn as sns
import random
import time
import math
import sc2
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer
from sc2bot.managers.army.simple_army_manager import SimpleArmyManager
from sc2bot.managers.army.advanced_army_manager import AdvancedArmyManager
from sc2bot.managers.building.simple_building_manager import SimpleBuildingManager
from sc2bot.managers.production.marine_production_manager import MarineProductionManager
from sc2bot.managers.production.reaper_marine_production_manager import ReaperMarineProductionManager
from sc2bot.managers.production.orbital_production_manager import OrbitalProductionManager
from sc2bot.managers.production.mlp_production_manager import MLPProductionManager
from sc2bot.managers.production.mlp_model import Net
from sc2bot.managers.scouting.simple_scouting_manager import SimpleScoutingManager
from sc2bot.managers.assault.simple_assault_manager import SimpleAssaultManager
from sc2bot.managers.assault.value_based_assault_manager import ValueBasedAssaultManager
from sc2bot.managers.worker.simple_worker_manager import SimpleWorkerManager
from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction
import numpy as np
import pickle

import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib import cm
from matplotlib import mlab


class TerranBot(sc2.BotAI):

    def __init__(self, features, verbose=True):
        super().__init__()
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


def run_game(features):

    #return np.mean(features) - random.random()*0.1
    replay_name = f"replays/sc2bot_{int(time.time())}.sc2replay"
    # Multiple difficulties for enemy bots available https://github.com/Blizzard/s2client-api/blob/ce2b3c5ac5d0c85ede96cef38ee7ee55714eeb2f/include/sc2api/sc2_gametypes.h#L30
    try:
        result = sc2.run_game(sc2.maps.get("(2)CatalystLE"),
                                players=[Bot(Race.Terran, TerranBot(features=features, verbose=True)), Computer(Race.Zerg, Difficulty.Medium)],
                                save_replay_as=replay_name,
                                realtime=False)
        return 0 if result.name == "Defeat" else (1 if result.name == "Victory" else 0.5)
    except Exception as e:
        print(e)
        return 0


def unique_rows(a):
    """
    A functions to trim repeated rows that may appear when optimizing.
    This is necessary to avoid the sklearn GP object from breaking

    :param a: array to trim repeated rows from

    :return: mask of unique rows
    """

    # Sort array and kep track of where things should go back to
    order = np.lexsort(a.T)
    reorder = np.argsort(order)

    a = a[order]
    diff = np.diff(a, axis=0)
    ui = np.ones(len(a), 'bool')
    ui[1:] = (diff != 0).any(axis=1)

    return ui[reorder]


n = 1e5
x = y = np.linspace(0, 6, 300)
X, Y = np.meshgrid(x, y)
x = X.ravel()
y = Y.ravel()
X = np.vstack([x, y]).T[:, [1, 0]]
#z = target(x, y)

fig, axis = plt.subplots(1, 1, figsize=(14, 10))
gridsize=150

#im = axis.hexbin(x, y, C=z, gridsize=gridsize, cmap=cm.jet, bins=None, vmin=-0.9, vmax=2.1)
#axis.axis([x.min(), x.max(), y.min(), y.max()])

#cb = fig.colorbar(im, )
#cb.set_label('Value')


def posterior(bo, X):
    ur = unique_rows(bo.X)
    bo.gp.fit(bo.X[ur], bo.Y[ur])
    mu, sigma2 = bo.gp.predict(X, eval_MSE=True)
    return mu, np.sqrt(sigma2), bo.util.utility(X, bo.gp, bo.Y.max())


def plot_grid(grid, iteration, std=False):
    # plt.style.use('ggplot')

    # brewer2mpl.get_map args: set name  set type  number of colors
    # bmap = brewer2mpl.get_map('Set2', 'qualitative', 7)

    # cmap = 'plasma'
    # cmap = 'inferno'
    # cmap = 'magma'
    # cmap = 'viridis'

    ax = sns.heatmap(grid, rasterized=True, linewidth=0, vmin=0, vmax=1)
    fig = ax.get_figure()
    #ax.axes.set_xlabel(grid.feature_b.title, fontsize=14)
    #ax.axes.set_ylabel(grid.feature_a.title, fontsize=14)
    ax.axes.set_xticklabels(np.arange(0, len(grid[0]), len(grid[0])))
    ax.axes.set_yticklabels(np.arange(0, len(grid), len(grid)))
    fig.show()
    fig.savefig(f'bayes/bayesian_map_{iteration}{"_std" if std else ""}.pdf')


def optimize(n=100):

    '''
    optimizer = BayesianOptimization(
        f=None,
        pbounds={'x': (0, 1), 'y': (0, 1)},
        verbose=2,
        random_state=1,
    )
    '''
    j = 10
    optimizer = pickle.load(open(f"bayes/optimizer_{j}.p", "rb"))
    j += 1
    utility = UtilityFunction(kind="ucb", kappa=2.5, xi=0.0)

    points = []
    for i in range(n):
        next_point = optimizer.suggest(utility)
        #plot_2d(optimizer, i)
        print(next_point)
        target = run_game([next_point['x'], next_point['y']])
        optimizer.register(params=next_point, target=target)
        print(target, next_point)
        points.append((next_point, target))

        pickle.dump(optimizer, open(f"bayes/optimizer_{i+j}.p", "wb"))
        pickle.dump(points, open(f"bayes/points_{i+j}.p", "wb"))
        #optimizer = pickle.load(open(f"bayes/optimizer_{i+1}.p", "wb"))

        # Grid
        size = 100
        grid = []
        for y in range(100):
            grid.append([])
            for x in range(100):
                pred_mean, pred_std = optimizer._gp.predict([[x/size, y/size]], return_std=True)
                grid[y].append(pred_mean[0])

        plot_grid(grid, i+j)
        print(optimizer.max)

    '''
    optimizer = BayesianOptimization(run_game, {'x': (0, 1), 'y': (0, 1)})
    gp_params = {'corr': 'absolute_exponential', 'nugget': 1e-9}
    optimizer.maximize(init_points=5, n_iter=0, acq='ucb', kappa=10, **gp_params)
    plot_2d("{:03}".format(len(bo.X)))

    # Turn interactive plotting off
    plt.ioff()

    for i in range(10):
        bo.maximize(init_points=0, n_iter=1, acq='ucb', kappa=10, **gp_params)
        plot_2d("{:03}".format(len(bo.X)), iteration=i)
    '''

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

    result = run_game(features_10)
    #print(result)
    #optimize(100)

    '''
    for i in range(1, 100):
        optimizer = pickle.load(open(f"bayes/optimizer_{i}.p", "rb"))

        # Grid
        size = 100
        grid_std = []
        grid = []
        for y in range(size):
            grid.append([])
            grid_std.append([])
            for x in range(size):
                pred_mean, pred_std = optimizer._gp.predict([[x / size, y / size]], return_std=True)
                grid[y].append(pred_mean[0])
                grid_std[y].append(pred_std[0])

        plot_grid(grid, i)
        plot_grid(grid_std, i, std=True)
        print(optimizer.max)
    '''

if __name__ == '__main__':
    main()
