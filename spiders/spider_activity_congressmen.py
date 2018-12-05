# -*- coding: utf-8 -*-
'''
    Date: Nov 9th, 2018

    Author: Guilherme Varela

    References:
        https://doc.scrapy.org/en/1.4/intro/tutorial.html#intro-tutorial

    Shell:
        scrapy shell 'http://www.camara.leg.br/internet/deputado/resultadoHistorico.asp?dt_inicial=03/02/2015&dt_final=03/02/2015&parlamentar=&histMandato=1&ordenarPor=1&Pesquisar=Pesquisar'
        scrapy shell 'http://www.camara.leg.br/internet/deputado/dep_Detalhe.asp?id=5830803'

    scrapy runspider spider_activity_congressmen.py -o datasets/camara/activity-55.json  -a legislatura=55

http://www.camara.leg.br/internet/deputado/resultadoHistorico.asp?dt_inicial=24/02/2015&dt_final=2015-02-24&parlamentar=&histMandato=1&ordenarPor=1&Pesquisar=Pesquisar
    missing entries -- bkp2 - bkp ?? Why?
    2015-02-09 5830515
    2015-02-24 5830490
    2015-02-24 5830805
    2015-02-24 5830828
    2015-02-24 5830830
    2015-02-24 5830671
    2015-02-25 5830661
    2015-02-25 5830818
    2015-02-27 5830793
    2015-03-02 5830661
    2015-10-22 5830849
    2015-12-15 5830858
    2015-12-16 5830859
    2015-12-28 5830858
    2016-03-15 5830862
    2016-10-10 5830777
    2016-10-11 5830777
    2018-08-21 1635224
    2018-08-22 1635214
    2018-09-14 1635227

'''
from datetime import date, datetime, timedelta
import re
import scrapy
import bs4

import utils
# Example
# CAMARA_URL = 'http://www.camara.leg.br/internet/deputado/resultadoHistorico.asp?dt_inicial=02%2F02%2F2015&dt_final=03%2F02%2F2015&parlamentar=&histMandato=1&ordenarPor=1&Pesquisar=Pesquisar'
CAMARA_URL = 'http://www.camara.leg.br/internet/deputado/'
ACTIVITY_URL = f'{CAMARA_URL}resultadoHistorico.asp'
QUERY_STR = '?dt_inicial={:}&dt_final={:}&parlamentar=&histMandato=1&ordenarPor=1&Pesquisar=Pesquisar'


class ActiviyCongressmenSpider(scrapy.Spider):
    name = 'activity_congressmen'

    # Overwrites default: ASCII
    custom_settings = {
        'FEED_EXPORT_ENCODING': 'utf-8'
    }

    def __init__(self, *args, **kwargs):
        # Handle input arguments
        legislatura = kwargs.pop('legislatura', 55)
        start_date = kwargs.pop('start_date', None)
        finish_date = kwargs.pop('finish_date', None)

        # import code; code.interact(local=dict(globals(), **locals()))

        super(scrapy.Spider, self).__init__(*args, **kwargs)

        # Process legislatura -- turn into a data interval
        if legislatura:
            legislatura = int(legislatura)
            # 55 --> 2015-02-01, 54 --> 2011-02-01, 53 --> 2007-02-01
            # legislatura beginings
            self.start_date = utils.get_start_from(legislatura)
            self.start_date = utils.busday_adjust(self.start_date + timedelta(days=1))
            if not finish_date:
                self.finish_date = min(utils.get_finish_from(legislatura), date.today())
            else:
                self.finish_date = utils.busday_adjust(finish_date)

            self.legislatura = legislatura

        elif start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            self.start_date = utils.busday_adjust(start_date)
            if not finish_date:
                finish_date = utils.busday_adjust(self.start_date + timedelta(days=1))
                self.finish_date = finish_date
            else:
                self.finish_date = utils.busday_adjust(finish_date)
        else:
            err = 'Either `legislatura` or `start_date` must be provided'
            raise ValueError(err)

        self.nm_dict = {}

    def start_requests(self):
        '''
            Stage 1: Request first term dates
        '''
        # sd = self.start_date.strftime('%d/%m/%Y')
        # fd = self.finish_date.strftime('%d/%m/%Y')
        sd = self.start_date
        fd = self.finish_date

        for dt in utils.busdays_range(sd, fd):
            dt_start = dt.strftime('%d/%m/%Y')


            q = QUERY_STR.format(dt_start, dt_start)
            url = '{:}{:}'.format(ACTIVITY_URL, q)

            req = scrapy.Request(
                url,
                self.activity_congressmen,
                headers={'accept': 'application/json'},
                meta={'dt_activity': dt_start}
            )
            yield req

    def activity_congressmen(self, response):
        '''Fetches the camara activity -- nomination of posts

        Example:
            http://www.camara.leg.br/internet/deputado/resultadoHistorico.asp?dt_inicial=03/02/2015&dt_final=03/02/2015&parlamentar=&histMandato=1&ordenarPor=1&Pesquisar=Pesquisa

        Arguments:
            response {[type]} -- [description]
        '''
        soup = bs4.BeautifulSoup(response.body_as_unicode(), features='lxml')
        activity_dict = {}
        d, m, y = response.meta['dt_activity'].split('/')
        activity_dict['dt_activity'] = f'{y}-{m}-{d}'


        for tag in soup.find(id='content').children:
            # a tag href ideCadastro -- content NomeParlamentarAtual
            info = getattr(tag, 'a', None)
            if info is not None:
                activity_dict['id_registry'] = info['href'].split('id=')[-1]
                activity_dict['nm_congressman'] = info.contents[0]

            # This block reads the contents of the message and assigns
            # entry of exit
            info = getattr(tag, 'li', None)
            if info is not None:
                # gets everything up to the first parenthesis
                # (.*)\(
                contents = re.sub(r'[\r|\t|\n]', '', info.contents[0])
                msg = re.search(r'(.*)\(', contents).group(0)
                # grebs everything enclosed in parenthesis
                extra = re.search(r'\((.*)\)', contents).group(0)
                if (('Reassução' in msg) or ('Posse' in msg) or ('Afastamento' in extra)):
                    activity_dict['dt_start'] = activity_dict['dt_activity']

                elif (('Posse' in extra) or ('Reassução' in extra) or ('Afastamento' in msg)):
                    activity_dict['dt_finish'] = activity_dict['dt_activity']

                activity_dict['message'] = contents

                id_registry = activity_dict['id_registry']
                if id_registry in self.nm_dict:
                    if self.nm_dict[id_registry] is not None:
                        activity_dict['nm_congressman'] = self.nm_dict[id_registry]['nm_congressman']
                        activity_dict['id_congressman'] = self.nm_dict[id_registry]['id_congressman']

                    yield activity_dict
                else:
                    url = f'{CAMARA_URL}dep_Detalhe.asp?id={id_registry}'
                    req = scrapy.Request(
                        url,
                        self.congressman_info,
                        headers={'accept': 'application/json'},
                        meta={'activity': activity_dict, 'url' : url},
                        dont_filter=True
                    )
                    yield req

                activity_dict = {}
                activity_dict['dt_activity'] = f'{y}-{m}-{d}'

    def congressman_info(self, response):
        '''Fetches full name from congressman

        activity page has information using internal names and not 
        birth names leading to dynamic information and possibly
        identity mismatchs -- fetches only the names

        Example:
            http://www.camara.leg.br/internet/deputado/dep_Detalhe.asp?id=5830803

        Arguments:
            response {[type]} -- [description]
        '''
        soup = bs4.BeautifulSoup(response.body_as_unicode(), features='lxml')
        activity_dict = response.meta['activity']

        ul = soup.find('ul', {'class': 'visualNoMarker'})
        if ul is not None:
            for li in ul.children:
                if isinstance(li, bs4.element.Tag):
                    # field which is a tag and content is a string
                    f, *v = li.contents
                    if 'strong' in f.name and 'nome civil' in f.contents[0].lower():
                        activity_dict['nm_congressman'] = v[0].strip()


                    elif f.name == 'a':
                        id_congressman = f.attrs['href'].split('=')[-1]
                        activity_dict['id_congressman'] = id_congressman

                if 'nm_congressman' in activity_dict and 'id_congressman' in activity_dict:
                    self.nm_dict[activity_dict['id_registry']] = activity_dict
                    yield activity_dict
                    return
        # garantees that one name is being passed along
        # import code; code.interact(local=dict(globals(), **locals()))
        yield activity_dict