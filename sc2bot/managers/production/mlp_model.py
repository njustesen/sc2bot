'''
This is Niels' code, interpreted and adapted.
'''

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
import numpy as np


class Net(nn.Module):
    '''
    This class creates a neural network using pytorch. It takes the
    amount of hidden layers, hidden nodes, the amount of inputs and 
    outputs.
    '''
    def __init__(self, inputs, hidden_nodes, hidden_layers, outputs, dropout=0.0):
        super(Net, self).__init__()
        self.hidden = nn.ModuleList()
        if hidden_layers == 0:
            self.output = nn.Linear(inputs, outputs)
        else:
            for h in range(hidden_layers):
                self.hidden.append(nn.Linear(inputs if h==0 else hidden_nodes, hidden_nodes))
            self.dropout = nn.Dropout(p=dropout)
            self.output = nn.Linear(hidden_nodes, outputs)
        
    def forward(self, x):
        for layer in self.hidden:
            x = F.relu(layer(x))
            x = self.dropout(x)
        return F.log_softmax(self.output(x), dim=1)


def train(args, model, device, train_loader, optimizer, epoch):
    model.train()
    ls = []
    correct = 0
    accumulator = 0
    for _, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        accumulator += data.shape[0]
        optimizer.zero_grad()
        output = model(data)
        pred = output.max(1, keepdim=True)[1] # get the index of the max log-probability
        correct += pred.eq(target.view_as(pred)).sum().item()
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        ls.append(loss.item())
    print(f"total amount of data processed: {accumulator}")
    acc = 100. * correct / len(train_loader.dataset)
    print('Train Epoch: {} [{}/{} ({:.4f}%)]\tLoss: {:.6f}'.format(
            epoch, correct, len(train_loader.dataset),
            acc, loss.item()))
    return np.mean(ls), np.mean(acc)


def accuracy(output, target, topk):
    _, pred = output.topk(topk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))
    correct_k = correct[:topk].view(-1).float().sum(0, keepdim=True)    
    return correct_k.item()


def test(args, model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    correct3 = 0
    correct10 = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction='sum').item() # sum up batch loss
            pred = output.max(1, keepdim=True)[1] # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()
            correct3 += accuracy(output, target, topk=3)
            correct10 += accuracy(output, target, topk=10)
            
    test_loss /= len(test_loader.dataset)
    top1 = 100. * correct / len(test_loader.dataset)
    top3 = 100. * correct3 / len(test_loader.dataset)
    top10 = 100. * correct10 / len(test_loader.dataset)
    print('Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.2f}%)'.format(
        test_loss, correct, len(test_loader.dataset), top1))
    print('Top 3 {:.3f} \t Top 10 {:.3f}'.format(top3, top10))
    return test_loss, 100. * correct / len(test_loader.dataset), top3, top10
