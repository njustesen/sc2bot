for key in $(seq 0 1)
do
    for features in PCA Isomap UMAP
    do
        python main.py --features_name=${features} --cluster_key=${key} --cluster_centers_path=/home/mgd/Projects/sc2bot/sc2bot/data/cluster_centers_Allied_${features}_1563018904.json --model_path=/home/mgd/Projects/sc2bot/sc2bot/models_kmeans/model_allied_${features}_kmeans_state_dict.pt --repetitions=1 --comment=allied_kmeans_experiment
        python main.py --features_name=${features} --cluster_key=${key} --cluster_centers_path=/home/mgd/Projects/sc2bot/sc2bot/data/cluster_centers_Enemy_${features}_1563018904.json --model_path=/home/mgd/Projects/sc2bot/sc2bot/models_kmeans/model_enemy_${features}_kmeans_state_dict.pt --repetitions=1 --comment=enemy_kmeans_experiment
    done
done