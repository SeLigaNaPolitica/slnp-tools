'''This module converts a CSV into json

Tabular data into json data
'''
from collections import defaultdict
from datetime import datetime
from random import sample
import json
import os

import pandas as pd

DATETIME_MASK = '%m-%d-%Y %H:%M'
DATE_MASK = '%m-%d-%Y'
BASE_URI = 'http://www.seliganapolitica.org/resource/'
DESCRIPTION_URI = 'https://github.com/SeLigaNaPolitica/slnp-tools/tree/develop/models/generators.py'
CONGRESSMAN_DESCRIPTION_URI = 'http://www2.camara.leg.br/transparencia/dados-abertos/dados-abertos-legislativo/webservices/deputados/obterDetalhesDeputado'
SENATOR_DESCRIPTION_URI = 'https://www25.senado.leg.br/web/senadores'


MAPPING_META = {
    'cam:dataFalecimento': {'label': 'Data de falecimento', 'functional': False, 'description': None, 'description_uri': CONGRESSMAN_DESCRIPTION_URI},
    'cam:dataNascimento': {'label': 'Data de nascimento', 'functional': False, 'description': None, 'description_uri': CONGRESSMAN_DESCRIPTION_URI},
    'cam:ideCadastro': {'label': 'id', 'functional': True, 'description': None, 'description_uri': CONGRESSMAN_DESCRIPTION_URI},
    'cam:nomeCivil': {'label': 'Nome completo', 'functional': False, 'description': None, 'description_uri': CONGRESSMAN_DESCRIPTION_URI},
    'cam:nomeParlamentarAtual': {'label': 'Apelido', 'functional': False, 'description': None, 'description_uri': CONGRESSMAN_DESCRIPTION_URI},
    'sen:CodigoParlamentar': {'label': 'id', 'functional': True, 'description': None, 'description_uri': SENATOR_DESCRIPTION_URI},
    'sen:NomeCompletoParlamentar': {'label': 'Apelido', 'functional': False, 'description': None, 'description_uri': SENATOR_DESCRIPTION_URI},
    'sen:NomeParlamentar': {'label': 'Nome completo', 'functional': False, 'description': None, 'description_uri': SENATOR_DESCRIPTION_URI},
}

MAPPING_PROV = {
    'cam': 'http://www2.camara.leg.br/transparencia/dados-abertos/dados-abertos-legislativo/webservices/deputados/obterDetalhesDeputado',
    'sen': 'https://www25.senado.leg.br/web/senadores',
    'slnp': 'http://www.seliganapolitica.org/'
}



class PersonGenerator(object):
    '''Binds identities from diferent sources into a single json file    
    '''
    def __init__(self):
        '''Loads a preprocessed agents.csv from sources 

        agents.csv is build from 2 sources:
            * camara
            * senado
        '''
        source_path = 'common/agents/agents.csv'
        df = pd.read_csv(source_path, sep=';', index_col=0).fillna('N/A')
        self.agents_dict = df.to_dict('index')

    def generate(self, filename='identities', sample_size=None):
        '''Generates the identities 

        [description]

        Keyword Arguments:
            filename {str} -- target file name (default: {'identities'})
            sample_size {[type]} -- if provided, will sample over this number of resources (default: {None})

        Raises:
            ValueError -- [description]
        '''
        this_prov = os.getpid()
        target_path = 'common/identities/{:}_{:}.json'.format(filename, this_prov)

        # Solve agents
        data_dict = defaultdict(list)
        prov_set = {'slnp'}

        if sample_size:
            keys = sample(list(self.agents_dict), sample_size)
            agents_dict_ = {key: self.agents_dict[key] for key in keys}
        else:
            agents_dict_ = self.agents_dict

        # fills up person entry
        for slnp_uri, columns_dict in agents_dict_.items():
            person_list = []

            person_list.append({
                'property_id': 'seliga_uri',
                'value': '{:}{:}'.format(BASE_URI, slnp_uri),
                'prov_id': this_prov
            })

            for label_, value_ in columns_dict.items():
                if not value_ == 'N/A':
                    prov_, name_ = label_.split(':')
                    prov_set = prov_set.union({prov_})

                    person_list.append({
                        'property_id': name_,
                        'value': value_,
                        'prov_id': this_prov
                    })

            data_dict['person'].append({'identity': person_list})

        data_dict['prov'].append({
            '_id': this_prov,
            'was_attributed_to': {'email': 'guilhermevarela@hotmail.com'},
            'generated_at': datetime.utcnow().strftime(DATE_MASK),
            'description_uri': DESCRIPTION_URI
        })

        # Solve property
        for property_key_, property_dict_ in MAPPING_META.items():
            prov_, name_ = property_key_.split(':')
            if prov_ in prov_set:
                property_dict_['_id'] = name_
                data_dict['property'].append(property_dict_)

        info_dict = {
            'type': 'PersonIdentity',
            'published_at': datetime.utcnow().strftime(DATETIME_MASK),
            'version': '0.9'
        }

        output_dict = {}
        output_dict['info'] = info_dict
        output_dict['data'] = data_dict
        with open(target_path, mode='w') as f:
            json.dump(output_dict, f)

if __name__ == '__main__':
    pgen = PersonGenerator()
    pgen.generate(filename='identities', sample_size=None)
    pgen.generate(filename='sample_identities', sample_size=3)
