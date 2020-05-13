import argparse
import os
import time
import numpy as np
import torch
from . import util

class Options():
    def __init__(self):
        self.parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        self.initialized = False

    def initialize(self):
        #base
        self.parser.add_argument('--gpu_id', type=int, default=0,help='choose which gpu want to use, 0 | 1 | 2 ...')        
        self.parser.add_argument('--no_cudnn', action='store_true', help='if specified, do not use cudnn')
        self.parser.add_argument('--label', type=str, default='auto',help='number of labels')
        self.parser.add_argument('--input_nc', type=str, default='auto', help='of input channels')
        self.parser.add_argument('--finesize', type=str, default='auto', help='crop your data into this size')
        self.parser.add_argument('--label_name', type=str, default='auto',help='name of labels,example:"a,b,c,d,e,f"')
        self.parser.add_argument('--model_name', type=str, default='micro_multi_scale_resnet_1d',help='Choose model  lstm | multi_scale_resnet_1d | resnet18 | micro_multi_scale_resnet_1d...')
        # ------------
        # for lstm 
        self.parser.add_argument('--input_size', type=str, default='auto',help='input_size of LSTM')
        self.parser.add_argument('--time_step', type=int, default=100,help='time_step of LSTM')
        # for autoencoder
        self.parser.add_argument('--feature', type=int, default=3, help='number of encoder features')
        # ------------
        self.parser.add_argument('--pretrained', action='store_true', help='if specified, use pretrained models')
        self.parser.add_argument('--continue_train', action='store_true', help='if specified, continue train')
        self.parser.add_argument('--lr', type=float, default=0.001,help='learning rate') 
        self.parser.add_argument('--batchsize', type=int, default=64,help='batchsize')
        self.parser.add_argument('--weight_mod', type=str, default='auto',help='Choose weight mode: auto | normal')
        self.parser.add_argument('--epochs', type=int, default=20,help='end epoch')
        self.parser.add_argument('--network_save_freq', type=int, default=5,help='the freq to save network')
        self.parser.add_argument('--k_fold', type=int, default=0,help='fold_num of k-fold.if 0 or 1,no k-fold')
        self.parser.add_argument('--mergelabel', type=str, default='None',
            help='merge some labels to one label and give the result, example:"[[0,1,4],[2,3,5]]" , label(0,1,4) regard as 0,label(2,3,5) regard as 1')
        self.parser.add_argument('--mergelabel_name', type=str, default='None',help='name of labels,example:"a,b,c,d,e,f"')
        self.parser.add_argument('--plotfreq', type=int, default=100,help='frequency of plotting results')

        self.parser.add_argument('--dataset_dir', type=str, default='./datasets/sleep-edfx/',
                                help='your dataset path')
        self.parser.add_argument('--save_dir', type=str, default='./checkpoints/',help='save checkpoints')
        self.parser.add_argument('--dataset_name', type=str, default='preload',
            help='Choose dataset preload | sleep-edfx | cc2018  ,preload:your data->shape:(num,ch,length), sleep-edfx&cc2018:sleep stage')
        self.parser.add_argument('--separated', action='store_true', help='if specified,for preload data, if input, load separated train and test datasets')
        self.parser.add_argument('--no_shuffle', action='store_true', help='if specified,do not shuffle data when load(use to evaluate individual differences)')

        #for EEG datasets  
        self.parser.add_argument('--BID', type=str, default='5_95_th',help='Balance individualized differences  5_95_th | median |None')
        self.parser.add_argument('--select_sleep_time', action='store_true', help='if specified, for sleep-cassette only use sleep time to train')
        self.parser.add_argument('--signal_name', type=str, default='EEG Fpz-Cz',help='Choose the EEG channel C4-M1 | EEG Fpz-Cz |...')
        self.parser.add_argument('--sample_num', type=int, default=20,help='the amount you want to load')
        
        self.initialized = True

    def getparse(self):
        if not self.initialized:
            self.initialize()
        self.opt = self.parser.parse_args()

        if self.opt.label !='auto':
            self.opt.label = int(self.opt.label)
        if self.opt.input_nc !='auto':
            self.opt.input_nc = int(self.opt.input_nc)
        if self.opt.finesize !='auto':
            self.opt.finesize = int(self.opt.finesize)
        if self.opt.input_size !='auto':
            self.opt.input_size = int(self.opt.input_size)

        if self.opt.dataset_name == 'sleep-edf':
            self.opt.sample_num = 8
        if self.opt.dataset_name not in ['sleep-edf','sleep-edfx','cc2018']:
            self.opt.BID = 'not-supported'
            self.opt.select_sleep_time = 'not-supported'
            self.opt.signal_name = 'not-supported'
            self.opt.sample_num = 'not-supported'

        if self.opt.k_fold == 0 :
            self.opt.k_fold = 1

        self.opt.mergelabel = eval(self.opt.mergelabel)
        if self.opt.mergelabel_name != 'None':
            self.opt.mergelabel_name = self.opt.mergelabel_name.replace(" ", "").split(",")

        """Print and save options
        It will print both current options and default values(if different).
        It will save options into a text file / [checkpoints_dir] / opt.txt
        """
        message = ''
        message += '----------------- Options ---------------\n'
        for k, v in sorted(vars(self.opt).items()):
            comment = ''
            default = self.parser.get_default(k)
            if v != default:
                comment = '\t[default: %s]' % str(default)
            message += '{:>20}: {:<30}{}\n'.format(str(k), str(v), comment)
        message += '----------------- End -------------------'
        localtime = time.asctime(time.localtime(time.time()))
        util.makedirs(self.opt.save_dir)
        util.writelog(str(localtime)+'\n'+message, self.opt,True)

        return self.opt

def get_auto_options(opt,label_cnt_per,label_num,shape):
    
    if opt.label =='auto':
        opt.label = label_num
    if opt.input_nc =='auto':
        opt.input_nc = shape[1]
    if opt.finesize =='auto':
        opt.finesize = int(shape[2]*0.9)
    if opt.input_size =='auto':
        opt.input_size = opt.finesize//opt.time_step

    # weight
    opt.weight = np.ones(opt.label)
    if opt.weight_mod == 'auto':
        opt.weight = 1/label_cnt_per
        opt.weight = opt.weight/np.min(opt.weight)
    util.writelog('Loss_weight:'+str(opt.weight),opt,True)
    opt.weight = torch.from_numpy(opt.weight).float()
    if opt.gpu_id != -1:      
        opt.weight = opt.weight.cuda()

    # label name
    if opt.label_name == 'auto':
        if opt.dataset_name in ['sleep-edf','sleep-edfx','cc2018']:
            opt.label_name = ["N3", "N2", "N1", "REM","W"]
        else:
            names = []
            for i in range(opt.label):
                names.append(str(i))
            opt.label_name = names
    else:
        opt.label_name = opt.label_name.replace(" ", "").split(",")
    
    return opt