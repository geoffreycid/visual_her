import os
import sys
import json
from itertools import product


def wrapper(dict_env, dict_agent, dict_expert, grid_search, extension):
    """
    - Create & check files and folders
    - Call the training procedure
    """
    # Update the agent with the extension
    dict_agent.update(extension)

    # Path to the env and the agent directories
    if not os.path.exists(dict_env["env_dir"]):
        os.makedirs(dict_env["env_dir"])
    env_dir = dict_env["env_dir"] + "/" + dict_env["name"]
    agent_dir = env_dir + "/" + dict_agent["name"] + "-" + dict_expert["name"]
    # Check if the experience has already been done
    # Make the needed folders
    if os.path.exists(env_dir):
        with open(env_dir + '/' + dict_env["name"] + '.json', 'r') as myfile:
            already_here_env = myfile.read()
        dict_already_here_env = json.loads(already_here_env)
        if dict_env["size"] != dict_already_here_env["size"] \
                or dict_env["manual"] != dict_already_here_env["manual"] \
                or dict_env["random_target"] != dict_already_here_env["random_target"] \
                or dict_env["numObjs"] != dict_already_here_env["numObjs"] \
                or dict_env["COLOR_TO_IDX"] != dict_already_here_env["COLOR_TO_IDX"] \
                or dict_env["TYPE_TO_IDX"] != dict_already_here_env["TYPE_TO_IDX"] \
                or dict_env["oneobject"] != dict_already_here_env["oneobject"] \
                or dict_env["TYPE_TO_IDX"] != dict_already_here_env["TYPE_TO_IDX"]:
            print("Try to override an existing env without the same parameters")
            sys.exit()
        name_agent = dict_agent["name"] + "-" + dict_expert["name"]

        if name_agent not in os.listdir(env_dir):
            os.mkdir(agent_dir)
        else:
            for seed in dict_agent["seed"]:
                if "run_{}".format(seed) in os.listdir(agent_dir):
                    print("Environment & Agent & run names already used")
                    sys.exit()
    else:
        os.makedirs(agent_dir)
        
    # Duplicate configuration files into model_dir and agent_dir
    with open(env_dir + "/" + dict_env["name"] + ".json", 'w') as outfile:
        json.dump(dict_env, outfile)
    
    with open(agent_dir + '/{}.json'.format(dict_agent["name"]), 'w') as outfile:
        json.dump(dict_agent, outfile)

    with open(agent_dir + '/gridsearch.json', 'w') as outfile:
        json.dump(grid_search, outfile)

    with open(agent_dir + '/expert.json', 'w') as outfile:
        json.dump(dict_expert, outfile)

    dict_agent["agent_dir"] = agent_dir

    def cleanstr(string):
        string = string.replace("{", "")
        string = string.replace("}", "")
        string = string.replace(":", "_")
        string = string.replace("'", "")
        string = string.replace(" ", "")
        string = string.replace(",", "_")
        return string

    # Grid search
    if len(grid_search.items()) > 0:
        dicts = []
        items = sorted(grid_search.items())
        keys, values = zip(*items)
        for ind, seed in enumerate(dict_agent["seed"]):
            for val in product(*values):
                d = dict_agent.copy()
                d.update(dict(zip(keys, val)))
                d["seed"] = seed
                d["agent_dir"] = dict_agent["agent_dir"] + "/run_{}".format(seed) + "/{}".format(cleanstr(str(dict(zip(keys, val)))))
                os.makedirs(d["agent_dir"])
                dicts.append(d)

        return dict_agent, dicts
    else:
        dicts = []
        for ind, seed in enumerate(dict_agent["seed"]):
            d = dict_agent.copy()
            d["seed"] = seed
            d["agent_dir"] = dict_agent["agent_dir"] + "/run_{}".format(seed) + "/a"
            os.makedirs(d["agent_dir"])
            dicts.append(d)
        return dict_agent, dicts
