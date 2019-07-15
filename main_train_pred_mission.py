import dill
import random
import torch
import models
import torch.nn.functional as F
import torch.nn as nn

import matplotlib.pyplot as plt
#dill.load_session("collect_samples_4_nc_1000.0_max_steps.pkl")


class AgentPredOneHot(nn.Module):
    def __init__(self, c, frames, n_mission, n_type, lr):
        """
        h: height of the screen
        w: width of the screen
        frames: last observations to make a state
        n_actions: number of actions
        """
        super(AgentPredOneHot, self).__init__()

        self.conv_net = nn.Sequential(
            nn.Conv2d(c * frames, 16, (2, 2)),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(16, 32, (2, 2)),
            nn.ReLU(),
            nn.Conv2d(32, 64, (2, 2)),
            nn.ReLU()
        )

        self.type_fc = nn.Sequential(
            nn.Linear(in_features=64, out_features=64),
            nn.ReLU(),
            nn.Linear(in_features=64, out_features=n_type)
        )

        self.color_fc = nn.Sequential(
            nn.Linear(in_features=64, out_features=64),
            nn.ReLU(),
            nn.Linear(in_features=64, out_features=n_mission)
        )

        self.optimizer = torch.optim.RMSprop(self.parameters(), lr=lr)

        self.criterion = nn.CrossEntropyLoss()

    def forward(self, state):
        out_conv = self.conv_net(state)
        flatten = out_conv.view(out_conv.shape[0], -1)

        return self.type_fc(flatten), self.color_fc(flatten)

    def prediction(self, state):
        with torch.no_grad():
            pred_type, pred_color = self.forward(state)
            return pred_type.max(1)[1], pred_color.max(1)[1]




with open('collect_samples_1_nc_1000000_memory_size_4_frames_new.pkl', 'rb') as file:
    mem = dill.load(file)

print("Memory loaded")
# Device to use
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

net = models.PredMissionNet(h=7, w=7, c=2, frames=1, lr_imc=1e-4,
                            dim_tokenizer=6, weight_decay=1e-6, device=device).to(device)

num_types = 2
num_colors = 4
# List of all possible missions
missions_type = F.one_hot(torch.arange(num_types))
missions_color = F.one_hot(torch.arange(num_colors))

all_possible_missions = []
for i in range(missions_type.shape[0]):
    for j in range(missions_color.shape[0]):
        all_possible_missions.append(torch.cat((missions_type[i], missions_color[j])))
all_possible_missions = torch.stack(all_possible_missions, dim=0).to(device).float()

#all_possible_missions = torch.eye(num_colors+num_types)[torch.arange(0, num_colors+num_types)]

random.shuffle(mem.memory)
train_memory = mem.memory[:998000]
test_memory = mem.memory[998000:]

n_epochs = 30
batch_size = 64
len_train = len(train_memory)
len_test = len(test_memory)

losses = []
test_accs = []

use_imc = 1
use_onehot = 0

# Training procedure

losses = []
test_accs = []

for _ in range(n_epochs):
    beg_ind = 0
    end_ind = batch_size
    for i in range(len_train//batch_size):
        imcs = train_memory[beg_ind:end_ind]

        batch_imcs = mem.imc(*zip(*imcs))
        batch_state = torch.cat(batch_imcs.state)
        # Keep only the last frame
        batch_state = batch_state[:, 6:]
        # For IMC only for onehot do not use batch mission
        batch_mission = torch.cat(batch_imcs.mission)
        batch_target = torch.cat(batch_imcs.target)

        if use_imc:
            batch_predictions = net.image_mission_correspondence(batch_state, batch_mission)

        if use_onehot:
            batch_predictions = net(batch_state)

        loss = net.criterion(batch_predictions, batch_target)
        if use_imc:
            net.optimizer_imc.zero_grad()
        elif use_onehot:
            net.optimizer.zero_grad()

        loss.backward()

        if use_imc:
            net.optimizer_imc.step()
        elif use_onehot:
            net.optimizer.step()

        beg_ind = end_ind
        end_ind += batch_size

        if i % 100 == 0:
            losses.append(float(loss))

    print("Start test time")
    acc = 0
    if use_imc:
        for imc in test_memory:
            state = imc.state[:, 6:]
            true_mission = torch.squeeze(imc.mission, dim=0)
            prediction_mission = net.find_best_mission(state, all_possible_missions)
            acc += torch.equal(prediction_mission, true_mission)
        acc /= len_test
        test_accs.append(acc)

    elif use_onehot:
        batch_imcs = mem.imc(*zip(*test_memory))
        batch_state = torch.cat(batch_imcs.state)
        # Keep only the last frame
        batch_state = batch_state[:, 6:]
        batch_target = torch.cat(batch_imcs.target)
        batch_predictions = net.prediction(batch_state)
    print("Accuracy: {}".format(acc))

plt.plot(losses)
plt.plot(test_accs)
plt.show()

