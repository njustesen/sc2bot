from sc2.ids.unit_typeid import UnitTypeId
import math

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

        # Is the closest enemy closer to our base than us -> then get mad?
        '''
        if closest_enemy_unit is not None:
            for building in self.units.structure:
                r_own = unit.ground_range if not closest_enemy_unit.is_flying else unit.air_range
                r_opp = closest_enemy_unit.ground_range if closest_enemy_unit.can_attack_ground else unit.air_range
                r = max(r_own, r_opp)
                if unit.distance_to(building) > closest_enemy_unit.distance_to(building) or closest_enemy_unit.distance_to(building) < r:
                    type = "attack"
                    target = closest_enemy_unit
                    break
        '''
        # Decide what to do
        if closest_enemy_unit is not None:
            if type == "attack" or closest_enemy_unit.distance_to(unit.position) < max(unit.ground_range,
                                                                                       unit.air_range):
                self._basic_attack(unit, closest_enemy_unit)
            else:
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
