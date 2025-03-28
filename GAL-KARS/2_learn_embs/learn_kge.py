from pykeen.triples import TriplesFactory
from pykeen.pipeline import pipeline
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import os
from os import path
import torch

# organized as list so that it is easy to automatically iterate 
# if you want to add other datasets, models, or embedding dimensions

np.random.seed(42)

# set dataset name, model of the GCN, dimension, num_layer, epochs
datasets = ['ml1m', 'dbbook']
emb_models = ['CompGCN']
settings = [8,7,6,5,4,3,2,1]
emb_dims = [64]
n_layers = [1,2,3]
emb_epochs = 15

# dict of setting id -> name (folder in which kgs are stored)
setting_kgs = {
    '1': '1_cf',
    '2': '2_cf_dbpedia',
    '3': '3_cf_llm_i',
    '4': '4_cf_llm_u',
    '5': '5_cf_llm_iu',
    '6': '6_cf_dbpedia_llm_i',
    '8': '8_cf_dbpedia_llm_ui',
    '7': '7_cf_dbpedia_llm_u'
}

log_file = open('log.txt', 'w')

for emb_model in emb_models:
    for emb_dim in emb_dims:
        for dataset in datasets:
            for setting in settings:
                for n_layer in n_layers:

                    printline = f'{dataset}_setting_{setting}_{emb_model}_k={str(emb_dim)}_l={str(n_layer)}'
                    print('Starting ' + printline)
                    log_file.write('Starting' + printline)
                    
                    folder = f'results/{dataset}_setting_{setting}_{emb_model}_k={str(emb_dim)}_l={str(n_layer)}'

                    train_path = f'{dataset}/setting_{setting_kgs[setting]}/pykeen_train.tsv'
                    test_path = f'{dataset}/setting_{setting_kgs[setting]}/pykeen_test.tsv'

                    checkpoint_name_file = f'{dataset}_checkpoints_setting_{setting}_{emb_model}_k={str(emb_dim)}_l={str(n_layer)}'

                    # if embs already exists, skip
                    if os.path.isfile(folder+'/embeddings.tsv') and False:
                        print('Existing embedding in ' + folder)
                        continue

                    # otherwise train
                    try:      

                        print('Starting learning:' + folder)
                        print("Starting learning:", printline)
                        

                        emb_training = TriplesFactory.from_path(
                            train_path,
                            create_inverse_triples=True,
                        )

                        emb_testing = TriplesFactory.from_path(
                            test_path,
                            entity_to_id=emb_training.entity_to_id,
                            relation_to_id=emb_training.relation_to_id,
                            create_inverse_triples=True,
                        )

                        result = pipeline(
                            training=emb_training,
                            testing=emb_testing,
                            model=emb_model,
                            device="cuda",
                            model_kwargs=dict(embedding_dim=emb_dim,
                                            encoder_kwargs=dict(num_layers=n_layer)),
                            random_seed=42,
                            evaluation_fallback = True,
                            training_kwargs=dict(
                                num_epochs=emb_epochs,
                                checkpoint_name=checkpoint_name_file,
                                checkpoint_directory='checkpoints',
                                checkpoint_frequency=1
                            ),
                        )

                        if not os.path.exists(folder):
                            os.mkdir(folder)


                        torch.save(result, folder+'/pipeline_result.dat')

                        map_ent = pd.DataFrame(data=list(emb_training.entity_to_id.items()))
                        map_ent.to_csv(folder+'/entities_to_id.tsv', sep='\t', header=False, index=False)
                        map_ent = pd.DataFrame(data=list(emb_training.relation_to_id.items()))
                        map_ent.to_csv(folder+'/relations_to_id.tsv', sep='\t', header=False, index=False)


                        # save mappings
                        result.save_to_directory(folder, save_training=True, save_metadata=True)

                        # extract embeddings with gpu
                        entity_embedding_tensor = result.model.entity_representations[0](indices = None)
                        # save entity embeddings to a .tsv file (gpu)
                        df = pd.DataFrame(data=entity_embedding_tensor.cpu().data.numpy())

                        # extract embeddings with cpu
                        #entity_embedding_tensor = result.model.entity_representations[0](indices=None).detach().numpy()
                        # save entity embeddings to a .tsv file (cpu)
                        #df = pd.DataFrame(data=entity_embedding_tensor.astype(float))

                        outfile = folder + '/embeddings.tsv'
                        df.to_csv(outfile, sep='\t', header=False, index=False)

                        print('Completed ' + printline)
                        log_file.write('Completed\n')
                    
                    except Exception as e:

                        print('An error occoured in ' + printline)
                        log_file.write('An error occoured in ' + printline + '\n')
                        print(e)
                        log_file.write(str(e)+'\n')

log_file.flush()
log_file.close()
