# -*- coding: utf-8 -*-
"""FSGM-emnist.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1DdOBXUFef44Nr7A3g8CYAaNYJEFiMq9x
"""

!ls drive/"My Drive"/
!pip install git+https://github.com/tensorflow/cleverhans.git#egg=cleverhans
!pip install emnist

from emnist import extract_test_samples
from emnist import extract_training_samples

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

    '''
    def get_data(self, train_start, train_end, test_start, test_end):
        train = np.genfromtxt("drive/My Drive/train.csv", delimiter=',')
        test = np.genfromtxt("drive/My Drive/test.csv", delimiter=',')
        self.x_test = test[:,1:].astype(int)
        self.y_test = oneHotEncodeY(test[:,0].astype(int),47)
        self.x_train = train[:,1:].astype(int)
        
        self.y_train = oneHotEncodeY(train[:,0].astype(int),47)

        self.x_train = np.reshape(self.x_train,(self.x_train.shape[0], 28, 28, 1))
        self.x_test = np.reshape(self.x_test,(self.x_test.shape[0], 28, 28, 1))
        print(self.x_train.shape, self.y_train.shape, self.x_test.shape, self.y_test.shape)
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]
        self.nb_classes = self.y_train.shape[1]

        
        mnist = MNIST(train_start=train_start, train_end=train_end,
                      test_start=test_start, test_end=test_end)
        self.x_train, self.y_train = mnist.get_set('train')
        self.x_test, self.y_test = mnist.get_set('test')
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]
        self.nb_classes = self.y_train.shape[1]
        '''

    def get_data(self):
        self.x_train, self.y_train = extract_training_samples('byclass')
        self.x_test, self.y_test = extract_test_samples('byclass')
        self.y_test = oneHotEncodeY(self.y_test, 62)
        self.y_train = oneHotEncodeY(self.y_train, 62)
        self.x_train = self.x_train.astype('float32')
        self.y_train = self.y_train.astype('float32')
        self.x_test = self.x_test.astype('float32')
        self.y_test = self.y_test.astype('float32')
        #print(np.amax(self.y_train))
        #print(self.x_train.shape, self.y_train.shape, self.x_test.shape, self.y_test.shape)
        
        self.x_train = self.x_train /255.
        self.y_train = self.y_train
        self.x_test = self.x_test/ 255.
        self.y_test = self.y_test
        
        self.x_train = np.reshape(self.x_train,(self.x_train.shape[0], 28, 28, 1))
        self.x_test = np.reshape(self.x_test,(self.x_test.shape[0], 28, 28, 1))
        #self.y_test = np.reshape(self.y_test,(self.y_test.shape[0],1))
        #self.y_train = np.reshape(self.y_train,(self.y_train.shape[0],1))
        
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]

        
        #images = np.reshape(images,(images.shape[0], 28, 28, 1))
        #self.x_train, self.y_train = mnist.get_set('train')
        #self.x_test, self.y_test = mnist.get_set('test')
        
        #print(type(images))
        #print(images.shape[1:4])
        #print(labels.shape)
        #print(images.shape)
        '''
        self.x_train, self.y_train = mnist.get_set('train')
        self.x_test, self.y_test = mnist.get_set('test')
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]
        self.nb_classes = self.y_train.shape[1]
        print(np.amax(self.y_train))
        '''
        self.nb_classes = 62
        #self.x_sub = self.x_test[:s0]
        #self.y_sub = np.argmax(self.y_test[:s0], axis=1)

        #self.x_test = self.x_test[s0:]
        #self.y_test = self.y_test[s0:]

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

    def get_data(self):
        self.x_train, self.y_train = extract_training_samples('byclass')
        self.x_test, self.y_test = extract_test_samples('byclass')
        self.y_test = oneHotEncodeY(self.y_test, 62)
        self.y_train = oneHotEncodeY(self.y_train, 62)
        self.x_train = self.x_train.astype('float32')
        self.y_train = self.y_train.astype('float32')
        self.x_test = self.x_test.astype('float32')
        self.y_test = self.y_test.astype('float32')
        print(np.amax(self.y_train))
        print(self.x_train.shape, self.y_train.shape, self.x_test.shape, self.y_test.shape)
        
        self.x_train = self.x_train /255.
        self.y_train = self.y_train
        self.x_test = self.x_test/ 255.
        self.y_test = self.y_test
        
        self.x_train = np.reshape(self.x_train,(self.x_train.shape[0], 28, 28, 1))
        self.x_test = np.reshape(self.x_test,(self.x_test.shape[0], 28, 28, 1))
        #self.y_test = np.reshape(self.y_test,(self.y_test.shape[0],1))
        #self.y_train = np.reshape(self.y_train,(self.y_train.shape[0],1))
        
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]

        
        #images = np.reshape(images,(images.shape[0], 28, 28, 1))
        #self.x_train, self.y_train = mnist.get_set('train')
        #self.x_test, self.y_test = mnist.get_set('test')
        
        print("//////////////////////////////")
        #print(type(images))
        #print(images.shape[1:4])
        #print(labels.shape)
        #print(images.shape)
        '''
        self.x_train, self.y_train = mnist.get_set('train')
        self.x_test, self.y_test = mnist.get_set('test')
        self.img_rows, self.img_cols, self.nchannels = self.x_train.shape[1:4]
        self.nb_classes = self.y_train.shape[1]
        print(np.amax(self.y_train))
        '''
        self.nb_classes = 62
        #self.x_sub = self.x_test[:s0]
        #self.y_sub = np.argmax(self.y_test[:s0], axis=1)

        #self.x_test = self.x_test[s0:]
        #self.y_test = self.y_test[s0:]

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
    label_smoothing = 0.1
    nb_filters = 64

    cnnobj = CleanCNN(nb_epochs, batch_size, learning_rate)
    cnnobj.get_data()
    initialize_tensorflow(cnnobj.img_rows, cnnobj.img_cols, cnnobj.nchannels, cnnobj.nb_classes)
    cnnobj.train(nb_filters, label_smoothing)
    cnnobj.test()

    cnnobj.adverserial_testing()
    print('Repeating the process, using adversarial training')

    advcnnobj = AdverseCNN(nb_epochs, batch_size, learning_rate)
    advcnnobj.get_data()
    advcnnobj.adverse_train(nb_filters, label_smoothing)
    advcnnobj.test()

    print(report)