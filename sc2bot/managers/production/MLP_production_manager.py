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
    def __init__(self, bot, worker_manager, building_manager, model_name, request_freq=22, reset_freq=22*10, features=[]):
        super().__init__(bot, worker_manager, building_manager)

        self.request_freq = request_freq
        self.reset_freq = reset_freq
        self.features = features

        self.action_dict = json.load(open("data/action_encoder_2.json"))
        self.inv_action_dict = {v: k for k, v in self.action_dict.items()}
        self.input_columns = json.load(open("data/all_columns_1552989984.json"))
        self.columns_maxes = json.load(open("data/all_columns_maxes_2.json"))

        # scalers = joblib.load("../data/scalers.json")
        print("Loading model")
        inputs = len(self.input_columns)
        hidden_nodes = 256
        hidden_layers = 3
        outputs = len(self.action_dict.keys())
        self.model = Net(inputs, hidden_nodes, hidden_layers, outputs)
        self.model.load_state_dict(torch.load(f"models/{model_name}.pt", map_location='cpu'))
        self.model.eval()
        print("Model ready")
        self.action_decoder = {v: k for k, v in self.action_dict.items()}
        self.seen_enemy_units_max = {}
        # self.game_info = bot.game_info
        self.research_abilities = {}
        self.unit_abilities = {}

        self.num_buildings = 0
        self.num_enemy_units = 0
        self.train_action = None
        self.upgrade_action = None
        self.add_on_action = None
        self.build_action = None
        self.refresh = True
        self.last_request = -1
        self.next_loop = 0

        self.locked = False
        self.main_base = None
    
    def prepare_input(self):

        state = self.bot.state

        observation = state.observation
        allied_unit_types = set([unit.name for unit in self.bot.units])
        enemy_unit_types = set([unit.name for unit in self.bot.enemy_units.values()])

        units = {
            name.upper(): len([
                unit.tag for unit in self.bot.units if unit.name == name and unit.build_progress == 1
            ]) for name in allied_unit_types
        }

        # Buildings in progress
        units_in_progress = {
            name.upper(): len([
                unit.tag for unit in self.bot.units.structure if unit.name == name and unit.build_progress < 1
            ]) for name in allied_unit_types
        }  # If this is implemented using the API, only buildings will appear.

        units_in_progress = {k: v for k, v in units_in_progress.items() if v != 0}

        highest_progress = {
            name.upper(): max([
                unit.build_progress for unit in self.bot.units.structure if unit.name.upper() == name and unit.build_progress < 1
            ], default=0) for name in units_in_progress
        }

        # Units in progress
        for building in self.bot.units.structure:
            for order in building.orders:
                if order.ability.id in self.unit_abilities:
                    unit_type = self.unit_abilities[order.ability.id]
                    progress = order.progress
                    # highest_progress
                    if unit_type not in highest_progress or progress < highest_progress[unit_type.name.upper()]:
                        highest_progress[unit_type.name.upper()] = progress
                    # units_in_progress
                    if unit_type not in units_in_progress:
                        units_in_progress[unit_type.name.upper()] = 1
                    elif progress < highest_progress[unit_type]:
                        units_in_progress[unit_type.name.upper()] += 1

        visible_enemy_units = {
            name.upper(): len([
                unit.tag for unit in self.bot.known_enemy_units | self.bot.known_enemy_structures if unit.name == name
            ]) for name in enemy_unit_types
        }

        cached_enemy_units = {
            name.upper(): len([
                unit.tag for unit in self.bot.enemy_units.values() if unit.name == name
            ]) for name in enemy_unit_types
        }

        upgrades = {
            upgrade.name.upper(): 1 for upgrade in self.bot.state.upgrades
        }

        upgrades_progress = {}

        for structure in self.bot.units.structure.ready:
            for order in structure.orders:
                if order.ability.id in self.research_abilities:
                    upgrade_type = self.research_abilities[order.ability.id]
                    upgrades_progress[upgrade_type.name.upper()] = order.progress

        if "SIEGETANKSIEGED" in units:
            if "SIEGETANK" in units:
                units["SIEGETANK"] = units["SIEGETANK"] + units["SIEGETANKSIEGED"]
            else:
                units["SIEGETANK"] = units["SIEGETANKSIEGED"]

        if "LIBERATORAG" in units:
            if "LIBERATOR" in units:
                units["LIBERATOR"] = units["LIBERATOR"] + units["LIBERATORAG"]
            else:
                units["LIBERATOR"] = units["LIBERATORAG"]

        # Name fixes
        if "SUPPLYDEPOTLOWERED" in units:
            if "SUPPLYDEPOT" in units:
                units["SUPPLYDEPOT"] = units["SUPPLYDEPOT"] + units["SUPPLYDEPOTLOWERED"]
            else:
                units["SUPPLYDEPOT"] = units["SUPPLYDEPOTLOWERED"]
            del units["SUPPLYDEPOTLOWERED"]
        if "SUPPLYDEPOTLOWERED" in units_in_progress:
            del units_in_progress["SUPPLYDEPOTLOWERED"]
        if "SUPPLYDEPOTLOWERED" in highest_progress:
            del highest_progress["SUPPLYDEPOTLOWERED"]

        print("--- OBSERVATION ---")
        print("Frame: ", observation.game_loop)
        print("Minerals: ", observation.player_common.minerals)
        print("Vespene: ", observation.player_common.vespene)
        print("Supply used: ", observation.player_common.food_used)
        print("Supply total: ", observation.player_common.food_cap)
        print("Units: ", units)
        print("Units in progress: ", units_in_progress)
        print("Highest progress: ", highest_progress)
        print("Visible enemy units: ", visible_enemy_units)
        print("Cached enemy units: ", cached_enemy_units)
        print("upgrades: ", upgrades)
        print("upgrades_progress: ", upgrades_progress)
        print("-------------------")

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
                name = column.split("_")[-1].upper()
                if name in units_in_progress:
                    row.append(units_in_progress[name])
                else:
                    row.append(0)
            elif "visible_enemy_units" in column:
                name = column.split("_")[-1].upper()
                if name in visible_enemy_units:
                    row.append(visible_enemy_units[name])
                else:
                    row.append(0)
            elif "seen_enemy_units" in column:
                name = column.split("_")[-1].upper()
                if name in cached_enemy_units:
                    row.append(cached_enemy_units[name])
                else:
                    row.append(0)
            elif "highest_progress" in column:
                name = column.split("_")[-1].upper()
                if name in highest_progress:
                    row.append(highest_progress[name])
                else:
                    row.append(0)
            elif "units" in column:
                name = column.split("_")[-1].upper()
                if name in units:
                    row.append(units[name])
                else:
                    row.append(0)
            elif "upgrade_progress" in column:
                name = column.split("_")[-1].upper()
                if name in upgrades_progress:
                    row.append(upgrades_progress[name])
                else:
                    row.append(0)
            elif "upgrades" in column:
                name = column.split("_")[-1].upper()
                if name in upgrades:
                    row.append(upgrades[name])
                else:
                    row.append(0)
            else:
                raise Exception(f"Unknown input: {column}")

        normalized = [row[i] / self.columns_maxes[self.input_columns[i]] for i in range(len(self.input_columns))]
        print("Normalized:", normalized)
        print("-------------------")

        if len(self.features) > 0:
            for feature in self.features:
                normalized.append(feature)

        return normalized

    def _has_planned_action(self):
        return self.train_action or self.add_on_action or self.upgrade_action or self.build_action

    async def _execute_planned_action(self):
        if self.train_action is not None:  # If train action is planned
            if not self.building_manager.is_legal_training_action(self.train_action):
                self.train_action = None
                return
            if self.bot.can_afford(self.train_action) and self.building_manager.can_train(self.train_action):
                print(f"ProductionManager: can now train {self.train_action}.")
                self.locked = True
                await self.building_manager.train(self.train_action)
                self.train_action = None
                self.locked = False
        elif self.upgrade_action is not None:  # If upgrade action is planned
            if not self.building_manager.is_legal_upgrade_action(self.upgrade_action):
                self.upgrade_action = None
                return
            if self.bot.can_afford(self.upgrade_action) and self.building_manager.can_upgrade(self.upgrade_action):
                print(f"ProductionManager: can now upgrade {self.upgrade_action}.")
                self.locked = True
                await self.building_manager.upgrade(self.upgrade_action)
                self.upgrade_action = None
                self.locked = False
        elif self.add_on_action is not None:  # If add on action is planned
            if not self.building_manager.is_legal_build_action(self.add_on_action):
                self.add_on_action = None
                return
            if self.bot.can_afford(self.add_on_action) and self.building_manager.can_add_on(self.add_on_action):
                print(f"ProductionManager: can now build {self.add_on_action}.")
                self.locked = True
                await self.building_manager.add_on(self.add_on_action)
                self.add_on_action = None
                self.locked = False
        elif self.build_action is not None:  # If add on action is planned
            if not self.building_manager.is_legal_build_action(self.build_action):
                self.build_action = None
                return
            if not self.worker_manager.has_unstarted_plan():
                self.locked = True
                print(f"ProductionManager: can now build {self.build_action}.")
                await self.worker_manager.build(self.build_action)
                self.locked = False

    def _clear_plans(self):
        self.train_action = None
        self.upgrade_action = None
        self.add_on_action = None
        self.build_action = None

    async def run(self):

        # Initialize in the first frame
        if len(self.research_abilities) == 0:
            self._init_abilites()
            self.main_base = self.bot.units(UnitTypeId.COMMANDCENTER)[0]

        # Rebuild main base if we lost it
        if self.main_base is None:
            await self.worker_manager.build(UnitTypeId.COMMANDCENTER, self.bot.start_location)
            return

        # Are we supply blocked?
        required = self.bot.game_data().units[self.train_action.value]._proto.food_required if self.train_action is not None else 0
        supply_blocked = self.bot.supply_left - required < 0

        # If supply blocked and planning to train - clear
        if supply_blocked and self.train_action and not (self.worker_manager.is_building(UnitTypeId.SUPPLYDEPOT) or self.worker_manager.is_building(UnitTypeId.COMMANDCENTER)):
            print("Supply blocked - resetting")
            self.refresh = True

        # If stuck for 10 seconds - clear
        # if self.last_request + self.reset_freq < self.bot.state.observation.game_loop:
        #     self.refresh = True

        # Clear plans if we should refresh
        if self.refresh:
            self._clear_plans()

        # Execute planned actions
        #if self.locked:
        #    # print("Locked")
        if self._has_planned_action():
            # print("Has plan")
            await self._execute_planned_action()
        else:
            print("Requesting")
            #self.locked = True
            # Only request model every 22 frames
            # if self.bot.state.observation.game_loop >= self.next_loop:
            self.refresh = False
            # self.last_request = self.bot.state.observation.game_loop
            # self.next_loop += self.request_freq

            # Request model
            await self._request_model()
            #self.request_locked = False

    async def _request_model(self):
        x = self.prepare_input()
        x = np.array([x])
        x = torch.from_numpy(x).float()
        out = self.model(x)
        out = out.detach().numpy()
        out = np.exp(out)
        print("--- Output ---")
        #print(out)
        out = out[0]
        top_idx = list(reversed(np.argsort(out)[-3:]))
        top_values = [out[i] for i in top_idx]
        top_predictions = [(self.inv_action_dict[top_idx[i]], top_values[i]) for i in range(len(top_idx))]
        print(top_predictions)
        # TODO: Filter out unavailable and unwanted actions
        action_idx = np.random.choice(list(range(len(self.action_dict))), 1, p=out)
        action_name = self.inv_action_dict[action_idx[0]]
        action_type = action_name.split("_")[0]
        build_name = action_name.split("_")[1]
        print(build_name)

        if action_type == "train":
            print(f"ProductionManager: train {build_name}.")
            unit_type = UnitTypeId[build_name.upper()]
            if not self.building_manager.is_legal_training_action(unit_type):
                self.refresh = True
                print("Illegal action:", unit_type)
                return
            if unit_type is None:
                print(f"Unknown unit type {unit_type}")
            if self.bot.can_afford(unit_type) and self.building_manager.can_train(unit_type):
                self.refresh = True
                # print(f"ProductionManager: train {build_name}.")
                await self.building_manager.train(unit_type)
            else:
                print(f"ProductionManager: cannot train {build_name}.")
                self.train_action = unit_type
        elif action_type == "build":
            print(f"ProductionManager: build {build_name}.")
            unit_type = UnitTypeId[build_name.upper()]
            if not self.building_manager.is_legal_build_action(unit_type):
                self.refresh = True
                print("Illegal action:", unit_type)
                return
            if self.worker_manager.has_unstarted_plan():
                self.build_action = unit_type
            else:
                print(f"ProductionManager: cannot build {build_name} - building something else.")
                await self.worker_manager.build(unit_type)
        elif action_type == "research":
            print(f"ProductionManager: research {build_name}.")
            upgrade_type = UpgradeId[build_name.upper()]
            await self.building_manager.research(upgrade_type)
        elif action_type == "upgrade":
            print(f"ProductionManager: upgrade {build_name}.")
            upgrade_type = UnitTypeId[build_name.upper()]
            if not self.building_manager.is_legal_upgrade_action(upgrade_type):
                self.refresh = True
                print("Illegal action:", upgrade_type)
                return
            if self.building_manager.can_upgrade(upgrade_type):
                # print(f"ProductionManager: upgrade {upgrade_type}.")
                await self.building_manager.upgrade(upgrade_type)
            else:
                print(f"ProductionManager: cannot upgrade {upgrade_type}.")
                self.upgrade_action = upgrade_type
        elif action_type == "addon":
            print(f"ProductionManager: add on {build_name}.")
            unit_type = UnitTypeId[build_name.upper()]
            if not self.building_manager.is_legal_build_action(unit_type):
                self.refresh = True
                print("Illegal action:", unit_type)
                return
            if self.bot.can_afford(unit_type) and self.building_manager.can_add_on(unit_type):
                self.refresh = True
                # print(f"ProductionManager: build {build_name}.")
                await self.building_manager.add_on(unit_type)
            else:
                print(f"ProductionManager: cannot build {build_name}.")
                self.add_on_action = unit_type
        elif action_type == "calldown":
            print("ProductionManager: calldown mule.")
            await self.building_manager.calldown_mule()
        else:
            print("Unknown action: ", action_type)

        # print(f"Bot's known enemy units: {self.bot.known_enemy_units | self.bot.known_enemy_structures}")

    def _init_abilites(self):
        print("Initializing abilities")
        for upgrade_type in UpgradeId:
            ability = self.bot.game_data().upgrades[upgrade_type.value].research_ability
            if ability is None:
                continue
            self.research_abilities[ability.id] = upgrade_type
        for unit_type in UnitTypeId:
            if unit_type.value in self.bot.game_data().units:
                ability = self.bot.game_data().units[unit_type.value].creation_ability
                if ability is None:
                    continue
                self.unit_abilities[ability.id] = unit_type

    async def on_building_construction_started(self, unit):
        if self.build_action is not None and self.build_action == unit.type_id:
            self.build_action = None
        if unit.type_id == UnitTypeId.COMMANDCENTER and unit.position.distance_to(self.bot.start_location) < 2:
            self.main_base = unit

    async def on_unit_destroyed(self, unit_tag):
        if self.main_base is not None and unit_tag == self.main_base.tag:
            self.main_base = None
