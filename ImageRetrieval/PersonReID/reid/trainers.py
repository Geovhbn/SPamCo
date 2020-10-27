from __future__ import print_function, absolute_import
import time

import torch
from torch.autograd import Variable

from .evaluation_metrics import accuracy
from .loss import OIMLoss, TripletLoss, SoftCrossEntropyLoss
from .utils.meters import AverageMeter


class BaseTrainer(object):
    def __init__(self, model, criterion, device):
        super(BaseTrainer, self).__init__()
        self.model = model
        self.criterion = criterion
        self.device=device

    def train(self, epoch, data_loader, optimizer, print_freq=1):
        self.model.train()

        batch_time = AverageMeter()
        data_time = AverageMeter()
        losses = AverageMeter()
        precisions = AverageMeter()

        end = time.time()
        for i, inputs in enumerate(data_loader):
            data_time.update(time.time() - end)

            inputs, targets, weights = self._parse_data(inputs)
            loss, prec1 = self._forward(inputs, targets, weights)

            #  import pdb; pdb.set_trace()
            losses.update(loss.item(), targets.size(0))
            precisions.update(prec1, targets.size(0))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            batch_time.update(time.time() - end)
            end = time.time()

            if (i + 1) % print_freq == 0 and epoch % 5 == 0:
                print('Epoch: [{}][{}/{}]\t'
                      'Time {:.3f} ({:.3f})\t'
                      'Data {:.3f} ({:.3f})\t'
                      'Loss {:.3f} ({:.3f})\t'
                      'Prec {:.2%} ({:.2%})\t'
                      .format(epoch, i + 1, len(data_loader),
                              batch_time.val, batch_time.avg,
                              data_time.val, data_time.avg,
                              losses.val, losses.avg,
                              precisions.val, precisions.avg))

    def _parse_data(self, inputs):
        raise NotImplementedError

    def _forward(self, inputs, targets):
        raise NotImplementedError

    def update_criterion(self, criterion):
        self.criterion = criterion


class Trainer(BaseTrainer):
    def _parse_data(self, inputs):
        imgs, _, pids, _, weights = inputs
        inputs = [Variable(imgs).to(self.device)]
        targets = Variable(pids.to(self.device))
        weights = Variable(weights.float().to(self.device))
        return inputs, targets, weights

    def _forward(self, inputs, targets, weights=None):
        outputs = self.model(*inputs)
        if isinstance(self.criterion, torch.nn.CrossEntropyLoss):
            loss = self.criterion(outputs, targets)
            prec, = accuracy(outputs.data, targets.data)
            prec = prec[0]
        elif isinstance(self.criterion, OIMLoss):
            loss, outputs = self.criterion(outputs, targets)
            prec, = accuracy(outputs.data, targets.data)
            prec = prec[0]
        elif isinstance(self.criterion, TripletLoss):
            loss, prec = self.criterion(outputs, targets)
        elif isinstance(self.criterion, SoftCrossEntropyLoss):
            loss = self.criterion(outputs, targets, weights)
            prec, = accuracy(outputs.data, targets.data)
            prec = prec[0]
        else:
            raise ValueError("Unsupported loss:", self.criterion)
        return loss, prec
