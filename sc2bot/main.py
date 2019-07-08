import click
import time
from run_utils import feature_experiment

@click.command()
@click.option("--features_name", type=str, default="PCA", help="Either PCA, UMAP or None")
@click.option("--feature_1", type=float, default=0.5, help="The first component of the features")
@click.option("--feature_2", type=float, default=0.5, help="The second component of the features")
@click.option("--model_path", type=str, default="", help="Path to the .pt state dict file")
@click.option("--repetitions", type=int, default=1, help="The second component of the features")
@click.option("--comment", type=str, default="", help="A comment to add to all filenames")
def main(features_name, feature_1, feature_2, model_path, repetitions, comment):
    # [0.8493908047676086, 0.44843146204948425]
    timestamp = int(time.time())
    feature_experiment(repetitions, features_name, [feature_1, feature_2], model_path, comment=comment, timestamp=timestamp)


if __name__ == '__main__':
    main()
