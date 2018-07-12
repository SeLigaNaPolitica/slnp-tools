'''This module converts a CSV into json

Tabular data into json data
'''
from collections import defaultdict
from datetime import datetime
from random import sample
import json
import os

import pandas as pd


MAPPING_PROV = {
    'cam:dataFalecimento': 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/',
    'cam:dataNascimento': 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/',
    'cam:ideCadastro': 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/',
    'cam:nomeCivil': 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/',
    'cam:nomeParlamentarAtual': 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/',
    'sen:CodigoParlamentar': 'http://legis.senado.leg.br/dadosabertos/senador/',
    'sen:NomeCompletoParlamentar': 'http://legis.senado.leg.br/dadosabertos/senador/',
    'sen:NomeParlamentar': 'http://legis.senado.leg.br/dadosabertos/senador/'
}
MAPPING_TYPES = {
    'cam:dataFalecimento': 'Property',
    'cam:dataNascimento': 'Property',
    'cam:ideCadastro': 'Identity',
    'cam:nomeCivil': 'Property',
    'cam:nomeParlamentarAtual': 'Property',
    'sen:CodigoParlamentar': 'Identity',
    'sen:NomeCompletoParlamentar': 'Property',
    'sen:NomeParlamentar': 'Property',
}

MAPPING_PROV = {
    'cam': 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/',
    'sen': 'http://legis.senado.leg.br/dadosabertos/senador/',
    'slnp': 'http://www.seliganapolitica.org/'
}

MAPPING_LABELS = {
    'cam': 'Camara do Deputados',
    'sen': 'Senado',
    'slnp': 'Se Liga na Politica'
}

DATETIME_MASK = '%m-%d-%Y %H:%M'
DATE_MASK = '%m-%d-%Y'
BASE_URI = 'http://www.seliganapolitica.org/resource/'
DESCRIPTION_URI = 'https://github.com/SeLigaNaPolitica/slnp-tools/tree/develop/models/generators.py'


class PersonGenerator(object):
    '''Binds identities from diferent sources into a single json file    
    '''
    def __init__(self):
        '''Loads a preprocessed agents.csv from sources 

        agents.csv is build from 2 sources:
            * camara
            * senado
        '''
        source_path = 'agents/agents.csv'
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
            keys = sample(list(self.agents_dict), 3)
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

            data_dict['person'].append(person_list) 

        data_dict['prov'].append({
            '_id': this_prov,
            'was_attributed_to': {'email': 'guilhermevarela@hotmail.com'},
            'generated_at': datetime.utcnow().strftime(DATE_MASK),
            'description_uri': DESCRIPTION_URI
        })

        # Solve provenance list
        for key_, value_ in MAPPING_PROV.items():
            prov_, name_ = label_.split(':')
            if prov_ in prov_set:
                data_dict['property'].append({
                    '_id': name_,
                    'label': MAPPING_LABELS[prov_],
                    'functional': value_ == 'Identity'
                    'description': datetime.utcnow().strftime(DATE_MASK),
                    'description_uri': DESCRIPTION_URI
                })

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

# def make_agents_json(filename='identities', sample_size=None):
#     '''Generates the identities 
    
#     [description]
    
#     Keyword Arguments:
#         filename {str} -- target file name (default: {'identities'})
#         sample_size {[type]} -- if provided will perform a sample over (default: {None})
    
#     Raises:
#         ValueError -- [description]
#     '''

#     target_path = 'datasets/slp/{:}.json'.format(filename)
#     # Solve agents
#     resource_list = [] 
#     prov_set = {'slnp'}
#     for slnp_uri, columns_dict in agents_dict.items():
#         resource_dict = defaultdict(list)
#         resource_dict['Identity'].append({
#             'hasName': 'resource_uri',
#             'hasValue': 'http://www.seliganapolitica.org/resource/{:}'.format(slnp_uri),
#             'hasProv': 'slnp'
#         })

#         for label_, value_ in columns_dict.items():
#             # if isinstance(value_, str) or not isnan(value_):
#             if not value_ == 'N/A':
#                 prov_, name_ = label_.split(':')
#                 prov_set = prov_set.union({prov_})
#                 if MAPPING_TYPES[label_] in ('Property',):
#                     resource_dict['Property'].append({
#                         'hasName': name_,
#                         'hasValue': value_,
#                         'hasProv': prov_
#                     })
#                 elif MAPPING_TYPES[label_] in ('Identity',):
#                     resource_dict['Identity'].append({
#                         'hasName': name_,
#                         'hasValue': value_,
#                         'hasProv': prov_
#                     })
#                 else:
#                     raise ValueError('only Identity and Property types mapped')


#         resource_list.append(resource_dict)

#     # Solve provenance list
#     prov_list = []
#     for key_, value_ in MAPPING_PROV.items():
#         if key_ in prov_set:
#             prov_list.append({
#                 'hasId': key_,
#                 'hasPublisher': value_,
#                 'datePub': datetime.utcnow().strftime(DATE_MASK),
#             })

#     data_dict = {}
#     data_dict['Resource'] = resource_list
#     data_dict['Prov'] = prov_list

#     info_dict = {
#         'hasType': 'Identity',
#         'timstampPub': datetime.utcnow().strftime(DATETIME_MASK),
#         'hasVersion': '0.0.1'
#     }

#     output_dict = {}
#     output_dict['Info'] = info_dict
#     output_dict['Data'] = data_dict
#     with open(target_path, mode='w') as f:
#         json.dump(output_dict, f)


if __name__ == '__main__':
    pgen = PersonGenerator()
    pgen.generate(filename='identities', sample_size=None)
    pgen.generate(filename='sample_identities', sample_size=3)
