class Option:
    def __init__(self, name, comment, features):
        self.name = name
        self.features = features
        self.comment = comment
        self.n = 0
        self.wins = 0
        self.draws = 0
        self.builds = []
        # self.enemy_builds = []
        # self.max_allied_units = []

    def to_json(self):
        return {
            "name": self.name,
            "features": self.features,
            "comment": self.comment,
            "n": self.n,
            "wins": self.wins,
            "draws": self.draws,
            "builds": self.builds
            # "enemy_builds": self.enemy_builds
        }
