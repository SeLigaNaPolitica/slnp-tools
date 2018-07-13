'''Mapping functions to convert from MD5 style to uuid4

    Date: May 31, 2018

    Author: Guilherme Varela
'''
import os
import json
import re
import glob

import pandas as pd

from .uri_generators import person_uri, formaleducation_uri
from uuid import uuid4

MAPPINGS_DIR = 'common/mappings/'
AGENTS_DIR = 'common/agents/'

CONGRESSMEN_DIR = 'camara_deputados/deputados/'
CONGRESSMEN_RAW_DIR = '{:}/raw/'.format(CONGRESSMEN_DIR)

def get_agents_mapping():
    '''
        Computes an dictionary olduri --> newuri
    '''
    agents_path = '{:}agents.json'.format(MAPPINGS_DIR)
    if os.path.isfile(agents_path):
        with open(agents_path, mode='r') as f:
            agents_dict = dict_list2dict(json.load(f))
        f.close()
    else:
        agents_dict = {}

    agents_dict.update(_get_agents_fromtable())

    name_tags = '<nomeCivil>(.*?)</nomeCivil>'
    def name_finder(x):
        return re.findall(name_tags, x)

    birthday_tags = '<dataNascimento>(.*?)</dataNascimento>'
    def birthday_finder(x):
        return re.findall(birthday_tags, x)

    agent_list = []
    for g in glob.glob('datasets/migrations/xml/*'):
        with open(g, mode='r') as f:
            contents = f.read()
        f.close()

        names_list = name_finder(contents)
        birthdates_list = birthday_finder(contents)
        if len(names_list) != len(birthdates_list):
            raise ValueError('names and birthdates must match')
        else:
            agent_list += zip(names_list, birthdates_list)

    new_agents_dict = {agent_tuple: (person_uri(*agent_tuple), str(uuid4()))
                        for agent_tuple in agent_list if agent_tuple not in agents_dict}
    agents_dict.update(new_agents_dict)

    with open(agents_path, mode='w') as f:
        json.dump(dict2dict_list(agents_dict), f)
    f.close()

    return agents_dict

def _get_agents_fromtable():
    agents_path = '{:}agents.csv'.format(AGENTS_DIR)
    _df = pd.read_csv(agents_path, sep=';', encoding='utf-8', index_col=0)
    _df = _df[['cam:nomeCivil', 'cam:dataNascimento']]


    _fullname = _df['cam:nomeCivil'].to_dict()
    _birthdate = _df['cam:dataNascimento'].to_dict()

    agents_dict = {
        (_fullname[idx], _birthdate[idx]): (person_uri(_fullname[idx], _birthdate[idx]), idx)
        for idx in _fullname  if _fullname[idx] and isinstance(_fullname [idx], str)
    }
    return agents_dict


def get_education_mapping():
    '''
        Computes an dictionary olduri --> newuri
        args:
        returns:
            formaleducation .: dict<str, list<str>>
                                keys  .: str presenting a educational formation
                                values        .: list of two items
                                    value[0]  .:  str md5() for resource
                                    value[1]  .:  str uuid4() for resource

        usage:
            self.educ_dict = self.get_education_mapping()
            {'Superior': ['2f615aa52f420810e559590a4cfbfafd', '01e502af-2208-4184-87db-c7162e14e60e']}
    '''
    formaleducation_path = '{:}formaleducation.json'.format(MAPPINGS_DIR)
    if os.path.isfile(formaleducation_path):
        with open(formaleducation_path, mode='r') as f:
            educ_dict = json.load(f)
        f.close()
    else:
        educ_dict = {}

    tags = '<escolaridade>(.*?)</escolaridade>'
    finder = lambda x : re.findall(tags, x)
    educ_set = set()
    for g in glob.glob('datasets/migrations/xml/*'):
        with open(g, mode='r') as f:
            contents = f.read()
        f.close()
        educ_set = set(finder(contents)).union(educ_set)

    educ_list = list(educ_set)
    for i in educ_list:
        if not i in educ_dict:
            # http://www.seliganapolitica.org/resource/skos/Formacao#
            olduri = re.sub('http://www.seliganapolitica.org/resource/skos/Formacao#','',formaleducation_uri(i))
            educ_dict[i] = (olduri, str(uuid4()))

    with open(formaleducation_path, mode='w') as f:
        json.dump(educ_dict, f)
    f.close()

    return educ_dict


def get_parties_mapping():
    '''[summary]

    Computes a new party attribute list
    '''    
    parties_path = '{:}parties.json'.format(MAPPINGS_DIR)
    if not os.path.isfile(parties_path):
        parties_dict = make_party_mapping_dict()
        with open(parties_path, mode='w') as f:
            json.dump(parties_dict, f)
        f.close()

    else:
        with open(parties_path, mode='r') as f:
            parties_dict = json.load(f)
        f.close()

    return parties_dict


def dict2dict_list(map_dict):
    '''
        Converts the mapping into a key, value list of dictionaries
        used to convert dicts having tuples as key to dict
        returns:
            dict_list
    '''
    return [{'key': key, 'value': values} for key, values in map_dict.items()]


def dict_list2dict(dict_list):
    '''
        Converts an array of dictionaries into lists
        returns:
            dict
    '''
    return {tuple(item_dict['key']):item_dict['value'] for item_dict in dict_list}


def make_party_mapping_dict():
    '''Computes party_mapping_dict

        keys will be `sigla` field
        values list of values
    '''
    organizations_path = 'datasets/slnp/organizations.csv'
    df = pd.read_csv(organizations_path, sep=';', index_col=0)

    parties_path = 'datasets/camara/v2/partidos.json'
    with open(parties_path, mode='r') as f:
        parties_list = json.load(f)

    party_mapping_dict = {}
    for dict_ in parties_list:
        rec_ = df[df.loc[:,'sigla'] == dict_['sigla']]
        if rec_.shape[0] == 0:
            raise KeyError('Sigla {:} not found on file organizations.csv. Update organizations.csv!'.format(dict_['sigla']))
        else:
            party_mapping_dict[dict_['sigla']] = (dict_['uri'], rec_.index[0])
    return party_mapping_dict    