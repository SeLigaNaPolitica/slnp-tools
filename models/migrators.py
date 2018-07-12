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
import errno

from scripts import get_agents_mapping, get_parties_mapping, get_education_mapping

BASE_URI = 'http://www.seliganapolitica.org/resource/'


CONGRESSMEN_DIR = 'camara_deputados/deputados/'
TURTLE_SOURCE_DIR = '{:}turtle/raw/'.format(CONGRESSMEN_DIR)
TURTLE_TARGET_DIR = '{:}turtle/edited/'.format(CONGRESSMEN_DIR)

VOTING_DIR = 'camara_deputados/votacao/'
VOTING_SOURCE_DIR = '{:}raw/'.format(VOTING_DIR)
VOTING_TARGET_DIR = '{:}edited/'.format(VOTING_DIR)


class TurtleMigrator(object):
    '''
        Provides migration utilities in order to convert previous 
            migration schemes into new objects
    '''

    def __init__(self):
        self.agents_dict = get_agents_mapping()
        self.educ_dict = get_education_mapping()
        self.parties_dict = get_parties_mapping()

    def migrate(self, input_dir, output_dir):
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
                           for line in line_list
                           if re_resource.match(line) is None]

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


class XMLMigrator(object):
    def __init__(self):
        self.agents_dict = get_agents_mapping()

    def migrate(self, source_dir, target_dir):

        glob_regex = '{:}/*.xml'.format(source_dir)

        for xmlfile in glob.glob(glob_regex):
            filename = xmlfile.split('/')[-1]
            print('processing .. {:}'.format(filename))

            with open(xmlfile, mode='r') as f:
                txt = f.read()
            f.close()

            for _, old_newidx in self.agents_dict.items():
                txt = txt.replace(*old_newidx)

            file_path = '{:}{:}'.format(target_dir, filename)
            if not os.path.exists(os.path.dirname(file_path)):
                try:
                    os.makedirs(os.path.dirname(file_path))
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            with open(file_path, mode='w') as f:
                f.write(txt)
            f.close()
            print('saved at ', file_path)


if __name__ == '__main__':
    TurtleMigrator().migrate(TURTLE_SOURCE_DIR, TURTLE_TARGET_DIR)
    XMLMigrator().migrate(VOTING_SOURCE_DIR, VOTING_TARGET_DIR)
