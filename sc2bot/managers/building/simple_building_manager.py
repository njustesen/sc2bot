from sc2bot.managers.interfaces import BuildingManager
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId


class SimpleBuildingManager(BuildingManager):

    def __init__(self, bot):
        super().__init__(bot)

        self.trained_at = {
            UnitTypeId.BANSHEE: UnitTypeId.STARPORT,
            UnitTypeId.BATTLECRUISER: UnitTypeId.STARPORT,
            UnitTypeId.CYCLONE: UnitTypeId.FACTORY,
            UnitTypeId.GHOST: UnitTypeId.BARRACKS,
            UnitTypeId.HELLION: UnitTypeId.FACTORY,
            UnitTypeId.LIBERATOR: UnitTypeId.STARPORT,
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKS,
            UnitTypeId.MARINE: UnitTypeId.BARRACKS,
            UnitTypeId.MEDIVAC: UnitTypeId.STARPORT,
            UnitTypeId.NUKE: UnitTypeId.GHOSTACADEMY,
            UnitTypeId.RAVEN: UnitTypeId.STARPORT,
            UnitTypeId.REAPER: UnitTypeId.STARPORT,
            UnitTypeId.SCV: UnitTypeId.COMMANDCENTER,
            UnitTypeId.SIEGETANK: UnitTypeId.FACTORY,
            UnitTypeId.THOR: UnitTypeId.FACTORY,
            UnitTypeId.VIKINGFIGHTER: UnitTypeId.STARPORT,
            UnitTypeId.WIDOWMINE: UnitTypeId.FACTORY
        }

        self.add_on_requirement = {
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKSTECHLAB,
            UnitTypeId.BANSHEE: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.BATTLECRUISER: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.CYCLONE: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.GHOST: UnitTypeId.BARRACKSTECHLAB,
            UnitTypeId.RAVEN: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.SIEGETANK: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.THOR: UnitTypeId.FACTORYTECHLAB
        }

        self.add_on_at = {
            UnitTypeId.BARRACKSTECHLAB: UnitTypeId.BARRACKS,
            UnitTypeId.BARRACKSREACTOR: UnitTypeId.BARRACKS,
            UnitTypeId.FACTORYTECHLAB: UnitTypeId.FACTORY,
            UnitTypeId.FACTORYREACTOR: UnitTypeId.FACTORY,
            UnitTypeId.STARPORTTECHLAB: UnitTypeId.STARPORT,
            UnitTypeId.STARPORTREACTOR: UnitTypeId.STARPORT
        }

        self.upgrades_from = {
            UnitTypeId.PLANETARYFORTRESS: UnitTypeId.COMMANDCENTER,
            UnitTypeId.ORBITALCOMMAND: UnitTypeId.COMMANDCENTER
        }

        self.researched_at = {
            UpgradeId.COMBATSHIELD: UnitTypeId.BARRACKSTECHLAB,
            UpgradeId.SIEGETECH: UnitTypeId.FACTORYTECHLAB,
            UpgradeId.BANSHEECLOAK: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.BANSHEESPEED: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.BATTLECRUISERENABLESPECIALIZATIONS: UnitTypeId.FUSIONCORE,
            UpgradeId.DRILLCLAWS: UnitTypeId.FACTORYTECHLAB,
            UpgradeId.HISECAUTOTRACKING: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.HIGHCAPACITYBARRELS: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.LIBERATORAGRANGEUPGRADE: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.MEDIVACINCREASESPEEDBOOST: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.NEOSTEELFRAME: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.PERSONALCLOAKING: UnitTypeId.GHOSTACADEMY,
            UpgradeId.PUNISHERGRENADES: UnitTypeId.BARRACKSTECHLAB,
            UpgradeId.RAVENCORVIDREACTOR: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.RAVENRECALIBRATEDEXPLOSIVES: UnitTypeId.STARPORTTECHLAB,
            UpgradeId.STIMPACK: UnitTypeId.BARRACKSTECHLAB,
            UpgradeId.TERRANBUILDINGARMOR: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANINFANTRYARMORSLEVEL1: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANINFANTRYARMORSLEVEL2: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANINFANTRYARMORSLEVEL3: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL1: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL2: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL3: UnitTypeId.ENGINEERINGBAY,
            UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1: UnitTypeId.ARMORY,
            UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2: UnitTypeId.ARMORY,
            UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3: UnitTypeId.ARMORY,
            UpgradeId.TERRANVEHICLEWEAPONSLEVEL1: UnitTypeId.ARMORY,
            UpgradeId.TERRANVEHICLEWEAPONSLEVEL2: UnitTypeId.ARMORY,
            UpgradeId.TERRANVEHICLEWEAPONSLEVEL3: UnitTypeId.ARMORY,
            UpgradeId.TERRANSHIPWEAPONSLEVEL1: UnitTypeId.ARMORY,
            UpgradeId.TERRANSHIPWEAPONSLEVEL2: UnitTypeId.ARMORY,
            UpgradeId.TERRANSHIPWEAPONSLEVEL3: UnitTypeId.ARMORY
        }

    async def run(self):

        # Raise depos when enemies are nearby
        for depo in self.bot.units(UnitTypeId.SUPPLYDEPOT).ready:
            for unit in self.bot.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 15:
                    break
            else:
                self.actions.append(depo(AbilityId.MORPH_SUPPLYDEPOT_LOWER))

        # Lower depos when no enemies are nearby
        for depo in self.bot.units(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            for unit in self.bot.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 10:
                    self.actions.append(depo(AbilityId.MORPH_SUPPLYDEPOT_RAISE))
                    break

    async def train(self, unit):
        # print("BuildingManager: training ", unit)
        if self.bot.can_afford(unit):
            for building in self.bot.units(self.trained_at[unit]).ready.noqueue:
                if unit in self.add_on_requirement:
                    for add_on in self.bot.units(self.add_on_requirement[unit]).ready:
                        if add_on.tag == building.add_on_tag:
                            self.actions.append(building.train(unit))
                            return
                else:
                    self.actions.append(building.train(unit))
                    return

    async def add_on(self, add_on):
        for building in self.bot.units(self.add_on_at[add_on]).ready:
            if not building.has_add_on:
                self.actions.append(building.build(add_on))
                return

    async def research(self, upgrade):
        for building in self.bot.units(self.researched_at[upgrade]).ready:
            self.actions.append(building.research(upgrade))
            return

    async def calldown_mule(self):
        for oc in self.bot.units(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs = self.bot.state.mineral_field.closer_than(10, oc)
            if mfs:
                mf = max(mfs, key=lambda x: x.mineral_contents)
                self.actions.append(oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf))
                return

    async def scan(self, location):
        for oc in self.bot.units(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs = self.bot.state.mineral_field.closer_than(10, oc)
            if mfs:
                self.actions.append(oc(AbilityId.SCANNERSWEEP_SCAN, location))
                return

    async def upgrade(self, upgrade):
        ability = None
        if upgrade == UnitTypeId.ORBITALCOMMAND:
            ability = AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND
        elif upgrade == UnitTypeId.PLANETARYFORTRESS:
            ability = AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS

        if ability is not None and self.bot.can_afford(upgrade):  # check if orbital is affordable
            for cc in self.bot.units(UnitTypeId.COMMANDCENTER).idle:  # .idle filters idle command centers
                self.actions.append(cc(ability))
                return

    def can_train(self, unit_type):
        if self.bot.can_afford(unit_type):
            for building in self.bot.units(self.trained_at[unit_type]).ready.noqueue:
                if unit_type in self.add_on_requirement:
                    for add_on in self.bot.units(self.add_on_requirement[unit_type]).ready:
                        if add_on.tag == building.add_on_tag:
                            return True
                else:
                    return True
        return False

    def can_upgrade(self, upgrade_type):
        ability = None
        if upgrade_type == UnitTypeId.ORBITALCOMMAND:
            ability = AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND
        elif upgrade_type == UnitTypeId.PLANETARYFORTRESS:
            ability = AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS
        if ability is not None and self.bot.can_afford(upgrade_type):  # check if orbital is affordable
            return self.bot.units(UnitTypeId.COMMANDCENTER).idle.exists
        return False

    def can_add_on(self, add_on):
        for building in self.bot.units(self.add_on_at[add_on]).ready:
            if not building.has_add_on:
                return True
        return False
