from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
import math
from sc2.units import Units
from sc2.position import Point2, Point3
import random


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
                centroid = self.units.closest_to(self.units.center).position
                for unit in self.units:
                    squad_size = self.units.amount + 2
                    distance = unit.distance_to(centroid)
                    # print("Squad size: ", squad_size, ", distance: ", distance)
                    if distance > squad_size/2:
                        #self.actions.append(unit.move(self.units.center))
                        self.actions.append(unit.move(centroid))
                    else:
                        self.unit_move(unit, self.target, self.order)
            elif self.order == "defend":
                for unit in self.units:
                    self.unit_move(unit, self.target, self.order)

    def unit_move(self, unit, target, order="attack"):
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
        # TODO: Define a more general defensive position, maybe even a list of them

        # Micro for medivacs
        '''
        If we have bio, move to the centroid of the squad; else, move away
        '''
        if unit.type_id == UnitTypeId.MEDIVAC:
            if self.bot.units(UnitTypeId.MARINE) or self.bot.units(UnitTypeId.MARAUDER):
                centroid = self.units.closest_to(self.units.center).position
                self.actions.append(unit.move(centroid))
            else:
                # Moving to base if we don't have bio
                self.actions.append(unit.move(self.main_base_ramp.higher()))

        # Decide what to do
        if closest_enemy_unit is not None:
            if order == "attack" or closest_enemy_unit.distance_to(unit.position) < range_own:

                # Micro for widowmines
                '''
                If we're close to the enemy, burrow down.
                '''
                if unit.type_id == UnitTypeId.WIDOWMINE:
                    self.actions.append(unit(AbilityId.BURROWDOWN_WIDOWMINE))
                    '''
                    Move a little bit away from the mines (i.e. bait)
                    (I guess all units are doing this in _basic_attack)
                    I don't know if we should uncomment this:
                    '''
                    # for unit in self.units:
                    #     self.actions.append(unit.move(self.bot.start_location))
                # Micro for tanks
                '''
                When we're close to the enemy, siege up
                '''
                elif unit.type_id == UnitTypeId.SIEGETANK:
                    # If the unit is too close, move back
                    if closest_enemy_unit.distance_to(unit.position) < 0.2 * range_own: # (?)
                        self.actions.append(unit.move(self.main_base_ramp.higher()))
                    else:
                        self.actions.append(unit(AbilityId.SIEGEMODE_SIEGEMODE))
                elif unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                    if closest_enemy_unit.distance_to(unit.position) < 0.2 * range_own:
                        self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                        # It should move on the next iteration, since it's a siegetank again
                # Basic attack
                else:
                    self._basic_attack(unit, closest_enemy_unit)

            else:
                defending_position = random.choice(self.bot.main_base_ramp.lower())

                # Widow mine micro
                '''
                If a widowmine is buried outside of the base and we're defending,
                then bring it back

                TODO: For now, it's burrowing in the lower part of the main ramp, find
                a way to bury it in the higher part of one of natural's ramps. This ties in
                with defining a "global" defensive spot.
                '''
                if unit.type_id == UnitTypeId.WIDOWMINE:
                    if unit.position not in self.bot.main_base_ramp.lower():
                        if unit.is_burrowed():
                            self.actions.append(unit(AbilityId.BURROWUP_WIDOWMINE))

                        self.actions.append(unit.move(defending_position))
                    
                    if unit.position == defending_position and not unit.is_burrowed():
                        self.actions.append(unit(AbilityId.BURROWDOWN_WIDOWMINE))
                # Medivac micro
                elif unit.type_id == UnitTypeId.MEDIVAC:
                    self.actions.append(unit.move(defending_position))
                # Siegetank micro
                elif unit.type_id == UnitTypeId.SIEGETANK:
                    if unit.distance_to(self.bot.main_base_ramp.lower()) > 10:
                        self.actions.append(unit.move(defending_position))
                    else:
                        self.actions.append(unit(AbilityId.SIEGEMODE_SIEGEMODE))
                elif unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                    if unit.distance_to(self.bot.main_base_ramp.lower()) > 10:
                        self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                    # It should move, since in the next iteration it's no longer
                    # SIEGETANKSIEGED but rather a SIEGETANK
                # basic attack for other units
                else:
                    if random.randint(0, len(self.units)) == 0:
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
        _range = unit.air_range if closest_enemy_unit.is_flying else unit.ground_range
        distance = closest_enemy_unit.distance_to(unit)
        # print("Range=", range)
        # print("Distance=", distance)
        if distance < _range * 0.8 and closest_enemy_unit.distance_to(self.bot.start_location) > unit.distance_to(self.bot.start_location):
            #direction_away = closest_enemy_unit.position.direction_vector(unit.position)
            #length = direction_away.distance2_to(Point2((0, 0)))
            #unit_vector = Point2((direction_away.x / length, direction_away.y / length))
            #self.actions.append(unit.move(self.bot.start_location))
            #position = unit.position + unit_vector * (range*0.1)
            self.actions.append(unit.move(self.bot.start_location))
        else:
            if not unit.is_attacking:
                self.actions.append(unit.attack(closest_enemy_unit))
