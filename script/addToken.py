import os
import sys
sys.path.append("..")
from config import config
#dir_file = ['../books/origin/cn','../books/origin/jp']
dir_file = ['../books/origin/jp','../books/origin/cn']
if __name__ == '__main__':
    for dir_ in dir_file:
        fs = os.listdir(dir_)
        for fp in fs:
            type = config[fp]["type"]
            if type == 0:
                continue
            fp = os.path.join("%s/%s"%(dir_,fp))
            if not os.path.isfile(fp):
                continue
            with open(fp,'r') as f:
                lines = f.readlines()
                for i,l in enumerate(lines):
                    l = l.strip()
                    if l.isdigit():
                        l = "@%s"%l 
                    lines[i]=l
            with open(fp,'w') as f:
                for l in lines:
                    l = l.strip()
                    if not l or l=='':
                        continue
                    f.write('%s\n'%l)
