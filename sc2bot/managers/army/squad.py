from sc2.ids.unit_typeid import UnitTypeId


class Squad:

    def __init__(self, bot, target, unit_types, order):
        self.bot = bot
        self.target = target
        self.order = order
        self.unit_types = unit_types
        self.units = None

    async def run(self):
        if self.bot.iteration % 5 == 0:
            if self.order == "attack":
                for unit in self.units:
                    squad_size = self.units.amount + 2
                    distance = unit.distance_to(self.units.center)
                    # print("Squad size: ", squad_size, ", distance: ", distance)
                    if distance > squad_size:
                        await self.bot.do(unit.move(self.units.center))
                    else:
                        await self.unit_move(unit, self.target, self.order)
            elif self.order == "defend":
                for unit in self.units:
                    await self.unit_move(unit, self.target, self.order)

    async def unit_move(self, unit, target, type="attack"):
        closest_enemy_ground_unit = self.bot.known_enemy_units.not_flying.closest_to(
            unit) if self.bot.known_enemy_units.not_flying.exists else None
        closest_enemy_air_unit = self.bot.known_enemy_units.flying.closest_to(
            unit) if self.bot.known_enemy_units.flying.exists else None
        closest_enemy_unit = None

        # Find closest enemy unit that the unit can attack
        if closest_enemy_ground_unit is not None and unit.can_attack_ground:
            closest_enemy_unit = closest_enemy_ground_unit
        if closest_enemy_air_unit is not None and unit.can_attack_air:
            if closest_enemy_unit is None or closest_enemy_unit.distance_to(
                    unit.position) < closest_enemy_air_unit.distance_to(unit.position):
                closest_enemy_unit = closest_enemy_air_unit

        # Decide what to do
        if closest_enemy_unit is not None:
            if type == "attack" or closest_enemy_unit.distance_to(unit.position) < max(unit.ground_range,
                                                                                       unit.air_range):
                #if unit.type_id in [UnitTypeId.MARINE:
                await self._basic_attack(unit, closest_enemy_unit)
            else:
                await self.bot.do(unit.move(target))

    async def _basic_attack(self, unit, closest_enemy_unit):
        range = unit.air_range if closest_enemy_unit.is_flying else unit.ground_range
        distance = closest_enemy_unit.distance_to(unit)
        # print("Range=", range)
        # print("Distance=", distance)
        if distance < range * 0.8:
            await self.bot.do(unit.move(self.bot.start_location))
        else:
            if not unit.is_attacking:
                await self.bot.do(unit.attack(closest_enemy_unit))
