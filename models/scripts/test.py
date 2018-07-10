import hashlib

def main(name, uriorg):

    splistring = uriorg.split()
    splistring=sorted(splistring)
    token = ""
    for x in splistring:
        token = token + x
    token = name+token+"membership"+"post"
    token = token.encode('utf-8');
    
    # return "http://www.seliganapolitica.org/resource/"+hashlib.md5(token).hexdigest()
    return "http://www.seliganapolitica.org/resource/"+token


if __name__ == '__main__':
    print(main("ABEL MESQUITA JR.", "http://www.camara.leg.br"))
    print(main("ADAIL CARNEIRO", "http://www.camara.leg.br"))
    print(main("ABEL SALVADOR MESQUITA JUNIOR", "http://www.camara.leg.br"))
    print(main("JOSE ADAIL CARNEIRO SILVA", "http://www.camara.leg.br"))