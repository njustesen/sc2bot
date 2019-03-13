class Manager:

    def __init__(self, bot):
        self.bot = bot

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")

    async def on_unit_destroyed(self, unit_tag):
        """ Override this in your bot class. """
        pass

    async def on_unit_created(self, unit):
        """ Override this in your bot class. """
        pass

    async def on_building_construction_started(self, unit):
        """ Override this in your bot class. """
        pass

    async def on_building_construction_complete(self, unit):
        """ Override this in your bot class. """
        pass


class ProductionManager(Manager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot)
        self.worker_manager = worker_manager
        self.building_manager = building_manager

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")


class ScoutingManager(Manager):

    def __init__(self, bot, worker_manager, building_manager):
        super().__init__(bot)
        self.worker_manager = worker_manager
        self.building_manager = building_manager

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")


class AssaultManager(Manager):

    def __init__(self, bot, army_manager, worker_manager):
        super().__init__(bot)
        self.army_manager = army_manager
        self.worker_manager = worker_manager

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")


class WorkerManager(Manager):

    def __init__(self, bot):
        super().__init__(bot)

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")

    async def distribute(self):
        raise NotImplementedError("Must be overridden by subclass")

    async def build(self, building, location=None):
        raise NotImplementedError("Must be overridden by subclass")

    async def scout(self, location):
        raise NotImplementedError("Must be overridden by subclass")

    async def rush(self, location):
        raise NotImplementedError("Must be overridden by subclass")

    async def defend(self, location):
        raise NotImplementedError("Must be overridden by subclass")


class BuildingManager(Manager):

    def __init__(self, bot):
        super().__init__(bot)

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")

    async def train(self, unit):
        raise NotImplementedError("Must be overridden by subclass")

    async def add_on(self, add_on):
        raise NotImplementedError("Must be overridden by subclass")

    async def research(self, upgrade):
        raise NotImplementedError("Must be overridden by subclass")


class ArmyManager(Manager):

    def __init__(self, bot):
        super().__init__(bot)

    async def run(self):
        raise NotImplementedError("Must be overridden by subclass")

    async def attack(self, location, unit_types=None):
        raise NotImplementedError("Must be overridden by subclass")

    async def defend(self, location, unit_types=None):
        raise NotImplementedError("Must be overridden by subclass")
