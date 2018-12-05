# -*- coding: utf-8 -*-
'''
    Date: Dec 5th, 2017

    Author: Guilherme Varela

    ref: https://doc.scrapy.org/en/1.4/intro/tutorial.html#intro-tutorial

    Three phase strategy:
    1. Get each congressmen for current term
    2. For each congressmen get details
    3. Within details gets current membership and membershipHistory

    Scrapy shell:
        1. scrapy shell 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/ObterDeputados'

    Scrapy running: scrapy runspider spider_congressman_with_memberships.py

    Scrapy run + store: 
        scrapy runspider spider_congressman_with_memberships.py -o datasets/camara/congressman_with_memberships-55.json  -a legislatura=55

    updates:
        2018-03-08 updated to use XPaths
        2018-04-04 updated to query current list of congress on API V2.
        2018-08-30 making it into a standing alone script.
'''
import datetime
import json
import xml.etree.ElementTree as ET

import scrapy
import networkx as nx
# import re


import pandas as pd
import aux

# Unique id without Network address
from uuid import uuid4

SLNP_PREFIX = 'http://www.seliganapolitica.org/resource/'

URL_OPEN_DATA_CAMARA_API_V1 = 'http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/'
URL_OPEN_DATA_CAMARA_API_V2 = 'https://dadosabertos.camara.leg.br/api/v2/'


class ElectedCongressmenSpider(scrapy.Spider):
    name = 'elected_congressmen'


    # Overwrites default: ASCII
    custom_settings={
        'FEED_EXPORT_ENCODING': 'utf-8'
    }

    congressman_with_affiliation_membership = set([
        'idPartidoAnterior', 'siglaPartidoAnterior',
        'nomePartidoAnterior', 'idPartidoPosterior',
        'siglaPartidoPosterior', 'nomePartidoPosterior',
        'dataFiliacaoPartidoPosterior'])

    congressman_with_term_membership = set(
        ['siglaUFRepresentacao', 'descricaoCausaFimExercicio', 'dataInicio','dataFim', 'situacaoExercicio']
    )

    congressman_mapping = set([
        'ideCadastro', 'nomeCivil', 'nomeParlamentarAtual',
        'dataNascimento', 'dataFalecimento'])

    def __init__(self, *args, **kwargs):
        # Handle input arguments
        legislatura = kwargs.pop('legislatura', 55)
        start_date = kwargs.pop('start_date', None)
        finish_date = kwargs.pop('finish_date', None)

        super(scrapy.Spider).__init__(*args, **kwargs)
        # Parses person json
        self.agents_graph = get_agents()
	    # yml or json?
        self.parties = get_parties()

        # Roles dictionary
        self.roles = get_roles()['rdfs:label']
        self.prefix = 'cam'

        # Process legislatura -- turn into a data interval
        if legislatura:
            legislatura = int(legislatura)
        	# 55 --> 2015-02-01, 54 --> 2011-02-01, 53 --> 2007-02-01
        	# legislatura beginings
            start_date = get_start_from(legislatura)
            self.start_date = start_date
            self.legislatura = legislatura

        elif start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            self.start_date = busday_adjust(start_date)
        else:
            err = 'Either `legislatura` or `start_date` must be provided'
            raise ValueError(err)

        if finish_date:
            finish_date = datetime.datetime.strptime(finish_date, '%Y-%m-%d')
            self.finish_date = finish_date
        else:
            finish_date = self.start_date + datetime.timedelta(days=1)
            self.finish_date = finish_date

    def start_requests(self):
        '''
            Stage 1: Request first term dates
        '''

        url = URL_OPEN_DATA_CAMARA_API_V2
        url = '{:}legislaturas?id={:}'.format(url, self.legislatura)
        url = '{:}&ordem=DESC'.format(url)
        url = '{:}&ordenarPor=id'.format(url)

        req = scrapy.Request(
            url,
            self.request_elected,
            headers={'accept': 'application/json'}
        )
        yield req

    def request_elected(self, response):
        '''
            Stage 2: Request elected dates
        '''
        # Override this to allow to get custom start and finish dates
        body = json.loads(response.body_as_unicode())
        data = body['dados']

        self.start_date = datetime.datetime.strptime(data[0]['dataInicio'], '%Y-%m-%d')
        self.finish_date = datetime.datetime.strptime(data[0]['dataFim'], '%Y-%m-%d')


        startstr = self.start_date.strftime('%Y-%m-%d')


        start1 = self.start_date
        start1 = start1 + datetime.timedelta(1)
        start1str = start1.strftime('%Y-%m-%d')

        url = URL_OPEN_DATA_CAMARA_API_V2
        url = '{:}deputados?idLegislatura={:}'.format(url, self.legislatura)
        url = '{:}&dataInicio={:}'.format(url, startstr)
        url = '{:}&dataFim={:}'.format(url, start1str)
        url = '{:}&ordenarPor=nome'.format(url)

        req = scrapy.Request(
            url,
            self.request_congressman,
            headers={'accept': 'application/json'}
        )
        yield req

    def request_congressman(self, response):
        '''
           Start by querying every congressmen during term (legislatura)

        '''
        body = json.loads(response.body_as_unicode())
        data = body['dados']
        links = body['links']

        for congressman in data:
            resource_idx = int(congressman['id'])
            url = URL_OPEN_DATA_CAMARA_API_V1
            url = '{:}ObterDetalhesDeputado?ideCadastro='.format(url)
            url = '{:}{:}'.format(url, resource_idx)
            url = '{:}&numLegislatura={:}'.format(url, self.legislatura)

            req = scrapy.Request(
                url,
                self.parse_congressman,
                headers={'accept': 'application/json'},
                meta={'resource_idx': resource_idx}
            )
            yield req

        # Next page
        for link in links:
            if (link['rel'] == 'next'):
                if link['href']:
                    req = scrapy.Request(
                        link['href'],
                        self.request_congressman,
                        headers={'accept': 'application/json'}
                    )
                    yield req

    def parse_congressman(self, response):
        '''
            Paginates congressman xml

            ref
                http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/ObterDetalhesDeputado?ideCadastro=160518&numLegislatura=55
        '''
        root = ET.fromstring(response.body_as_unicode())

        # resource_uri = response.meta['resource_uri']
        outputs = {}
        for deputados in root:
            outputs = {}
            for attr in deputados:
                if attr.tag in self.congressman_mapping:
                    key = '{:}:{:}'.format(self.prefix, attr.tag)
                    value = aux.parse_fn(attr.text)
                    if (len(value) > 0):
                        if 'data' in attr.tag:
                            outputs[key] = aux.date_format(value)
                        else:
                            outputs[key] = aux.text_format(attr.text)
                    else:
                        outputs[key] = None


            outputs['resource_uri'] = self.search_agents_uri(outputs)
            if not outputs['resource_uri']:
                outputs['resource_uri'] = '{:}{:}'.format(SLNP_PREFIX, str(uuid4()))

            self.process_terms(deputados, outputs)

            # self.process_afiliations(deputados, outputs)

        if bool(outputs['terms']):
            yield outputs

    def search_agents_uri(self, outputs):
        '''Search agents uri in a property digraph

        Ref .: https://networkx.github.io/documentation/latest/release/migration_guide_from_1.x_to_2.0.html

        Arguments:
            outputs {[type]} -- [description]

        Returns:
            [type] -- [description]
        '''
        mapping_dict = {
            'cam:ideCadastro': 'cam:ideCadastro',
            'cam:nomeCivil': 'cam:nomeCivil',
            'cam:nomeCivil': 'sen:NomeCompletoParlamentar'
        }
        for col_congress, col_agents in mapping_dict.items():

            lbl = col_congress.split(':')[-1]
            val = outputs[col_congress]
            nid = '{:s}:{:s}'.format(lbl, val)
            try:
                vid = self.agents_graph.predecessors(nid)
                vid = list(vid)[0] if not isinstance(vid, str) else vid
            except nx.exception.NetworkXError:
                vid = None

            if vid:
                return vid
        return None

    def process_terms(self, deputados, outputs, filter_date=True):
        '''Process terms from congressmen

        Arguments:
            deputados {ET} -- XML iterable
            outputs {dict} -- output dict
            filter_date {bool} -- filters only terms at the beginning (default:None)
        '''
        terms = []
        filter_value = datetime.datetime.strftime(self.start_date,'%Y-%m-%d')
        for term in deputados.find('./periodosExercicio'):
            result = {
                'slnp:resource_uri': str(uuid4()),
                'org:role': self.roles['Deputy']
            }
            for attr in term:
                if attr.tag in self.congressman_with_term_membership:
                    key = '{:}:{:}'.format(self.prefix, attr.tag)
                    value = aux.parse_fn(attr.text)
                    if (len(value) > 0):
                        if 'data' in attr.tag:
                            result[key] = aux.date_format(value)
                        else:
                            result[key] = aux.text_format(attr.text)
                    else:
                        result[key] = None

            if filter_date and result['cam:dataInicio'] == filter_value:
                terms.append(result)
        outputs['terms'] = terms

    def process_afiliations(self, deputados, outputs):
        affiliations = []
        for affiliation in deputados.find('./filiacoesPartidarias'):
            result = {
                'slnp:resource_uri': str(uuid4()),
                'org:role': self.roles['Affiliate']
            }
            for attr in affiliation:
                if attr.tag in self.congressman_with_affiliation_membership:
                    key = '{:}:{:}'.format(self.prefix, attr.tag)
                    value = aux.parse_fn(attr.text)
                    if (len(value) > 0):
                        if 'data' in attr.tag:
                            result[key] = aux.date_format(value)
                        else:
                            result[key] = aux.text_format(attr.text)
                    else:
                        result[key] = None
            if affiliations:
                affiliations[-1]['cam:finishDate'] = result['cam:dataFiliacaoPartidoPosterior']
            else:
                affiliation_0 = {
                    'slnp:resource_uri': str(uuid4()),
                    'cam:sigla': result['cam:siglaPartidoAnterior'],
                    'cam:startDate': None,
                    'cam:finishDate': result['cam:dataFiliacaoPartidoPosterior'],
                    'org:role': self.roles['Affiliate'],
                }
                affiliations.append(affiliation_0)

            affiliation_0 = {
                'slnp:resource_uri': str(uuid4()),
                'cam:sigla': result['cam:siglaPartidoPosterior'],
                'cam:startDate': result['cam:dataFiliacaoPartidoPosterior'],
                'cam:finishDate': None,
                'org:role': self.roles['Affiliate']
            }
            affiliations.append(affiliation_0)

        if affiliations:
            outputs['affiliations'] = affiliations
        else:
            id_partido = deputados.find('./partidoAtual/idPartido')
            outputs['affiliations'] = [{
                'slnp:resource_uri': str(uuid4()),
                'cam:sigla': id_partido.text,
                'cam:startDate': None,
                'cam:finishDate': None,
                'org:role': self.roles['Affiliate'],
            }]


def get_agents(identities_path='identities.json'):

    with open(identities_path, mode='r') as f:
        agents_json = json.load(f)

    if agents_json['info']['type'] != 'PersonIdentity':
        ValueError('identitiesJSON must be of info#type = `PersonIdentity`')

    agents_list = agents_json['data']['person']

    properties_list = agents_json['data']['property']

    agents_graph = nx.DiGraph()

    for a in agents_list:

        id_list = a['identity']

        source_list = [dict_['value']
                       for dict_ in id_list
                       if dict_['property_id'] == 'seliga_uri']

        target_list = []

        for p in properties_list:
            pid = p['_id']

            p_list = [id_dict
                      for id_dict in id_list
                      if id_dict['property_id'] == p['_id']]

            if bool(p_list):
                p_dict = p_list[0]
                pvl = p_dict['value']
                pvl = '{0:.0f}'.format(pvl) if isinstance(pvl, float) else pvl
                pst = '{:s}:{:s}'.format(pid, pvl)

                target_list.append(pst)

        if bool(source_list):

            agents_graph.add_edges_from([
                (src, tgt)
                for src in source_list
                for tgt in target_list
            ])

    return agents_graph


def get_roles():

    roles_path = 'datasets/slnp/roles.csv'

    df = pd.read_csv(roles_path, sep=';', index_col=0)

    roles_dict = df.to_dict()

    for label, d in roles_dict.items():
        roles_dict[label] = {v: k for k, v in d.items()}

    return roles_dict


def get_parties():
    parties_path = 'datasets/slnp/organizations.csv'

    df = pd.read_csv(parties_path, sep=';', index_col=0)

    parties_dict = df.to_dict()

    for label, d in parties_dict.items():
        parties_dict[label] = {v: k for k, v in d.items()}

    return parties_dict


def get_start_from(legislatura):
    '''Gets the first date from legislatura

    Arguments:
        legislatura {int} -- [description]
    '''
    year = (legislatura - 55) * 4 + 2015

    return datetime.date(year, 2, 1)


def busday_adjust(start_date):
    '''Returns closest business date from start date

    Arguments:
        start_date {datetime.date} -- inital date

    Returns:
        busdate {datetime.date} -- busdate
    '''

    finish_date = start_date + datetime.timedelta(21)

    for busdate in busdays_range(start_date, finish_date):
        return busdate
    return None


def busdays_range(start_date, end_date):

    from dateutil.rrule import DAILY, rrule, MO, TU, WE, TH, FR

    return rrule(DAILY, dtstart=start_date, until=end_date, byweekday=(MO,TU,WE,TH,FR))
