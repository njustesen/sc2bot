import click
import time
from run_utils import feature_experiment, bayesian_optimization_experiment, ucb_experiment

@click.command()
@click.option("--features_name", type=str, default="PCA", help="Either PCA, UMAP or None")
# @click.option("--cluster_key", type=int, default=0, help="The cluster number to grab the features from.")
@click.option("--cluster_centers_path", type=str, default="", help="Path to the cluster centers file")
@click.option("--model_path", type=str, default="", help="Path to the .pt state dict file")
@click.option("--repetitions", type=int, default=1, help="The second component of the features")
@click.option("--comment", type=str, default="", help="A comment to add to all filenames")
def main(features_name, cluster_centers_path, model_path, repetitions, comment):
    # [0.8493908047676086, 0.44843146204948425]
    timestamp = int(time.time())
    # feature_experiment(repetitions, features_name, cluster_key, cluster_centers_path, model_path, comment=comment, timestamp=timestamp)
    # bayesian_optimization_experiment(repetitions, features_name, cluster_centers_path, model_path, comment, timestamp)
    ucb_experiment(repetitions, features_name, cluster_centers_path, model_path, comment, timestamp)


if __name__ == '__main__':
    main() #pylint: disable=no-value-for-parameter
