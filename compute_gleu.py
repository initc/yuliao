import precess_compare_duan
files = 'testfile.txt'
f = open(files,'r')
gleu = precess_compare_duan.Gleu('transform',"","")
lines = f.readlines()
#print(len(lines))
for l in lines:
    l = l.strip()
    l = l.split('$')
    zh = l[0]
    t1 = l[1]
    t2 = l[2]
    g1, zh_len1, t_len1, c_len1 = gleu.gleu_compare_line(zh,t1)
    g2, zh_len2, t_len2, c_len2 = gleu.gleu_compare_line(zh,t2)
    print('==中文==  %s\n'%zh)
    print("==错误翻译==  %s\n"%t1)
    print("==正确翻译==  %s\n"%t2)
    print("gleu_T  :%f  gleu_F :%f  equal:%s\n"%(g1, g2, "True" if g1==g2 else "False"))
    print("zh_len : %f \n"%zh_len1)
    print("trans_len : %f  %f  %f\n"%(t_len1,t_len2, t_len1-t_len2))
    print("common_len : %f  %f  %f\n"%(c_len1, c_len2, c_len1-c_len2))
    print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")