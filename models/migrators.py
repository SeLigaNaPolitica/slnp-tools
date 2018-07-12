'''This scripts converts legacy uris into current ones

    Date: May 31, 2018

    Author: Guilherme Varela

Some uris are converted from md5 format to uuid4

Converts:

    * Agents
    * Formal education
    * Organization (Parties)

Removes instances from:

    * Membership
    * Post

'''
import os
import re
import glob
import pandas as pd
import json
import sys
import errno

from numpy import nan

from scripts import person_uri, formaleducation_uri
from uuid import uuid4

BASE_URI = 'http://www.seliganapolitica.org/resource/'
MAPPINGS_DIR = 'common/mappings/'

CONGRESSMEN_DIR = 'camara_deputados/deputados/'
CONGRESSMEN_DATASETS_DIR = '{:}datasets/'.format(CONGRESSMEN_DIR)
TURTLE_SOURCE_DIR = '{:}turtle/inputs/'.format(CONGRESSMEN_DIR)
TURTLE_TARGET_DIR = '{:}turtle/outputs/'.format(CONGRESSMEN_DIR)
AGENTS_DIR = 'agents/'


class TurtleMigrator(object):
    '''
        Provides migration utilities in order to convert previous 
            migration schemes into new objects
    '''

    def __init__(self):
        self._initialize_agents()
        self._initialize_formaleducation()
        self._initialize_parties()

    def migrate(self, input_dir):
        '''
            Migrates file
                * Replace uris for the following resources:
                    * Person
                    * Organization

                * Remove all lines which have uris for resources:
                    * Membership
                    * Post

            To do:
                * Add instances ttl lines for resources:
                    * Membership
                    * Post
        '''
        input_glob = glob.glob('{:}*txt'.format(input_dir))
        output_dir = TURTLE_TARGET_DIR
        for txtfile in input_glob:
            filename = txtfile.split('/')[-1]
            print('processing .. {:}'.format(filename))

            with open(txtfile, mode='r') as f:
                txt = f.read()
            f.close()

            # REPLACE URI's
            for _, old_newidx in self.agents_dict.items():
                txt = txt.replace(*old_newidx)

            for _, old_newidx in self.educ_dict.items():
                txt = txt.replace(*old_newidx)

            for _, old_newidx in self.parties_dict.items():
                olduri, newuri = old_newidx
                newuri = '{:}{:}'.format(BASE_URI, newuri)
                txt = txt.replace(olduri, newuri)

            # REMOVE URI's from POST
            re_resource = re.compile('.*(http:\/\/www.seliganapolitica.org\/resource\/[a-f0-9]{32}).*')

            line_list = txt.split('\n')
            filter_list = [line
                           for line in line_list if re_resource.match(line) is None]

            re_congressmen = re.compile('.*(https:\/\/dadosabertos.camara.leg.br\/api\/v2\/deputados\/[0-9]*).*')
            filter_list = [line
                           for line in filter_list if re_congressmen.match(line) is None]
            filter_txt = '\n'.join(filter_list)
            if not os.path.exists(os.path.dirname(output_dir)):
                try:
                    os.makedirs(os.path.dirname(output_dir))
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

        output_path = '{:}{:}'.format(output_dir, filename)
        with open(output_path, mode='w') as f:
            f.write(filter_txt)
        f.close()
        print('saved at ', output_path)

    def _initialize_agents(self):
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

        agents_dict.update(self._initialize_agents_fromtable())


        name_tags = '<nomeCivil>(.*?)</nomeCivil>'
        name_finder = lambda x : re.findall(name_tags, x)

        birthday_tags = '<dataNascimento>(.*?)</dataNascimento>'
        birthday_finder = lambda x : re.findall(birthday_tags, x)

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

        self.agents_dict = agents_dict

    def _initialize_agents_fromtable(self):
        agents_path = '{:}agents.csv'.format(AGENTS_DIR)
        _df = pd.read_csv(agents_path, sep=';', encoding='utf-8', index_col=0)
        print(_df.columns)
        _df = _df[['cam:nomeCivil', 'cam:dataNascimento']]


        _fullname = _df['cam:nomeCivil'].to_dict()
        _birthdate = _df['cam:dataNascimento'].to_dict()

        agents_dict = {
            (_fullname[idx], _birthdate[idx]): (person_uri(_fullname[idx], _birthdate[idx]), idx)
            for idx in _fullname  if _fullname[idx] and isinstance(_fullname [idx], str)
        }
        return agents_dict


    def _initialize_formaleducation(self):
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
                self.educ_dict = self._initialize_formaleducation()
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

        self.educ_dict = educ_dict


    def _initialize_parties(self):
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

        self.parties_dict = parties_dict



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

def make_post_camara_mapping_dict():
    pass

def make_post_camara_mapping_dict():
    pass

def make_post_membership_party_mapping_dict():
    pass


if __name__ == '__main__':
    TurtleMigrator().migrate(TURTLE_SOURCE_DIR)
