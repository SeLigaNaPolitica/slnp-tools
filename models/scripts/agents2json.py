'''This module converts a CSV into json

Tabular data into json data
'''
from collections import defaultdict
from datetime import datetime
from random import sample
import json



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

DATETIME_MASK = '%m-%d-%Y %H:%M'
DATE_MASK = '%m-%d-%Y'

def make_agents_json(agents_dict, filename='agents'):    
    target_path = 'datasets/slp/{:}.json'.format(filename)
    # Solve agents
    resource_list = [] 
    prov_set = {'slnp'}
    for slnp_uri, columns_dict in agents_dict.items():
        resource_dict = defaultdict(list)
        resource_dict['Identity'].append({
            'hasName': 'resource_uri',
            'hasValue': 'http://www.seliganapolitica.org/resource/{:}'.format(slnp_uri),
            'hasProv': 'slnp'
        })

        for label_, value_ in columns_dict.items():
            # if isinstance(value_, str) or not isnan(value_):
            if not value_ == 'N/A':
                prov_, name_ = label_.split(':')
                prov_set = prov_set.union({prov_})
                if MAPPING_TYPES[label_] in ('Property',):
                    resource_dict['Property'].append({
                        'hasName': name_,
                        'hasValue': value_,
                        'hasProv': prov_
                    })
                elif MAPPING_TYPES[label_] in ('Identity',):
                    resource_dict['Identity'].append({
                        'hasName': name_,
                        'hasValue': value_,
                        'hasProv': prov_
                    })
                else:
                    raise ValueError('only Identity and Property types mapped')


        resource_list.append(resource_dict)

    # Solve provenance list
    prov_list = []
    for key_, value_ in MAPPING_PROV.items():
        if key_ in prov_set:
            prov_list.append({
                'hasId': key_,
                'hasPublisher': value_,
                'datePub': datetime.utcnow().strftime(DATE_MASK),
            })

    data_dict = {}
    data_dict['Resource'] = resource_list
    data_dict['Prov'] = prov_list

    info_dict = {
        'hasType': 'Identity',
        'timstampPub': datetime.utcnow().strftime(DATETIME_MASK),
        'hasVersion': '0.0.1'
    }

    output_dict = {}
    output_dict['Info'] = info_dict
    output_dict['Data'] = data_dict
    with open(target_path, mode='w') as f:
        json.dump(output_dict, f)


if __name__ == '__main__':    
    source_path = 'datasets/slnp/agents.csv'
    df = pd.read_csv(source_path, sep=';', index_col=0).fillna('N/A')
    agents_dict = df.to_dict('index')

    filename ='agents'
    # # Uncomment to generate a sample
    # keys = sample(list(agents_dict), 3)
    # agents_dict = {key: agents_dict[key] for key in keys}
    # filename ='sample_agents'


    make_agents_json(agents_dict, filename=filename)