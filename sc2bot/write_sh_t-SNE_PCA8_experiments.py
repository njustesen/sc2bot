string = ""

# dicts:

# allied_PCA = {
#     "marine": 2,
#     "cyclone": 5,
#     "reaper": 3,
#     "hellion": 11
# }

# allied_Isomap = {
#     "marine": 8,
#     "cyclone": 18,
#     "reaper": 3,
#     "hellion": 6
# }

# allied_UMAP = {
#     "marine": 1,
#     "cyclone": 9,
#     "reaper": 4,
#     "hellion": 2
# }

# enemy_PCA = {
#     "zergling": 3,
#     "queen": 6,
#     "roach": 11,
#     "mutalisk": 16
# }

# enemy_Isomap = {
#     "zergling": 3,
#     "queen": 23,
#     "roach": 8,
#     "mutalisk": 7
# }

# enemy_UMAP = {
#     "zergling": 0,
#     "queen": 10,
#     "roach": 18,
#     "mutalisk": 11
# }

allied_t_SNE = {
    "marine": 6,
    "hellion": 3,
    "reaper": 10,
    "cyclone": 16
}

def get_command(feature, key, name, allied_or_enemy):
    return f"python main.py --features_name={feature} --cluster_key={key} --cluster_centers_path=\"/home/mgd/Projects/sc2bot/sc2bot/data/cluster_centers_t-SNE_PCA8_allied_kmeans_1563641162.json\" --model_path=\"/home/mgd/Projects/sc2bot/sc2bot/models_kmeans/model_{allied_or_enemy}_{feature}_kmeans_state_dict.pt\" --repetitions=100 --comment={allied_or_enemy}_kmeans_experiment_cluster_{key}_{name}" + "\n"

def write_for_dict(dict_, feature, allied_or_enemy):
    string = ""
    for name, cluster_key in dict_.items():
        string += get_command(feature, cluster_key, name, allied_or_enemy)
    return string

def get_PCA8_command():
    string = ""
    for k in [5, 7, 10, 4]:
        string += f"python main.py --features_name=PCA8 --cluster_key={k} --cluster_centers_path=\"/home/mgd/Projects/sc2bot/sc2bot/data/cluster_centers_t-SNE_PCA8_allied_kmeans_1563641162.json\" --model_path=/home/mgd/Projects/sc2bot/sc2bot/models_kmeans/model_allied_PCA8_kmeans_state_dict.pt --repetitions=80 --comment=allied_kmeans_experiment_cluster_{k}_nounit" + "\n"
    return string

string = ""
# string += write_for_dict(allied_t_SNE, "t-SNE", "allied")
string += get_PCA8_command()
# string += write_for_dict(allied_Isomap, "Isomap", "allied")
# string += write_for_dict(allied_UMAP, "UMAP", "allied")
# string += write_for_dict(enemy_PCA, "PCA", "enemy")
# string += write_for_dict(enemy_Isomap, "Isomap", "enemy")
# string += write_for_dict(enemy_UMAP, "UMAP", "enemy")

with open("./to_run_t-SNE_PCA8_experiment.sh", "w") as f:
    f.write(string)
