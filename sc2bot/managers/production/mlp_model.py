'''
This is Niels' code, interpreted and adapted. In it, the network topologies are defined.
'''

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np

class Net2(nn.Module):
    '''
    This class creates a neural network using pytorch. It takes the
    amount of hidden layers, hidden nodes, the amount of inputs and
    outputs.
    '''
    def __init__(self, inputs, h_nodes_obs, h_layers_obs, outputs, dropout=0.0, h_nodes_f=256, h_layers_f=2, outputs_obs=256//2, outputs_f=256//2):
        super(Net2, self).__init__()

        self.outputs_f = outputs_f
        self.outputs_obs = outputs_obs
        self.hidden_obs = nn.ModuleList()
        if h_layers_obs == 0:
            self.output = nn.Linear(inputs, outputs)
        else:
            for h in range(h_layers_obs):
                self.hidden_obs.append(nn.Linear(inputs if h==0 else h_nodes_obs, h_nodes_obs))
            self.output_obs = nn.Linear(h_nodes_obs, outputs_obs)

        self.expanding_layer = nn.Linear(2, outputs_f)

        self.hidden_f = nn.ModuleList()
        for h in range(h_layers_f):
            self.hidden_f.append(nn.Linear(outputs_obs+outputs_f if h==0 else h_nodes_f, h_nodes_f))


        self.dropout = nn.Dropout(p=dropout)
        self.output = nn.Linear(h_nodes_f, outputs)

    def forward(self, x):
        x_obs = x[:, :-2]
        x_feat = x[:,-2:]

        # Processing the observation stuff
        for layer in self.hidden_obs:
            x_obs = F.relu(layer(x_obs))
            x_obs = self.dropout(x_obs)
        x_obs = self.output_obs(x_obs)

        # Expanding the features
        # TODO: ask myself if this makes sense.
        x_feat = self.expanding_layer(x_feat)

        # Joining with features and processing
        x = torch.cat((x_obs, x_feat), 1) #pylint: disable=no-member
        for layer in self.hidden_f:
            x = F.relu(layer(x))
            x = self.dropout(x)

        # Outputing.
        return F.log_softmax(self.output(x), dim=1)

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
