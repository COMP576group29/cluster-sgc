import pickle as pkl
import os
from math import log
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
import matplotlib.pyplot as plt

from clustersgc.clustering import ClusteringMachine
from clustersgc.clustertrain import ClusterTrainer
from clustersgc.utils import load_reddit,load_npz,set_seed
import pickle as pkl

SEED=42

DATASET_DIR="datasets/"
DATASET_NAME = "reddit"
TEST_RATIO=0.1 #0.9 for clustersgc

CLUSTER =True
CLUSTER_METHOD="metis" #metis random
CLUSTER_NUM=10

MODEL="SGC"
#SGC
DEGREE=6 #2 only when sgc
#GCN&SGCN
LAYERS = [16,16,16] ##SGCN,defalut16,16,16
HIDDEN = 16 #GCN
DROPOUT=0.5 #defalut 0.5

EPOCHS=200 #200 for clustergcn 100 for sgc
LR=0.2 #0.01 for clustergcn 0.2 for sgc
WEIGHT_DECAY=0 #5e-6 for sgc

TUNED = False
if TUNED:
        with open("cluster-tuning/{}-lr.txt".format(DATASET_NAME), 'rb') as f:
            opt = pkl.load(f)
            #WEIGHT_DECAY =opt['weight_decay']
            LR = opt['lr']
            #DEGREE = int(opt['degree'])
            #print("using tuned weight decay: {} lr:{} degree:{}".format(WEIGHT_DECAY,LR,DEGREE))
            print("using tuned lr: {}".format(LR))
        with open("cluster-tuning/{}-weight_decay.txt".format(DATASET_NAME), 'rb') as f2:
            opt = pkl.load(f2)
            #WEIGHT_DECAY =opt['weight_decay']
            WEIGHT_DECAY = opt['weight_decay']
            #DEGREE = int(opt['degree'])
            #print("using tuned weight decay: {} lr:{} degree:{}".format(WEIGHT_DECAY,LR,DEGREE))
            print("using tuned weight_decay: {}".format(WEIGHT_DECAY))

set_seed(SEED)

# Hyperparameter optimization
space = {#'weight_decay' : hp.loguniform('weight_decay', log(1e-10), log(1e-4)),
         #'lr' : hp.uniform('lr', 0.001, 0.01),
         #'degree' : hp.quniform('degree', 1,5,4),
        'cluster_num' : hp.uniform('cluster_num', 2,30)
         }

if DATASET_NAME == "reddit":
    graph, features, labels = load_reddit(DATASET_DIR)
else:
    graph, features, labels= load_npz(DATASET_DIR,DATASET_NAME)
print("Finished data loading.")

if CLUSTER == False:
    CLUSTER_METHOD = "random"
    CLUSTER_NUM = 1

def clustersgc_objective(space):
    clustering_machine = ClusteringMachine(MODEL, DEGREE, CLUSTER_METHOD, round(space['cluster_num']), TEST_RATIO, graph, features,
                                           labels)  # normalize
    precompute_time = clustering_machine.decompose()
    print("Finished decompose")
    gcn_trainer = ClusterTrainer(MODEL, LAYERS, DROPOUT, HIDDEN,DEGREE, EPOCHS,LR,WEIGHT_DECAY,clustering_machine)
    model, train_time = gcn_trainer.train()
    test_f1,test_ac = gcn_trainer.test()
    # print('weight decay: {:.2e} lr:{}'.format(space['weight_decay'], space['lr']) + 'f1score: {:.4f}'.format(test_f1))
    print('cluster_num:{}'.format(round(space['cluster_num'])) + 'f1score: {:.4f}'.format(test_f1))
    return {'loss': -test_f1, 'status': STATUS_OK}

trials = Trials()
best = fmin(clustersgc_objective, space=space, algo=tpe.suggest, max_evals=30,trials=trials)
#print("Best weight decay: {:.2e} lr:{}".format(best["weight_decay"],best['lr']))
print("Best cluster_num:{}".format(best['cluster_num']))

# os.makedirs("./cluster-tuning", exist_ok=True)
# path = 'cluster-tuning/{}.txt'.format(DATASET_NAME)
# with open(path, 'wb') as f: pkl.dump(best, f)

clustersgc_objective, ax = plt.subplots(1)
xs = [t['misc']['vals']['cluster_num'] for t in trials.trials]
ys = [t['result']['loss'] for t in trials.trials]
ax.scatter(xs, ys, s=20, linewidth=0.01, alpha=0.75)
ax.set_title('$val$ $vs$ $x$ ', fontsize=18)
ax.set_xlabel('$cluster_num$', fontsize=16)
ax.set_ylabel('$f1-score$', fontsize=16)
plt.show()
