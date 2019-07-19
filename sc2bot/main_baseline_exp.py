import click
import time
import json
from run_utils import run_game


def baseline_experiment(n, model_path, comment="", timestamp=int(time.time())):
    features_name = "baseline"
    win_results = {
        "win": 0,
        "draws": 0,
        "loss": 0
    }
    for i in range(n):
        print("-"*80)
        print("\n")
        print("NEW GAME")
        print("\n")
        print("-"*80)
        result, bot = run_game([], "easy", features_name, model_path, comment=comment+f"_{i}_", timestamp=timestamp)

        with open(f"./model_outputs/{timestamp}_{features_name}_outputs_{comment}_{i}.json", "w") as f:
            json.dump(bot.outputs, f)

        with open(f"./builds/{timestamp}_{features_name}_builds_{comment}_{i}.json", "w") as f:
            json.dump(bot.builds, f)
        
        with open(f"./enemy_units/{timestamp}_{features_name}_enemy_units_{comment}_{i}.json", "w") as f:
            json.dump(bot.max_seen_enemy_units, f)

        with open(f"./allied_units/{timestamp}_{features_name}_max_allied_units_{comment}_{i}.json", "w") as f:
            json.dump(bot.max_allied_units, f)
        
        if result == 1:
            win_results["win"] += 1
        elif result == 0.5:
            win_results["draw"] += 1
        else:
            win_results["loss"] += 1
        
    with open(f"./win_results/{timestamp}_{features_name}_win_results_{comment}.json", "w") as f:
        json.dump(win_results, f)

@click.command()
# @click.option("--features_name", type=str, default="PCA", help="Either PCA, UMAP or None")
# @click.option("--cluster_key", type=int, default=0, help="The cluster number to grab the features from.")
# @click.option("--cluster_centers_path", type=str, default="", help="Path to the cluster centers file")
@click.option("--model_path", type=str, default="", help="Path to the .pt state dict file")
@click.option("--repetitions", type=int, default=1, help="The second component of the features")
@click.option("--comment", type=str, default="", help="A comment to add to all filenames")
def main(model_path, repetitions, comment):
    timestamp = int(time.time())
    baseline_experiment(repetitions, model_path, comment=comment, timestamp=timestamp)


if __name__ == '__main__':
    main() #pylint: disable=no-value-for-parameter
