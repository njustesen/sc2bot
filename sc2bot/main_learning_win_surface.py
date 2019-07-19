import click
import time
import json
from run_utils import run_game

def run_all_points(points, method, model_path, comment="", timestamp=int(time.time())):
    # here we assume that points is a list of points that can be run as features.
    experiment_name = f"{method}_learning_surface"
    game_results = {}
    for i, point in enumerate(points):
        assert len(point) == 2
        print("-"*80)
        print("\n")
        print("NEW GAME")
        print("\n")
        print("-"*80)
        result, bot = run_game(point, "easy", experiment_name, model_path, comment=comment+f"_{i}_", timestamp=timestamp)

        game_results[str(i)] = {
            "point": point,
            "result": result
        }

        with open(f"./model_outputs/{timestamp}_{experiment_name}_outputs_{comment}_{i}.json", "w") as f:
            json.dump(bot.outputs, f)

        with open(f"./builds/{timestamp}_{experiment_name}_builds_{comment}_{i}.json", "w") as f:
            json.dump(bot.builds, f)
        
        with open(f"./enemy_units/{timestamp}_{experiment_name}_enemy_units_{comment}_{i}.json", "w") as f:
            json.dump(bot.max_seen_enemy_units, f)

        with open(f"./allied_units/{timestamp}_{experiment_name}_max_allied_units_{comment}_{i}.json", "w") as f:
            json.dump(bot.max_allied_units, f)

        with open(f"./individual_results_win_surface/{timestamp}_{experiment_name}_game_results_{comment}_{i}.json", "w") as f:
            json.dump(game_results[str(i)], f)
    
    with open(f"./results_win_surface/{timestamp}_{experiment_name}_game_results_{comment}.json", "w") as f:
        json.dump(game_results, f)

@click.command()
@click.option("--points_path", type=str, default="", help="Path to the json file with all points")
@click.option("--model_path", type=str, default="", help="Path to the .pt state dict file")
# @click.option("--repetitions", type=int, default=1, help="The second component of the features")
@click.option("--comment", type=str, default="", help="A comment to add to all filenames")
def main(points_path, model_path, comment):
    timestamp = int(time.time())
    method = points_path.split("/")[-1].split(".")[0].replace("points_", "")
    with open(points_path) as f:
        points = json.load(f)
    
    # points = points[:1]

    run_all_points(points, method, model_path, comment=comment, timestamp=timestamp)


if __name__ == '__main__':
    main() #pylint: disable=no-value-for-parameter
