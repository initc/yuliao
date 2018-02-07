import precess
files = 'testfile.txt'
f = open(files,'r')
gleu = precess.Gleu('transform')
lines = f.readlines()
#print(len(lines))
for l in lines:
    l = l.strip()
    l = l.split('\t')
    g = gleu.gleu_compare(l[0],l[1])
    print('Gleu : %f ---T  %s  === O %s \n'%(g,l[0],l[1]))

