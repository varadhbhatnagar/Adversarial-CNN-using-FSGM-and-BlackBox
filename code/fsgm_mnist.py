# -*- coding: utf-8 -*-
"""FSGM-mnist.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1kgrvII5mraRQjP-w23JTNIJo91YLc0-S
"""

!ls drive/"My Drive"/
!pip install git+https://github.com/tensorflow/cleverhans.git#egg=cleverhans

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import numpy as np
import tensorflow as tf

from cleverhans.compat import flags
from cleverhans.loss import CrossEntropy
from cleverhans.dataset import MNIST
from cleverhans.utils_tf import model_eval
from cleverhans.train import train
from cleverhans.attacks import FastGradientMethod
from cleverhans.utils import AccuracyReport, set_log_level
from cleverhans.model_zoo.basic_cnn import ModelBasicCNN

from tensorflow.python.util import deprecation
deprecation._PRINT_DEPRECATION_WARNINGS = False
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

import warnings 
warnings.filterwarnings('ignore')

x = None
y = None
report = None
sess = None

def initialize_tensorflow(img_rows, img_cols, nchannels, nb_classes, num_threads=None):
    global report , x , y, sess
    report = AccuracyReport()
    tf.set_random_seed(1234)
    #set_log_level(logging.DEBUG)

    if num_threads:
        config_args = dict(intra_op_parallelism_threads=1)
    else:
        config_args = {}
    sess = tf.Session(config=tf.ConfigProto(**config_args))

    x = tf.placeholder(tf.float32, shape=(None, img_rows, img_cols,
                                          nchannels))
    y = tf.placeholder(tf.float32, shape=(None, nb_classes))


def do_eval(preds, eval_params, x_set, y_set, report_key, is_adv=None):
    acc = model_eval(sess, x, y, preds, x_set, y_set, args=eval_params)
    setattr(report, report_key, acc)
    if is_adv is None:
        report_text = None
    elif is_adv:
        report_text = 'adversarial'
    else:
        report_text = 'legitimate'
    if report_text:
        print('Test accuracy on %s examples: %0.4f' % (report_text, acc))

# Some utility functions

def preprocessEmnist(X):
    
    Y = np.mean(X, axis=1)
    Y = Y.reshape(Y.shape[0],1)
    Z = np.std(X, axis=1)
    Z = Z.reshape(Z.shape[0],1)
    return ((X-Y)/Z)

def oneHotEncodeY(Y, nb_classes):
	return (np.eye(nb_classes)[Y]).astype(int)

class CleanCNN:

    def __init__(self, nb_epochs, batch_size, learning_rate, eps = 0.3, clip_min=0, clip_max=1):
        self.train_params = {
            'nb_epochs': nb_epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate
        }
        self.eval_params = {'batch_size': batch_size}
        self.fgsm_params = {
            'eps': eps,
            'clip_min': clip_min,
            'clip_max': clip_max
        }

        self.x_train = None
        self.y_train = None
        self.x_test = None
        self.y_test = None
        self.range = np.random.RandomState([2019, 11, 25])
        self.model = None
        self.preds = None
        self.loss = None
        self.img_rows = None
        self.img_cols = None
        self.nchannels = None
        self.nb_classes = None

    
    def get_data(self, train_start, train_end, test_start, test_end):
        mnist = MNIST(train_start=train_start, train_end=train_end,
                      test_start=test_start, test_end=test_end)
        self.x_train, self.y_train = mnist.get_set('train')
        self.x_test, self.y_test = mnist.get_set('test')
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]
        self.nb_classes = self.y_train.shape[1]


    def train(self, nb_filters, label_smoothing):
        self.model = ModelBasicCNN('model1', self.nb_classes, nb_filters)
        self.preds = self.model.get_logits(x)
        self.loss = CrossEntropy(self.model, smoothing=label_smoothing)

        train(sess, self.loss, self.x_train, self.y_train, evaluate=self.evaluate,
              args=self.train_params, rng=self.range, var_list=self.model.get_params())

    def evaluate(self):
        do_eval(self.preds, self.eval_params, self.x_test, self.y_test, 'clean_train_clean_eval', False)

    def test(self):
        do_eval(self.preds, self.eval_params, self.x_train, self.y_train, 'train_clean_train_clean_eval')

    def adverserial_testing(self):
        fgsm = FastGradientMethod(self.model, sess=sess)
        adv_x = fgsm.generate(x, **self.fgsm_params)
        preds_adv = self.model.get_logits(adv_x)

        #Call from mail
        do_eval(preds_adv, self.eval_params, self.x_test, self.y_test, 'clean_train_adv_eval', True)
        do_eval(preds_adv, self.eval_params, self.x_train, self.y_train, 'train_clean_train_adv_eval')

        print('Repeating the process, using adversarial training')


class AdverseCNN:
    def __init__(self, nb_epochs, batch_size, learning_rate, eps = 0.3, clip_min=0, clip_max=1):
        self.train_params = {
            'nb_epochs': nb_epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate
        }
        self.eval_params = {'batch_size': batch_size}
        self.fgsm_params = {
            'eps': eps,
            'clip_min': clip_min,
            'clip_max': clip_max
        }

        self.x_train = None
        self.y_train = None
        self.x_test = None
        self.y_test = None
        self.range = np.random.RandomState([2019, 11, 25])
        self.model = None
        self.preds = None
        self.loss = None
        self.img_rows = None
        self.img_cols = None
        self.nchannels = None
        self.nb_classes = None
        self.preds_adv = None

    def get_data(self, train_start, train_end, test_start, test_end):
        mnist = MNIST(train_start=train_start, train_end=train_end,
                      test_start=test_start, test_end=test_end)
        self.x_train, self.y_train = mnist.get_set('train')
        self.x_test, self.y_test = mnist.get_set('test')
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]
        self.nb_classes = self.y_train.shape[1]

    def adverse_train(self, nb_filters, label_smoothing):
        self.model = ModelBasicCNN('model2', self.nb_classes, nb_filters)
        fgsm = FastGradientMethod(self.model, sess=sess)

        def attack(x):
            return fgsm.generate(x, **self.fgsm_params)

        self.preds = self.model.get_logits(x)
        self.loss = CrossEntropy(self.model, smoothing=label_smoothing, attack=attack)

        adv_x = attack(x)
        self.preds_adv = self.model.get_logits(adv_x)

        train(sess, self.loss, self.x_train, self.y_train, evaluate=self.evaluate,
              args=self.train_params, rng=self.range, var_list=self.model.get_params())

    def evaluate(self):
        do_eval(self.preds, self.eval_params, self.x_test, self.y_test, 'adv_train_clean_eval', False)
        do_eval(self.preds_adv, self.eval_params, self.x_test, self.y_test, 'adv_train_adv_eval', True)

    def test(self):
        do_eval(self.preds, self.eval_params, self.x_train, self.y_train, 'train_adv_train_clean_eval')
        do_eval(self.preds_adv, self.eval_params, self.x_train, self.y_train, 'train_adv_train_adv_eval')


if __name__ == '__main__':

    
    nb_epochs = 6
    batch_size = 128
    learning_rate = 0.001
    train_start = 0
    train_end = 60000
    test_start = 0
    test_end = 10000
    label_smoothing = 0.1
    nb_filters = 64

    cnnobj = CleanCNN(nb_epochs, batch_size, learning_rate)
    cnnobj.get_data(train_start, train_end, test_start, test_end)
    initialize_tensorflow(cnnobj.img_rows, cnnobj.img_cols, cnnobj.nchannels, cnnobj.nb_classes)
    cnnobj.train(nb_filters, label_smoothing)
    cnnobj.test()

    cnnobj.adverserial_testing()
    print('Repeating the process, using adversarial training')

    advcnnobj = AdverseCNN(nb_epochs, batch_size, learning_rate)
    advcnnobj.get_data(train_start, train_end, test_start, test_end)
    advcnnobj.adverse_train(nb_filters, label_smoothing)
    advcnnobj.test()

    print(report)