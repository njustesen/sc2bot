from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
import math
from sc2.units import Units
from sc2.unit import Unit
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
        self.defensive_ramp = None
        self.defending_position = None

    async def run(self):
        if self.defensive_ramp is None or self.bot.iteration % 50 == 0 and self.bot.townhalls.exists:
            front_base = self.bot.townhalls.closest_to(self.bot.enemy_start_locations[0])
            distance_between_bases = front_base.distance_to(self.bot.enemy_start_locations[0])
            closest_distance_to_home = 100000
            for ramp in self.bot.game_info.map_ramps:
                distance_to_enemy = ramp.top_center.distance_to(self.bot.enemy_start_locations[0])
                distance_to_us = ramp.top_center.distance_to(front_base)
                distance_to_home = ramp.top_center.distance_to(self.bot.start_location)
                if distance_to_enemy < distance_between_bases:
                    if distance_to_home < closest_distance_to_home:
                        closest_distance_to_home = distance_to_home
                        self.defensive_ramp = ramp
                        dir_vector = ramp.bottom_center.direction_vector(ramp.top_center)
                        self.defending_position = ramp.top_center + dir_vector*4

        if len(self.actions) > 0:
            actions = [action for action in self.actions]
            self.actions = []
            await self.bot.do_actions(actions)
        else:
            if self.order == "attack":
                centroid = self.units.closest_to(self.units.center).position if self.units.amount > 0 else None
                for unit in self.units:
                    squad_size = self.units.amount + 2
                    distance = unit.distance_to(centroid)
                    # print("Squad size: ", squad_size, ", distance: ", distance)
                    if distance > squad_size/2:
                        #self.actions.append(unit.move(self.units.center))
                        if unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                            self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                        else:
                            self.actions.append(unit.move(centroid))
                    else:
                        self.unit_move(unit, self.target, self.order)
            elif self.order == "defend":
                for unit in self.units:
                    self.unit_move(unit, self.target, self.order)
            elif self.order == "harass":
                for unit in self.units:
                    self.harass_move(unit, self.target)

    def harass_move(self, unit, target):
        harassment_home = Point2((self.bot.start_location.y, self.bot.enemy_start_locations[0].x))
        harass_target = self.bot.known_enemy_structures.closest_to(harassment_home) if self.bot.known_enemy_structures.exists else self.bot.enemy_start_locations[0]

        if abs(unit.position.x - harassment_home.x) > 15:
            if unit.is_idle:
                self.actions.append(unit.move(harassment_home))
        elif unit.distance_to(target) > 25:
            if self.bot.iteration % 10 == 0:
                self.actions.append(unit.move(target))
        else:
            self.unit_move(unit, harass_target, order="harass", retreat_to=harassment_home, exclude_buildings=True)

    def unit_move(self, unit, target, order="attack", retreat_to=None, exclude_buildings=False):
        if retreat_to is None:
            retreat_to = self.bot.start_location

        if not exclude_buildings:
            closest_enemy_ground_unit = self.bot.known_enemy_units.not_flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).closest_to(
                unit) if self.bot.known_enemy_units.not_flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).exists else None
            closest_enemy_air_unit = self.bot.known_enemy_units.flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).closest_to(
                unit) if self.bot.known_enemy_units.flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).exists else None
            closest_enemy_unit = None
        else:
            closest_enemy_ground_unit = self.bot.known_enemy_units.not_structure.not_flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).closest_to(
                unit) if self.bot.known_enemy_units.not_flying.not_structure.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).exists else None
            closest_enemy_air_unit = self.bot.known_enemy_units.not_structure.flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).closest_to(
                unit) if self.bot.known_enemy_units.not_structure.flying.exclude_type(UnitTypeId.EGG).exclude_type(UnitTypeId.LARVA).exists else None
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
                self.actions.append(unit.move(self.bot.start_location))

        # Decide what to do
        centroid = self.units.not_structure.closest_to(self.units.center).position
        if order == "attack" or (closest_enemy_unit is not None and closest_enemy_unit.distance_to(unit.position) < range_own):

            # Micro for widowmines
            '''
            If we're close to the enemy, burrow down.
            '''
            if unit.type_id == UnitTypeId.WIDOWMINE:

                if not unit.is_burrowed and closest_enemy_ground_unit is not None and closest_enemy_ground_unit.distance_to(unit) < 8:
                    self.actions.append(unit(AbilityId.BURROWDOWN_WIDOWMINE))
                elif not unit.is_burrowed and self.bot.iteration % 50 == 0:
                    if isinstance(target, Unit):
                        self.actions.append(unit.move(target.position + Point2((random.randint(-3, 3), random.randint(-3, 3)))))
                    else:
                        self.actions.append(unit.move(target + Point2((random.randint(-3, 3), random.randint(-3, 3)))))

                '''
                Move a little bit away from the mines (i.e. bait)
                (I guess all units are doing this in _basic_attack)
                I don't know if we should uncomment this:
                '''
                # for unit in self.units:
                #     self.actions.append(unit.move(self.bot.start_location))
            elif unit.type_id == UnitTypeId.SIEGETANK:
                # Micro for tanks
                '''
                When we're close to the enemy, siege up
                '''
                # If the unit is too close, move back
                if closest_enemy_ground_unit is not None:
                    if range_own * 1.5 < closest_enemy_ground_unit.distance_to(unit.position) < 2.5 * range_own and not self.bot.known_enemy_units(UnitTypeId.BROODLORD).exists:  # (?)
                        self.actions.append(unit(AbilityId.SIEGEMODE_SIEGEMODE))
                    else:
                        self._basic_attack(unit, closest_enemy_ground_unit)
                else:
                    self.actions.append(unit.move(target))
            elif unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                if closest_enemy_unit is not None and closest_enemy_unit.distance_to(unit.position) < 0.3 * range_own:
                    self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                elif self.bot.known_enemy_units(UnitTypeId.BROODLORD).exists:
                    self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                    # It should move on the next iteration, since it's a siegetank again

            elif unit.type_id == UnitTypeId.LIBERATOR:
                # Micro for tanks
                '''
                When we're close to the enemy, AG MODE
                '''
                # If the unit is too close, move back
                if closest_enemy_ground_unit is not None:
                    if closest_enemy_ground_unit.distance_to(unit.position) < 10:  # (?)
                        self.actions.append(unit(AbilityId.LIBERATORMORPHTOAG_LIBERATORAGMODE))
                    elif closest_enemy_air_unit is not None:
                        self._basic_attack(unit, closest_enemy_air_unit)
                    else:
                        self.actions.append(unit.move(closest_enemy_ground_unit.position))
                else:
                    self.actions.append(unit.move(target))
            elif unit.type_id == UnitTypeId.LIBERATORAG:
                if closest_enemy_unit is not None and closest_enemy_unit.distance_to(unit.position) > 1.2 * range_own:
                    self.actions.append(unit(AbilityId.MORPH_LIBERATORAAMODE))
                elif closest_enemy_unit is not None and closest_enemy_unit.is_flying and closest_enemy_unit.distance_to(unit.position) < closest_enemy_unit.air_range:
                    self.actions.append(unit(AbilityId.MORPH_LIBERATORAAMODE))
                elif closest_enemy_unit is None:
                    self.actions.append(unit(AbilityId.MORPH_LIBERATORAAMODE))

            # Medivac micro
            # Basic attack
            elif closest_enemy_unit is not None:
                self._basic_attack(unit, closest_enemy_unit)
            else:
                self.actions.append(unit.move(target))

        elif order == "harass":
            if closest_enemy_unit is not None:
                if closest_enemy_ground_unit.ground_range >= unit.ground_range * 0.9:
                    self.actions.append(unit.move(retreat_to))
                else:
                    self._basic_attack(unit, closest_enemy_unit)
            elif self.bot.iteration % 200 == 0:
                self.actions.append(unit.move(target))

        elif order == "defend":

            # Widow mine micro
            '''
            If a widowmine is buried outside of the base and we're defending,
            then bring it back

            TODO: For now, it's burrowing in the lower part of the main ramp, find
            a way to bury it in the higher part of one of natural's ramps. This ties in
            with defining a "global" defensive spot.
            '''
            if unit.type_id == UnitTypeId.WIDOWMINE:
                if unit.is_burrowed:
                    return
                elif unit.position.distance_to(self.defending_position) < 5 and self.bot.units(UnitTypeId.WIDOWMINE).amount > 1 and self.bot.units(UnitTypeId.WIDOWMINE).closest_to(unit).distance_to(unit) > 3:
                    self.actions.append(unit(AbilityId.BURROWDOWN_WIDOWMINE))
                elif unit.position.distance_to(self.defending_position) < 3:
                    self.actions.append(unit(AbilityId.BURROWDOWN_WIDOWMINE))
                elif self.bot.iteration % 50 == 0:
                    self.actions.append(unit.move(self.defending_position + Point2((random.randint(-5, 5), random.randint(-5, 5)))))

            # Medivac micro
            elif unit.type_id == UnitTypeId.MEDIVAC:
                self.actions.append(unit.move(self.defending_position))

            # Siegetank micro
            elif unit.type_id == UnitTypeId.SIEGETANK:
                if unit.distance_to(self.defending_position) > 12:
                    self.actions.append(unit.move(self.defending_position))
                elif not self.bot.known_enemy_units(UnitTypeId.BROODLORD).exists:
                    self.actions.append(unit(AbilityId.SIEGEMODE_SIEGEMODE))
            elif unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                if unit.distance_to(self.defending_position) > 12:
                    self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                elif self.bot.known_enemy_units(UnitTypeId.BROODLORD).exists:
                    self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                # It should move, since in the next iteration it's no longer
                # SIEGETANKSIEGED but rather a SIEGETANK

            elif unit.type_id == UnitTypeId.SIEGETANK:
                if unit.distance_to(self.defending_position) < self.bot.units(UnitTypeId.SIEGETANKSIEGED).amount + 3:
                    if closest_enemy_ground_unit is not None and 7 < closest_enemy_ground_unit.distance_to(unit) < 15:
                        self.actions.append(unit(AbilityId.SIEGEMODE_SIEGEMODE))
                    elif closest_enemy_ground_unit is not None:
                        self._basic_attack(unit, closest_enemy_ground_unit)
                    elif not self.bot.known_enemy_units(UnitTypeId.BROODLORD).exists:
                        self.actions.append(unit(AbilityId.SIEGEMODE_SIEGEMODE))
                else:
                    self.actions.append(unit.move(self.defending_position))
            elif unit.type_id == UnitTypeId.SIEGETANKSIEGED:
                if closest_enemy_ground_unit is not None and closest_enemy_ground_unit.distance_to(unit) < 5:
                    self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                elif unit.distance_to(self.defending_position) > self.bot.units(UnitTypeId.SIEGETANKSIEGED).amount + 1:
                    self.actions.append(unit(AbilityId.UNSIEGE_UNSIEGE))
                elif self.bot.known_enemy_units(UnitTypeId.BROODLORD).exists:
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
                            if bunker.distance_to(self.defensive_ramp.top_center) <= unit.ground_range and bunker.cargo_used < bunker.cargo_max:
                                if unit.type_id in [UnitTypeId.MARINE, UnitTypeId.MARAUDER]:
                                    self.actions.append(bunker(AbilityId.LOAD_BUNKER, unit))

                    # Give some slack if kinda close
                    if unit.distance_to(self.defending_position) <= 15 and self.bot.iteration % 20 != 0:
                        return

                    # Otherwise hurry up
                    if unit.distance_to(self.defending_position) > 5:
                        self.actions.append(unit.move(self.defending_position))

    def _basic_attack(self, unit, closest_enemy_unit):
        _range = unit.air_range if closest_enemy_unit.is_flying else unit.ground_range
        distance = closest_enemy_unit.distance_to(unit)
        if distance < _range * 0.8 and closest_enemy_unit.distance_to(self.bot.start_location) > unit.distance_to(self.bot.start_location):
            self.actions.append(unit.move(self.bot.start_location))
        elif not unit.is_attacking:
            self.actions.append(unit.attack(closest_enemy_unit))
        else:
            if self.bot.units(UnitTypeId.MEDIVAC).amount >= 1 and distance < _range:
                if unit.type_id == UnitTypeId.MARINE and unit.health >= unit.health_max * 0.9:
                    self.actions.append(unit(AbilityId.EFFECT_STIM_MARINE))
                    # self.actions.append(unit(AbilityId.EFFECT_STIM))
                if unit.type_id == UnitTypeId.MARAUDER and unit.health >= unit.health_max * 0.9:
                    self.actions.append(unit(AbilityId.EFFECT_STIM_MARAUDER))
                    # self.actions.append(unit(AbilityId.EFFECT_STIM))
