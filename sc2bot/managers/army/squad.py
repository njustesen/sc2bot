from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
import math
from sc2.units import Units


class Squad:

    def __init__(self, bot, target, unit_types, order):
        self.bot = bot
        self.target = target
        self.order = order
        self.unit_types = unit_types
        self.units = None
        self.actions = []

    async def run(self):
        if len(self.actions) > 0:
            actions = [action for action in self.actions]
            self.actions = []
            await self.bot.do_actions(actions)
        else:
            if self.order == "attack":
                for unit in self.units:
                    squad_size = self.units.amount + 2
                    distance = unit.distance_to(self.units.center)
                    # print("Squad size: ", squad_size, ", distance: ", distance)
                    if distance > squad_size:
                        self.actions.append(unit.move(self.units.center))
                    else:
                        self.unit_move(unit, self.target, self.order)
            elif self.order == "defend":
                for unit in self.units:
                    self.unit_move(unit, self.target, self.order)

    def unit_move(self, unit, target, type="attack"):
        closest_enemy_ground_unit = self.bot.known_enemy_units.not_flying.closest_to(
            unit) if self.bot.known_enemy_units.not_flying.exists else None
        closest_enemy_air_unit = self.bot.known_enemy_units.flying.closest_to(
            unit) if self.bot.known_enemy_units.flying.exists else None
        closest_enemy_unit = None

        # Find closest enemy unit that the unit can attack
        if closest_enemy_ground_unit is not None and unit.can_attack_ground:
            closest_enemy_unit = closest_enemy_ground_unit
        if closest_enemy_air_unit is not None and unit.can_attack_air:
            if closest_enemy_unit is None or closest_enemy_air_unit.distance_to(unit.position) < closest_enemy_unit.distance_to(unit.position):
                closest_enemy_unit = closest_enemy_air_unit

        range_own = 0
        if closest_enemy_unit is not None:
            range_own = unit.ground_range if not closest_enemy_unit.is_flying else unit.air_range

        # TODO: Is the closest enemy closer to our base than us -> then get mad?

        # Decide what to do
        if closest_enemy_unit is not None:
            if type == "attack" or closest_enemy_unit.distance_to(unit.position) < range_own:

                # Basic attack
                self._basic_attack(unit, closest_enemy_unit)

            else:

                if self.bot.iteration % 20 == 0:

                    # Go into bunker
                    bunkers = self.bot.units(UnitTypeId.BUNKER).ready
                    if bunkers.exists:
                        for bunker in bunkers:
                            if bunker.cargo_used < bunker.cargo_max:
                                self.actions.append(bunker(AbilityId.LOAD_BUNKER, unit))
                                # self.actions.append(unit.move(bunker))
                                return

                # Give some slack if kinda close
                if unit.distance_to(target) <= 15 and self.bot.iteration % 20 != 0:
                    return

                # Otherwise hurry up
                if unit.distance_to(target) > 5:
                    self.actions.append(unit.move(target))

    def _basic_attack(self, unit, closest_enemy_unit):
        range = unit.air_range if closest_enemy_unit.is_flying else unit.ground_range
        distance = closest_enemy_unit.distance_to(unit)
        # print("Range=", range)
        # print("Distance=", distance)
        if distance < range * 0.8:
            self.actions.append(unit.move(self.bot.start_location))
        else:
            if not unit.is_attacking:
                self.actions.append(unit.attack(closest_enemy_unit))
