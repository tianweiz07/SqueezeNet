from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import argparse
import os
import re
import sys
import math

from datetime import datetime
import numpy as np
import tensorflow as tf

import arg_parsing
import dataset
import network

FLAGS = arg_parsing.parser.parse_args()

def test():
    with tf.Graph().as_default() as g:
        images, labels = dataset.process_inputs("testing")

        logits = network.inference(images)

        top_k_op = tf.nn.in_top_k(logits, labels, 1)

        variable_averages = tf.train.ExponentialMovingAverage(
                               arg_parsing.MOVING_AVERAGE_DECAY)
        variables_to_restore = variable_averages.variables_to_restore()
        saver = tf.train.Saver(variables_to_restore)

        with tf.Session() as sess:
            ckpt = tf.train.get_checkpoint_state(FLAGS.model_dir)
            if ckpt and ckpt.model_checkpoint_path:
                saver.restore(sess, ckpt.model_checkpoint_path)
                global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
            else:
                raise ValueError("No checkpoint file found")

            coord = tf.train.Coordinator()
            try:
                threads = []
                for qr in tf.get_collection(tf.GraphKeys.QUEUE_RUNNERS):
                    threads.extend(qr.create_threads(sess, coord=coord, daemon=True, start=True))

                num_iter = int(math.ceil(FLAGS.num_examples / FLAGS.batch_size))
                true_count = 0
                total_sample_count = num_iter * FLAGS.batch_size
                step = 0
                while step < num_iter and not coord.should_stop():
                    predictions = sess.run([top_k_op])
                    true_count += np.sum(predictions)
                    step += 1

                precision = true_count / total_sample_count
                print('%s: precision @ 1 = %.3f' % (datetime.now(), precision))
            except Exception as e:
                coord.request_stop(e)
                
            coord.request_stop()
            coord.join(threads, stop_grace_period_secs=10)
