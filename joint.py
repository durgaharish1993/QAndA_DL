"""Example running MemN2N on a single bAbI task.
Download tasks from facebook.ai/babi """
from __future__ import absolute_import
from __future__ import print_function

from data_utils import load_task, vectorize_data,jaccard_cutting
from sklearn import cross_validation, metrics
from memn2n import MemN2N
from itertools import chain
from six.moves import range, reduce

import tensorflow as tf
import numpy as np
import pandas as pd



hops_list = [4]
jaccard = [1]


for hop in hops_list:
    for jac in jaccard:
        print('The Hop Number is:',hop)
        print('jac is considered or not:',jac)

        # tf.flags.DEFINE_float("learning_rate", 0.01, "Learning rate for Adam Optimizer.")
        # tf.flags.DEFINE_integer("hops",hop, "Number of hops in the Memory Network.")
        #
        # ####################
        # tf.flags.DEFINE_float("anneal_rate", 15, "Number of epochs between halving the learnign rate.")
        # tf.flags.DEFINE_float("anneal_stop_epoch", 60, "Epoch number to end annealed lr schedule.")
        # tf.flags.DEFINE_float("max_grad_norm", 40.0, "Clip gradients to this norm.")
        # tf.flags.DEFINE_integer("evaluation_interval", 10, "Evaluate and print results every x epochs")
        # tf.flags.DEFINE_integer("batch_size", 32, "Batch size for training.")
        # tf.flags.DEFINE_integer("epochs", 60, "Number of epochs to train for.")
        # tf.flags.DEFINE_integer("embedding_size", 40, "Embedding size for embedding matrices.")
        # tf.flags.DEFINE_integer("memory_size", 50, "Maximum size of memory.")
        # tf.flags.DEFINE_integer("random_state", None, "Random state.")
        # tf.flags.DEFINE_string("data_dir", "data/tasks_1-20_v1-2/en/", "Directory containing bAbI tasks")
        # tf.flags.DEFINE_string("output_file", file_name, "Name of output file for final bAbI accuracy scores.")


        hops = hop

        learning_rate = 0.01
        anneal_rate = 15
        anneal_stop_epoch = 60
        max_grad_norm = 40.0
        evaluation_interval = 10
        batch_size = 32
        epochs = 60
        embedding_size = 40
        memory_size = 100
        random_state = None
        data_dir = "data/tasks_1-20_v1-2/en/"
	file_name = 'output_hop_'+str(hop)+'_jac_'+str(jac)+'_memory_'+str(memory_size)+'_gradient_001.csv'

	print(file_name)
        output_file = file_name










        FLAGS = tf.flags.FLAGS
        # load all train/test data
        ids = range(1, 21)
        train, test = [], []
        for i in ids:
            tr, te = load_task(data_dir, i)
            train.append(tr)
            test.append(te)
        data = list(chain.from_iterable(train + test))

        if jac==1:
            temp_train = []
            for t in train:
                temp_t=jaccard_cutting(t)
                temp_train.append(temp_t)

            temp_test = []
            for t in test:
                temp_t = jaccard_cutting(t)
                temp_test.append(temp_t)
            train = temp_train
            test = temp_test



        vocab = sorted(reduce(lambda x, y: x | y, (set(list(chain.from_iterable(s)) + q + a) for s, q, a in data)))
        word_idx = dict((c, i + 1) for i, c in enumerate(vocab))

        max_story_size = max(map(len, (s for s, _, _ in data)))
        mean_story_size = int(np.mean([ len(s) for s, _, _ in data ]))
        sentence_size = max(map(len, chain.from_iterable(s for s, _, _ in data)))
        query_size = max(map(len, (q for _, q, _ in data)))
        memory_size = min(memory_size, max_story_size)

        # Add time words/indexes
        for i in range(memory_size):
            word_idx['time{}'.format(i+1)] = 'time{}'.format(i+1)

        vocab_size = len(word_idx) + 1 # +1 for nil word
        sentence_size = max(query_size, sentence_size) # for the position
        sentence_size += 1  # +1 for time words

        print("Longest sentence length", sentence_size)
        print("Longest story length", max_story_size)
        print("Average story length", mean_story_size)


        trainS = []
        valS = []
        trainQ = []
        valQ = []
        trainA = []
        valA = []












        for task in train:
            S, Q, A = vectorize_data(task, word_idx, sentence_size, memory_size)
            ts, vs, tq, vq, ta, va = cross_validation.train_test_split(S, Q, A, test_size=0.1, random_state=random_state)
            trainS.append(ts)
            trainQ.append(tq)
            trainA.append(ta)
            valS.append(vs)
            valQ.append(vq)
            valA.append(va)

        trainS = reduce(lambda a,b : np.vstack((a,b)), (x for x in trainS))
        trainQ = reduce(lambda a,b : np.vstack((a,b)), (x for x in trainQ))
        trainA = reduce(lambda a,b : np.vstack((a,b)), (x for x in trainA))
        valS = reduce(lambda a,b : np.vstack((a,b)), (x for x in valS))
        valQ = reduce(lambda a,b : np.vstack((a,b)), (x for x in valQ))
        valA = reduce(lambda a,b : np.vstack((a,b)), (x for x in valA))

        testS, testQ, testA = vectorize_data(list(chain.from_iterable(test)), word_idx, sentence_size, memory_size)

        n_train = trainS.shape[0]
        n_val = valS.shape[0]
        n_test = testS.shape[0]

        print("Training Size", n_train)
        print("Validation Size", n_val)
        print("Testing Size", n_test)

        print(trainS.shape, valS.shape, testS.shape)
        print(trainQ.shape, valQ.shape, testQ.shape)
        print(trainA.shape, valA.shape, testA.shape)

        train_labels = np.argmax(trainA, axis=1)
        test_labels = np.argmax(testA, axis=1)
        val_labels = np.argmax(valA, axis=1)

        tf.set_random_seed(random_state)
        #batch_size = batch_size

        # This avoids feeding 1 task after another, instead each batch has a random sampling of tasks
        batches = zip(range(0, n_train-batch_size, batch_size), range(batch_size, n_train, batch_size))
        batches = [(start, end) for start,end in batches]

        with tf.Session() as sess:
            print('I am here')
            model = MemN2N(batch_size, vocab_size, sentence_size, memory_size, embedding_size, session=sess,
                           hops=hops, max_grad_norm=max_grad_norm)
            for i in range(1, epochs+1):
                # Stepped learning rate
                if i - 1 <= anneal_stop_epoch:
                    anneal = 2.0 ** ((i - 1) // anneal_rate)
                else:
                    anneal = 2.0 ** (anneal_stop_epoch // anneal_rate)
                lr = learning_rate / anneal

                np.random.shuffle(batches)
                total_cost = 0.0
                for start, end in batches:
                    s = trainS[start:end]
                    q = trainQ[start:end]
                    a = trainA[start:end]
                    cost_t = model.batch_fit(s, q, a, lr)
                    total_cost += cost_t

                if i % evaluation_interval == 0:
                    train_accs = []
                    for start in range(0, n_train, n_train/20):
                        end = start + n_train/20
                        s = trainS[start:end]
                        q = trainQ[start:end]
                        pred = model.predict(s, q)
                        acc = metrics.accuracy_score(pred, train_labels[start:end])
                        train_accs.append(acc)

                    val_accs = []
                    for start in range(0, n_val, n_val/20):
                        end = start + n_val/20
                        s = valS[start:end]
                        q = valQ[start:end]
                        pred = model.predict(s, q)
                        acc = metrics.accuracy_score(pred, val_labels[start:end])
                        val_accs.append(acc)

                    test_accs = []
                    for start in range(0, n_test, n_test/20):
                        end = start + n_test/20
                        s = testS[start:end]
                        q = testQ[start:end]
                        pred = model.predict(s, q)
                        acc = metrics.accuracy_score(pred, test_labels[start:end])
                        test_accs.append(acc)

                    print('-----------------------')
                    print('Epoch', i)
                    print('Total Cost:', total_cost)
                    print()
                    t = 1
                    for t1, t2, t3 in zip(train_accs, val_accs, test_accs):
                        print("Task {}".format(t))
                        print("Training Accuracy = {}".format(t1))
                        print("Validation Accuracy = {}".format(t2))
                        print("Testing Accuracy = {}".format(t3))
                        print()
                        t += 1
                    print('-----------------------')

                # Write final results to csv file
                if i == epochs:
                    print('Writing final results to {}'.format(output_file))
                    df = pd.DataFrame({
                    'Training Accuracy': train_accs,
                    'Validation Accuracy': val_accs,
                    'Testing Accuracy': test_accs
                    }, index=range(1, 21))
                    df.index.name = 'Task'
                    df.to_csv(output_file)

