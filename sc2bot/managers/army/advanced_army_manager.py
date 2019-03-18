from sc2bot.managers.interfaces import ArmyManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2bot.managers.army.squad import Squad
from sc2.ids.ability_id import AbilityId
import math
from sc2.units import Units


class AdvancedArmyManager(ArmyManager):

    def __init__(self, bot):
        super().__init__(bot)
        self.squads = []

    async def run(self):

        # Create squads
        for squad in self.squads:
            units = []
            if squad.unit_types is None:
                for unit in self.bot.units.not_structure:
                    if unit.type_id not in [UnitTypeId.SCV, UnitTypeId.MULE]:
                        units.append(unit)
            else:
                for unit in self.bot.units:
                    if unit.type_id in squad.unit_types:
                            units.append(unit)
            squad.units = Units(units, self.bot.game_data())

        # Control squads:
        for squad in self.squads:
            await squad.run()

    async def attack(self, target, unit_types=None):
        # Unload bunkers
        bunkers = self.bot.units(UnitTypeId.BUNKER).ready
        for bunker in bunkers:
            for passenger in bunker.passengers:
                if unit_types is None or passenger.type_id in unit_types:
                    self.actions.append(bunker(AbilityId.UNLOADALL))
                    self.actions.append(bunker(AbilityId.UNLOADALL_BUNKER))
        squad = Squad(self.bot, target, unit_types, order="attack")
        if unit_types is None:
            self.squads = [squad]
        else:
            self.squads.append(Squad(self.bot, target, unit_types, order="attack"))

    async def defend(self, target, unit_types=None):
        squad = Squad(self.bot, target, unit_types, order="defend")
        if unit_types is None:
            self.squads = [squad]
        else:
            self.squads.append(Squad(self.bot, target, unit_types, order="defend"))

