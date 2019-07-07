class Option:

    def __init__(self, cluster_id, features):
        self.cluster_id = cluster_id
        self.features = features
        self.n = 0
        self.wins = 0
        self.draws = 0
        self.builds = []

    def to_json(self):
        return {
            "cluster_id": self.cluster_id,
            "features": self.features,
            "n": self.n,
            "wins": self.wins,
            "draws": self.draws,
            "builds": self.builds
        }
