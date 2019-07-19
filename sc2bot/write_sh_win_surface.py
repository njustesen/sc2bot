string = ""

def get_command(feature, allied_or_enemy):
    return f"python main_learning_win_surface.py --points_path=/home/mgd/Projects/sc2bot/sc2bot/points_win_surface/points_{allied_or_enemy}_{feature}.json --model_path=/home/mgd/Projects/sc2bot/sc2bot/models_kmeans/model_{allied_or_enemy}_{feature}_kmeans_state_dict.pt --comment=100_random_points" + "\n"

for feature in ["PCA", "Isomap", "UMAP"]:
    for a in ["allied", "enemy"]:
        string += get_command(feature, a)

with open("./to_run_win_surface.sh", "w") as f:
    f.write(string)
