from sc2bot.managers.interfaces import ArmyManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class Order():

    def __init__(self, location, type="attack"):
        self.location = location
        self.type = type


class AdvancedArmyManager(ArmyManager):

    def __init__(self, bot):
        super().__init__(bot)
        self.orders = {}
        self.n = 0

    async def run(self):
        if self.n % 2 == 0:
            for unit_type, order in self.orders.items():
                if unit_type is None:
                    for unit in self.bot.units:
                        if unit.type_id != UnitTypeId.SCV:
                            await self.unit_move(unit, order.location, order.type)
                else:
                    for unit in self.bot.units:
                        if unit.type_id == unit_type:
                            if unit.weapon_cooldown > 0:
                                await self.unit_move(unit, order.location, order.type)
        self.n += 1

    async def unit_move(self, unit, location, type="attack"):
        closest_enemy_ground_unit = self.bot.known_enemy_units.not_flying.closest_to(unit) if self.bot.known_enemy_units.not_flying.exists else None
        closest_enemy_air_unit = self.bot.known_enemy_units.flying.closest_to(unit) if self.bot.known_enemy_units.flying.exists else None
        closest_enemy_unit = None

        # Find closest enemy unit that the unit can attack
        if closest_enemy_ground_unit is not None and unit.can_attack_ground:
            closest_enemy_unit = closest_enemy_ground_unit
        if closest_enemy_air_unit is not None and unit.can_attack_air:
            if closest_enemy_unit is None or closest_enemy_unit.distance_to(unit.position) < closest_enemy_air_unit.distance_to(unit.position):
                closest_enemy_unit = closest_enemy_air_unit

        # Decide what to do
        if closest_enemy_unit is not None:
            if type == "attack" or closest_enemy_unit.distance_to(unit.position) < max(unit.ground_range, unit.air_range):
                if unit.type_id == UnitTypeId.MARINE:
                    await self.marine_attack(unit, closest_enemy_unit)
            else:
                await self.bot.do(unit.move(location))

    async def marine_attack(self, unit, closest_enemy_unit):
        range = unit.air_range if closest_enemy_unit.is_flying else unit.ground_range
        distance = closest_enemy_unit.distance_to(unit)
        print("Range=", range)
        print("Distance=", distance)
        if distance < range * 0.8 and unit.weapon_cooldown == 0:
            await self.bot.do(unit.move(self.bot.start_location))
        else:
            await self.bot.do(unit.attack(closest_enemy_unit))

    async def attack(self, location, unit_types=None):
        order = Order(location, "attack")
        if unit_types is None:
            self.orders.clear()
            self.orders[None] = order
        else:
            for unit_type in unit_types:
                self.orders[unit_type] = order

    async def defend(self, location, unit_types=None):
        order = Order(location, "defend")
        if unit_types is None:
            self.orders.clear()
            self.orders[None] = order
        else:
            for unit_type in unit_types:
                self.orders[unit_type] = order
