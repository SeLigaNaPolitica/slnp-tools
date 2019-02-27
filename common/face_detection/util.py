import cv2
import os
import face_emb as fe
import numpy as np
import operator

def load_database(root_folder):
    print("Registering facial images of reference in database ...")
    person_dict = {}
    for person_id in os.listdir(root_folder): 
        if person_id[0] == '.':
            continue
        person_dict[person_id] = []
        for image in os.listdir(os.path.join(root_folder, person_id)):
            if image[0] == '.':
                continue
            img_path = os.path.join(root_folder, person_id, image)
            print(img_path)
            img = cv2.imread(img_path)
            if img.shape[2] == 4:
                img = cv2.cvtColor(img,cv2.COLOR_BGRA2RGB)
            else:
                img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
            emb = fe.get_embedding(img)
            person_dict[person_id].append(emb)

    return person_dict


def distance(vector1, vector2):
    return np.sqrt(np.sum((vector1-vector2)**2))  


def calcule_near_neighbors(top, person_dict, emb1):
    near5 = []
    for key, emb_list in person_dict.items():
            for emb in emb_list:
                dist = distance(emb1,emb)
                #print(dist)
                if len(near5) < top:
                    near5.append((dist, key))
                else:
                    bigger = 0
                    bigger_index = -1
                    for index, tuple_ in enumerate(near5):
                        if tuple_[0] > bigger:
                            bigger = tuple_[0]
                            bigger_index = index
                    if bigger > dist:
                        near5.pop(bigger_index)
                        near5.append((dist, key))
    return near5

def vote(nearList):
    dict_ = {}
    dict_score = {}
    for index, tuple_ in enumerate(nearList):
        if tuple_[1] not in dict_:
            dict_[tuple_[1]] = 1
            dict_score[tuple_[1]] = tuple_[0]
        else:
            dict_[tuple_[1]] += 1
            dict_score[tuple_[1]] += tuple_[0]
    
    #print(dict_score)
    person_id = max(dict_.items(), key=operator.itemgetter(1))[0]
    prob = dict_[person_id]/len(nearList)

    #check draw
    for key, value in dict_.items():
        if key != person_id and value == dict_[person_id]:
            if dict_score[person_id] < dict_score[key]:
                break
            else:
                person_id = key
    
    return (person_id, prob)


def who_is(person_dict, emb, top=5):
    near5 = calcule_near_neighbors(top, person_dict, emb)
    return vote(near5)
    

if __name__ == '__main__':
    person_dict = load_database("database")
    for key, emb_list in person_dict:
        print(key, len(emb_list))



