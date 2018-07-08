import os
import requests
import shutil
import xml.etree.ElementTree as ET
import argparse
import json
import itertools
import logging
import re
import uuid
import sys
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import unidecode


#this camara`s endpoint contains the list of politicians in current legislation
endpoint = "http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/ObterDeputados"

#folder where the photos will be saved
target_folder = "slnp_photos/"


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('[%(asctime)s %(levelname)s %(module)s]: %(message)s'))
    logger.addHandler(handler)
    return logger

logger = configure_logging()

REQUEST_HEADER = {
    'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}


def get_soup(url, header):
    response = urlopen(Request(url, headers=header))
    return BeautifulSoup(response, 'html.parser')

def get_query_url(query):
    return "https://www.google.co.in/search?q=%s&source=lnms&tbm=isch" % query

def extract_images_from_soup(soup):
    image_elements = soup.find_all("div", {"class": "rg_meta"})
    metadata_dicts = (json.loads(e.text) for e in image_elements)
    link_type_records = ((d["ou"], d["ity"]) for d in metadata_dicts)
    return link_type_records

def extract_images(query):
    url = get_query_url(query)
    logger.info("Souping")
    soup = get_soup(url, REQUEST_HEADER)
    logger.info("Extracting image urls")
    link_type_records = extract_images_from_soup(soup)
    return link_type_records

def get_raw_image(url):
    req = Request(url, headers=REQUEST_HEADER)
    resp = urlopen(req)
    return resp.read()

def save_image(raw_image, image_type, save_directory, file_name):
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    extension = image_type if image_type else 'jpg'
    file_name = file_name + "." + extension
    save_path = os.path.join(save_directory, file_name)
    with open(save_path, 'wb') as image_file:
        image_file.write(raw_image)

def download_images_to_dir(images, save_directory, num_images):
    download_counter = 0
    for i, (url, image_type) in enumerate(images):
        try:
            ext = os.path.splitext(url)[-1]
            if ext != ".jpg" and ext != ".png":
                continue 

            if download_counter > num_images:
                return    

            logger.info("Making request (%d/%d): %s", i, num_images, url)
            raw_image = get_raw_image(url)
            save_image(raw_image, image_type, save_directory, str(download_counter) )
            download_counter += 1
        except Exception as e:
            logger.exception(e)

def run(query, save_directory, num_images=100):
    query = '+'.join(query.split())
    logger.info("Extracting image links")
    images = extract_images(query)
    logger.info("Downloading images")
    download_images_to_dir(images, save_directory, num_images)
    logger.info("Finished")



#function that parsers the xml document retrivied from camara`s endpoint
def doc_parser(xml):
    data_list = []
    root = ET.fromstring(xml)
    for dep in root.findall('deputado'):
        id = dep.find('ideCadastro').text
        name = unidecode.unidecode(dep.find('nome').text)
        if os.path.exists("downloads/"+str(id)):
            continue
        run("DEPUTADO "+name, "downloads/"+str(id), 30)

req = requests.get(endpoint)
if req.status_code == requests.codes.ok:
    print("Document has been downloaded from", endpoint)
    print("Initializing document parsing")
    doc_parser(req.text)
else:
    print ("Something is wrong, error: ", req.status_code)

