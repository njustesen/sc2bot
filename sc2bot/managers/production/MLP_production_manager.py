import random
from sc2bot.managers.interfaces import ProductionManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
import torch
import json
import numpy as np
from sc2bot.managers.production.mlp_model import Net
from sklearn.externals import joblib
import glob


class MLPProductionManager(ProductionManager):
    '''
    This production manager transforms the observation that the bot
    is getting into the input for the model. It accepts also a pair of
    features.
    '''
    def __init__(self, bot, worker_manager, building_manager, model_name):
        super().__init__(bot, worker_manager, building_manager)
        self.action_dict = json.load(open("data/action_encoder.json"))
        self.inv_action_dict = {v: k for k, v in self.action_dict.items()}
        self.input_columns = json.load(open("data/columns_for_input.json"))
        self.columns_maxes = json.load(open("data/all_columns_maxes.json"))

        # scalers = joblib.load("../data/scalers.json")

        inputs = len(self.input_columns)
        hidden_nodes = 128
        hidden_layers = 3
        outputs = len(self.action_dict.keys())
        self.model = Net(inputs, hidden_nodes, hidden_layers, outputs)
        self.model.load_state_dict(torch.load(f"models/{model_name}.pt"))
        self.model.eval()
        self.action_decoder = {v: k for k, v in self.action_dict.items()}
        self.seen_enemy_units_max = {}
        # self.game_info = bot.game_info
        self.research_abilities = {}
    
    def prepare_input(self):

        state = self.bot.state

        observation = state.observation
        allied_unit_types = set([unit.name for unit in self.bot.units])
        enemy_unit_types = set([unit.name for unit in self.bot.enemy_units.values()])

        units = {
            name: len([
                unit.tag for unit in self.bot.units if unit.name == name and unit.build_progress == 1
            ]) for name in allied_unit_types
        }

        units_in_progress = {
            name: len([
                unit.tag for unit in self.bot.units if unit.name == name and unit.build_progress < 1
            ]) for name in allied_unit_types
        }  # If this is implemented using the API, only buildings will appear.

        highest_progress = {
            name: max([
                unit.build_progress for unit in self.bot.units if unit.name == name and unit.build_progress < 1
            ], default=0) for name in units_in_progress
        }

        visible_enemy_units = {
            name: len([
                unit.tag for unit in self.bot.known_enemy_units | self.bot.known_enemy_structures if unit.name == name
            ]) for name in enemy_unit_types
        }

        cached_enemy_units = {
            name: len([
                unit.tag for unit in self.bot.enemy_units.values() if unit.name == name
            ]) for name in enemy_unit_types
        }

        upgrades = {
            upgrade.name: 1 for upgrade in self.bot.state.upgrades
        }

        upgrades_progress = {}

        for structure in self.bot.units.structure.ready:
            for order in structure.orders:
                if order.ability.id in self.research_abilities:
                    upgrade_type = self.research_abilities[order.ability.id]
                    # if "LEVEL" in upgrade_type.name:
                    #    level = upgrade_type.name[-1]
                    #if order.ability.button_name[-1] != level:
                    #    upgrades_progress[upgrade_type.name] = 0
                    #else:
                    upgrades_progress[upgrade_type.name] = order.progress

        row = []
        for column in self.input_columns:
            if column == "frame_id":
                row.append(observation.game_loop)
            elif column == "resources_minerals":
                row.append(observation.player_common.minerals)
            elif column == "resources_vespene":
                row.append(observation.player_common.vespene)
            elif column == "supply_used":
                row.append(observation.player_common.food_used)
            elif column == "supply_total":
                row.append(observation.player_common.food_cap)
            elif column == "supply_army":
                row.append(observation.player_common.food_army)
            elif column == "supply_workers":
                row.append(observation.player_common.food_workers)
            elif "units_in_progress_" in column:
                name = column.split("_")[-1]
                if name in units_in_progress:
                    row.append(units_in_progress[name])
                else:
                    row.append(0)
            elif "visible_enemy_units" in column:
                name = column.split("_")[-1]
                if name in visible_enemy_units:
                    row.append(visible_enemy_units[name])
                else:
                    row.append(0)
            elif "seen_enemy_units" in column:
                name = column.split("_")[-1]
                if name in cached_enemy_units:
                    row.append(cached_enemy_units[name])
                else:
                    row.append(0)
            elif "highest_progress" in column:
                name = column.split("_")[-1]
                if name in highest_progress:
                    row.append(highest_progress[name])
                else:
                    row.append(0)
            elif "units" in column:
                name = column.split("_")[-1]
                if name in units:
                    row.append(units[name])
                else:
                    row.append(0)
            elif "upgrade_progress" in column:
                name = column.split("_")[-1]
                if name in upgrades_progress:
                    row.append(upgrades_progress[name])
                else:
                    row.append(0)
            elif "upgrades" in column:
                name = column.split("_")[-1]
                if name in upgrades:
                    row.append(upgrades[name])
                else:
                    row.append(0)
            else:
                raise Exception(f"Unknown input: {column}")

        normalized = [row[i] / self.columns_maxes[self.input_columns[i]] for i in range(len(self.input_columns))]
        print(normalized)

        return normalized

    async def run(self):

        if len(self.research_abilities):
            print("Initializing abilities")
            for upgrade_type in UpgradeId:
                ability = self.bot.game_data().upgrades[upgrade_type.value].research_ability
                if ability is None:
                    continue
                self.research_abilities[ability.id] = upgrade_type

        x = self.prepare_input()
        x = np.array([x])
        x = torch.from_numpy(x).float()
        out = self.model(x)
        out = out.detach().numpy()
        out = np.exp(out)
        # TODO: Filter out unavailable and unwanted actions
        action_idx = np.random.choice(list(range(len(self.action_dict))), 1, p=out[0])
        action_name = self.inv_action_dict[action_idx[0]]
        action_type = action_name.split("_")[0]
        build_name = action_name.split("_")[1]

        if action_type == "train":
            print(f"ProductionManager: train {build_name}.")
            unit_type = UnitTypeId[build_name.upper()]
            await self.building_manager.train(unit_type)
        elif action_type == "build":
            print(f"ProductionManager: build {build_name}.")
            unit_type = UnitTypeId[build_name.upper()]
            await self.worker_manager.build(unit_type)
        elif action_type == "research":
            print("ProductionManager: research {build_name}.")
            upgrade_type = UpgradeId[build_name.upper()]
            await self.building_manager.research(upgrade_type)
        elif action_type == "upgrade":
            print("ProductionManager: upgrade {build_name}.")
            upgrade_type = UnitTypeId[build_name.upper()]
            await self.building_manager.upgrade(upgrade_type)
        elif action_type == "addon":
            print("ProductionManager: upgrade {build_name}.")
            unit_type = UnitTypeId[build_name.upper()]
            await self.building_manager.add_on(unit_type)
        elif action_type == "calldown":
            print("ProductionManager: calleown mule.")
            await self.building_manager.calldown_mule()
        else:
            print("Unknown action: ", action_type)

        # print(f"Bot's known enemy units: {self.bot.known_enemy_units | self.bot.known_enemy_structures}")
