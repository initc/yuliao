#coding:utf-8 -*-  
import math
import time
import json
import os
import pickle
import re
from config import config
from collections import OrderedDict
import random
import traceback

class Gleu(object):
    """对翻译后的文本进行gleu值的匹配"""
    def __init__(self, save_dir, random_dir, chunking=1000):
        """
        @paras chuncking:对一个文本的分段大小，默认为500
        """
        self.chunking=chunking
        self.save_dir = save_dir
        self.random_dir = random_dir
        self.pattern = re.compile('(。|``|\?|,|\'\'|\.)')


    def ngrams(self, s, n=4):
        """计算一个语句的ngrams的数量，默认只取4
        @paras n:n-grams的数量，默认为4
        @return ng:一个dict的值，存储这句子的n-gram
        """
        s = "".join(s.split())
        s = self.pattern.sub('',s)
        ng=set([])
        for i in range(n):
            length=len(s)
            for j in range(length-i):
                w=s[j:j+i+1]
                ng.add(w)
        return ng


    def gleu_compare(self ,t ,o):
        """返回两个句子的gleu
        @paras o:原句子
        @paras t:对比的句字
        @return :gleu值
        """
        
        o_gleu = self.ngrams(o)
        t_gleu = self.ngrams(t)
        t_len = len(t_gleu)
        o_len = len(o_gleu)
        if not t_len or not o_len:
            return 0.0
        #print(o_gleu&t_gleu)
        common_length = len(o_gleu & t_gleu)
        return min(common_length/t_len,common_length/o_len)


    def acc_gleu_compare(self,ti,oi):
        ct = self.acc_t[ti]
        acc_o = self.acc_o[oi]
        len_match = len(acc_o)
        match_len = 0
        max_gleu = 0.0
        for i in range(len_match):
            co = acc_o[i]
            t_len = len (ct)
            o_len = len(co)
            if not t_len or not o_len:
                continue
            common_length = len(ct&co)
            tmp_gleu = min(common_length/t_len,common_length/o_len)
            #print(tmp_gleu)
            if tmp_gleu > max_gleu:
                max_gleu = tmp_gleu
                match_len = i+1
        return max_gleu,match_len

       
    def compare_s(self, paras_t, paras_o,compare_len,info,l=5,len_match = 3,low_gleu=0.1):
        '''
        @paras compare_len: 一对多的匹配  最多匹配len_match个
        @paras  : zh paras
        @paras paras_o : translate paras
        @paras info : 文章参数
        '''
        acc_t = []
        acc_o = []
        tmp_o = []
        for i in paras_t:
            g = self.ngrams(i)
            acc_t.append(g)
        for i in paras_o:
            g = self.ngrams(i)
            tmp_o.append(g)
        self.acc_t = acc_t
        len_o = len(tmp_o)
        for i in range(len_o):
            acc = []
            tmp = set([])
            for j in range(len_match):
                if i + j >= len_o:
                    break
                tmp |=  tmp_o[i+j]
                acc.append(tmp.copy())
            acc_o.append(acc)
        self.acc_o = acc_o
        #print("acc_o ",acc_o)

        (t_duan_line,o_duan_line,t_line_duan,o_line_duan) = info

        len_duan = len(o_duan_line)  # 获取翻译文章的总的段落数
        pos=[]
        for in_t,t in enumerate(acc_t):
            #如果字符串太短，就没有很大的意义
            #if len(t) <= l:
            #    continue
            max_gleu=0
            o_i = None
            t_i = None
            match_len = None
            t_duan = t_line_duan[in_t]  # 获取所在的段落 
            # 计算段落的上下界
            begin_d = max(0,t_duan-compare_len)
            end_d = min(len_duan-1,t_duan+compare_len)
            begin =max(0,o_duan_line[begin_d]-10)  # 获取对应的行数
            end = o_duan_line[end_d]  # 行数
            
            
            for index_o in range(begin,end):
                in_o = index_o
                o = acc_o[in_o]
                gleu,_match_len = self.acc_gleu_compare(in_t,in_o)
                #print(gleu,_match_len)
                if gleu > max_gleu:
                    max_gleu=gleu
                    t_i = in_t
                    o_i = in_o
                    match_len = _match_len
            if o_i==None : continue
            pos.append((t_i,o_i,match_len,max_gleu,t_line_duan[t_i],o_line_duan[o_i]))
        return pos


    def compare_c(self,chunk_t,chunk_o,low_gleu=0.1):
        """对比段落的gleu值，获取段落的一对一"""
        pos = []
        for in_t,t in enumerate(chunk_t):
            max_gleu=0
            t_i=None
            o_i=None
            for in_o,o in enumerate(chunk_o):
                gleu_0=self.gleu_compare(t[0],o[0])
                gleu_1=self.gleu_compare(t[-1],o[-1])
                if gleu_0+gleu_1 < max_gleu:
                    max_gleu=gleu_0+gleu_1
                    t_i = in_t
                    o_i = in_o
                if max_gleu < low_gleu:
                    continue
                pos.append((t_i,o_i))
        return pos


    def read_full_cn(self, fname, pattern, pattern_len):
        '''
        把一篇文章分成几个片段，这些片段首先是由章节分开，随后依照章节内的序列号分开
        @paras fname : 文章的名字
        @paras pattern : 文章分章的分隔符
        @paras pattern_len : 需要匹配的长度
        @return paras ：分段后的文章,一个二维数组
        '''
        try:
            with open(fname,'r') as f:
                
                full_paras = f.readlines()

                len_lines = len(full_paras)
                #总的文章结构
                paras = [] #一个二维的数组
                #文章的章节
                pa = []
                #文章的序号节点
                p = []
                lines_index = 0
                #一个章节中的序号列表
                lines_order = 0
                while True:
                    #超出数组了
                    if lines_index >= len_lines:
                        pa.append(p)
                        paras.append(pa)
                        break
                    #句子之前的数目
                    b_sens = full_paras[lines_index].strip()
                    lines_index += 1
                    #句子的内容
                    sentence = full_paras[lines_index].strip()
                    #每一个段落的句子‘数’
                    paras_len = int(b_sens.split()[0])
                    content = sentence.split()
                    #如果是章节或者序列的标志
                    if paras_len==1 and len(content)==3 :
                        c = "".join(content[:2])
                        if len(c)==pattern_len and pattern.match(c):
                            #读取到了新的一章 
                            if p and pa :
                                pa.append(p)
                                paras.append(pa)
                            pa = []
                            p = []
                            lines_index += 1
                            continue
                        c = content[1]
                        #新的一个序列节点
                        if c.isdigit() and int(c)==1 and content[0]=="@" :
                            #如果之前有序列 把序列加入到章节中
                            if p:
                                pa.append(p)
                            p = []
                            lines_order = 1
                            lines_index += 1
                            continue
                        elif c.isdigit() and int(c)==lines_order+1 and content[0]=="@":
                            #把上一个序号内容加入到文章中
                            pa.append(p)
                            lines_order+=1
                            p = []
                            lines_index += 1
                            continue
                    #是一个普通的句子
                    p.append(b_sens)
                    for i in range(paras_len):
                        p.append(full_paras[lines_index+i].strip())
                    lines_index += paras_len
                    continue
                return paras
        except Exception as e:
            print("catch exception in read_full method::")
            print(repr(e))


    def read_full_jp(self, oname, tname,pattern,pattern_len):
        '''
        
        @paras oname : 文章的中文 
        @paras tname : 文章的译文
        @return paras ：分段后的文章,一个二维数组
        '''
        try:
            with open(oname,'r') as f,open(tname) as f1:
                
                full_paras = f.readlines()
                trans_paras = f1.readlines()

                len_lines = len(full_paras)
                #总的文章结构
                paras = [] #一个二维的数组
                tparas = []
                #文章的章节
                pa = []
                tpa = []
                #文章的序号节点
                p = []
                tp = []
                lines_index = 0
                #一个章节中的序号列表
                lines_order = 0
                while True:
                    #超出数组了
                    if lines_index >= len_lines:
                        #中文
                        pa.append(p)
                        paras.append(pa)
                        #译文
                        tpa.append(tp)
                        tparas.append(tpa)
                        #
                        break
                    #句子之前的数目
                    b_sens = full_paras[lines_index].strip()
                    lines_index += 1
                    #句子的内容
                    sentence = full_paras[lines_index].strip()
                    #每一个段落的句子‘数’
                    paras_len = int(b_sens.split()[0])
                    content = sentence.split()
                    #如果是章节或者序列的标志
                    if paras_len==1 and len(content)==3 :
                        c = "".join(content[:2])
                        if len(c)==pattern_len and pattern.match(c) :
                            #读取到了新的一章
                            if pa and p: 
                                pa.append(p)
                                paras.append(pa)
                                #译文
                                tpa.append(tp)
                                tparas.append(tpa)
                            pa = []
                            p = []
                            tpa=[]
                            tp=[]
                            #
                            lines_index += 1
                            continue
                        c = content[1]
                        #新的一个序列节点
                        if c.isdigit() and int(c)==1 and content[0]=="@" :
                            #如果之前有序列 把序列加入到章节中
                            if p:
                                pa.append(p)
                                #
                                tpa.append(tp)
                                #
                            p = []
                            #译文
                            tp = []
                            #
                            lines_order = 1
                            lines_index += 1
                            continue
                        elif c.isdigit() and int(c)==lines_order+1 and content[0]=="@":
                            #把上一个序号内容加入到文章中
                            pa.append(p)
                            #
                            tpa.append(tp)
                            #
                            lines_order+=1
                            p = []
                            #
                            tp = []
                            lines_index += 1
                            continue
                    #是一个普通的句子
                    p.append(b_sens)
                    #译文中文是一样的
                    tp.append(b_sens)
                    for i in range(paras_len):
                        p.append(full_paras[lines_index+i].strip())
                        tp.append(trans_paras[lines_index+i].strip())
                    lines_index += paras_len
                    continue
                return paras,tparas
        except Exception as e:
            print("catch exception in read_full method::")
            print(repr(e))


    def read_pattern_cn(self, fname):
        self_config = config[os.path.basename(fname)[10:]]
        config_len = self_config["lenght"]
        pattern = re.compile(self_config["pattern"])
        try:
            with open(fname,'r') as f:
                full_paras = f.readlines()
                len_lines = len(full_paras)
                #总的文章结构
                paras = [] #一个二维的数组
                #文章的章节
                pa = []
                lines_index = 0
                while True:
                    #超出数组了
                    if lines_index >= len_lines:
                        paras.append(pa)
                        break
                    #句子之前的数目
                    b_sens = full_paras[lines_index].strip()
                    lines_index += 1
                    #句子的内容
                    sentence = full_paras[lines_index].strip()
                    #每一个段落的句子‘数’
                    paras_len = int(b_sens.split()[0])
                    content = sentence.split()
                    #如果是章节或者序列的标志
                    join_content = "".join(content[:-1])
                    if paras_len==1 and len(join_content) == config_len:
                        if pattern.match(join_content):
                            #print("matched  ",lines_index)
                            #读取到了新的一章 
                            if pa:
                                paras.append(pa)
                            pa = []
                            lines_index += 1
                            continue
                    #是一个普通的句子
                    pa.append(b_sens)
                    for i in range(paras_len):
                        pa.append(full_paras[lines_index+i].strip())
                    lines_index += paras_len
                    continue
                return paras
        except Exception as e:
            traceback.print_exc()
            print("exception  ",lines_index)
            return None


    def read_pattern_jp(self, oname, tname):
        self_config = config[os.path.basename(tname)[10:]]
        config_len = self_config["lenght"]
        pattern = re.compile(self_config["pattern"])
        try:
            with open(oname,'r') as f1,open(tname,"r") as f2:
                o_full_paras = f1.readlines()
                t_full_paras = f2.readlines()
                len_lines = len(o_full_paras)
                #总的文章结构
                o_paras = [] #一个二维的数组
                t_paras = []
                #文章的章节
                o_pa = []
                t_pa = []
                lines_index = 0
                while True:
                    #超出数组了
                    if lines_index >= len_lines:
                        o_paras.append(o_pa)
                        t_paras.append(t_pa)
                        break
                    #句子之前的数目
                    b_sens = o_full_paras[lines_index].strip()
                    lines_index += 1
                    #句子的内容
                    sentence = o_full_paras[lines_index].strip()
                    #每一个段落的句子‘数’
                    paras_len = int(b_sens.split()[0])
                    content = sentence.split()
                    #如果是章节或者序列的标志
                    join_content = "".join(content[:-1])
                    if paras_len==1 and len(join_content) == config_len:
                        if pattern.match(join_content):
                            #print("matched ",join_content)
                            #读取到了新的一章 
                            if o_pa:
                                o_paras.append(o_pa)
                                t_paras.append(t_pa)
                            o_pa = []
                            t_pa = []
                            lines_index += 1
                            continue
                    #是一个普通的句子
                    o_pa.append(b_sens)
                    t_pa.append(b_sens)
                    for i in range(paras_len):
                        o_pa.append(o_full_paras[lines_index+i].strip())
                        t_pa.append(t_full_paras[lines_index+i].strip())
                    lines_index += paras_len
                return o_paras,t_paras
        except Exception as e:
            traceback.print_exc()
            return None,None


    def read_paras(self, paras):
        #f_ori = open(fname,'r')
        lines_ori = paras
        len_ori = len(lines_ori)
        index = 0
        lines_index=0
        para_ori = []
        #记录每一个段落所在的行数
        duan_line=[]  # 段映射到行
        line_duan = []  # 行映射到段
        len_p = 0   # 记录段的数
        lines = 0   #记录行数
        while True:
            #print("lines_index  ",lines_index)
            #print(lines_ori[:lines_index+5])
            read_len = int(lines_ori[lines_index].split()[0])
            lines += read_len # 增加行数
            duan_line.append(lines) # 段落 -》 行数
            lines_index += 1
            for i in range(read_len):
                line_duan.append(len_p) # 行数 -》 段落
                l = lines_ori[lines_index].strip()
                para_ori.append(l)
                lines_index += 1
            if lines_index == len(lines_ori):
              break
            len_p += 1 # 增加段落数
        return para_ori,duan_line,line_duan,len_p
        

    def compare(self ,zh_dir , jp_dir, trans_dir):
        '''
        @paras zh_dir : 中文原本
        @paras tans_dir : 翻译原本
        @paras jp_dir : 日文原本
        '''
        try:
            cn_files = os.listdir(zh_dir)
            for f_name in cn_files:
                self_config = config[os.path.basename(f_name)[10:]]
                p_type = self_config["type"]
                if p_type==0 :
                    cn_paras = self.read_pattern_cn(os.path.join(zh_dir, f_name))
                    jp_paras,trans_paras = self.read_pattern_jp(os.path.join(jp_dir, f_name),os.path.join(trans_dir, f_name))
                    if not cn_paras or not jp_paras or not trans_paras:
                        print("read_pattern func error!!!")
                        continue
                    save_cn = []
                    save_jp = []
                    save_trans = []
                    poss = []
                    for chunk_zh, chunk_jp, chunk_trans in zip(cn_paras, jp_paras, trans_paras):
                        p_cn_paras, cn_duan_line, cn_line_duan= self.read_paras(chunk_zh)
                        p_trans_paras, trans_duan_line, trans_line_duan= self.read_paras(chunk_trans)
                        p_jp_paras, _, _ = self.read_paras(chunk_jp)
                        dt_len = len(cn_duan_line) # 原始的段诺数
                        do_len = len(trans_duan_line) # 翻译的段落数
                        if abs(dt_len-do_len)<200:
                            compare_len = min(dt_len,do_len,200)
                        else:
                            compare_len = min(dt_len,do_len,2 * abs(dt_len-do_len))
                        #print("paras_t ",len(paras_t))
                        pos = self.compare_s(p_cn_paras, p_trans_paras,compare_len,(cn_duan_line,trans_duan_line,cn_line_duan,trans_line_duan))
                        # 保存分析后的文章
                        save_cn.append(p_cn_paras)
                        save_jp.append(p_jp_paras)
                        save_trans.append(p_trans_paras)
                        poss.append(pos)
                    self.save_paras(save_cn, save_trans, save_jp, poss, f_name)
                elif p_type==1 :
                    pattern = re.compile(self_config["pattern"])
                    pattern_len = self_config["lenght"]
                    cn_paras = self.read_full_cn(os.path.join(zh_dir, f_name), pattern, pattern_len)
                    jp_paras,trans_paras = self.read_full_jp(os.path.join(jp_dir, f_name), os.path.join(trans_dir, f_name),  pattern, pattern_len)
                    if not cn_paras or not jp_paras or not trans_paras:
                        print("read_pattern func error!!!")
                        continue
                    save_cn = []
                    save_jp = []
                    save_trans = []
                    poss = []
                    for _chunk_zh, _chunk_jp, _chunk_trans in zip(cn_paras, jp_paras, trans_paras):
                        for chunk_zh, chunk_jp, chunk_trans in zip(_chunk_zh, _chunk_jp, _chunk_trans):
                            p_cn_paras, cn_duan_line, cn_line_duan= self.read_paras(chunk_zh)
                            p_trans_paras, trans_duan_line, trans_line_duan = self.read_paras(chunk_trans)
                            p_jp_paras, _, _= self.read_paras(chunk_jp)
                            dt_len = len(cn_duan_line) # 原始的段诺数
                            do_len = len(trans_duan_line) # 翻译的段落数
                            if abs(dt_len-do_len)<200:
                                compare_len = min(dt_len,do_len,200)
                            else:
                                compare_len = min(dt_len,do_len,2 * abs(dt_len-do_len))
                            #print("paras_t ",len(paras_t))
                            pos = self.compare_s(p_cn_paras, p_trans_paras,compare_len,(cn_duan_line,trans_duan_line,cn_line_duan,trans_line_duan))
                            # 保存分析后的文章
                            save_cn.append(p_cn_paras)
                            save_jp.append(p_jp_paras)
                            save_trans.append(p_trans_paras)
                            poss.append(pos)
                    self.save_paras(save_cn, save_trans, save_jp, poss, f_name)
        except Exception as err:
            traceback.print_exc()
            print("读取文件出现错误::%s"%(str(err)))


    def save_paras(self, _paras_cn, _paras_trasn, _paras_jp, _pos, fname,show_len=2):
        save_dir = self.save_dir
        random_dir = self.random_dir
        save_name = os.path.join(save_dir, fname)
        with open(save_name,'w') as f:
            json_result=[]
            for paras_cn, paras_trasn, paras_jp, pos in zip(_paras_cn, _paras_trasn, _paras_jp, _pos):
                cn_len = len(paras_cn)
                jp_len = len(paras_jp)
                for i,p in  enumerate(pos):
                    match_len = p[2]
                    zh_floor = max(0, p[0]-show_len)
                    zh_ceil = min(cn_len, p[0]+show_len)
                    jp_floor = max(0, p[1]-show_len)
                    jp_ceil = min(jp_len, p[1]+match_len+show_len)
                    content = OrderedDict()
                    content["ZH"] = paras_cn[p[0]]
                    content["JP"] = " || ".join(paras_jp[p[1]:p[1]+match_len])
                    content["JP_TRANS"] = " || ".join(paras_trasn[p[1]:p[1]+match_len])
                    content["CONTEXT_ZH"] = " || ".join(paras_cn[zh_floor:zh_ceil])
                    content["CONTEXT_JP"] = " || ".join(paras_jp[jp_floor:jp_ceil])
                    content["CONTEXT_TRANS"] = " || ".join(paras_trasn[jp_floor:jp_ceil])
                    content["MATCHED_LEN"] = p[2]
                    content["MATCHED_ZH_PARAS"] = p[5]
                    content["MATCHED_JP_PARAS"] = p[4]
                    content["GLEU"]=p[3]
                    content["MATCHED"] = 0

                    json_result.append(content)
            #print(fname,":",len(json_result),"\n")
            f.write(json.dumps(json_result,ensure_ascii=False,indent=4))
            random_name = os.path.join(random_dir,"%s_.random"%fname)
            with open(random_name,"w") as rf:
                rf.write(json.dumps(self.random_select(json_result,50),ensure_ascii=False,indent=4))


    def random_select(self,l,l_len):
        return random.sample(l,l_len)


if __name__ == "__main__":
    begin = time.time()
    cn_dir = "books/pad/cn/"
    jp_dir = "books/pad/jp/"
    trans_dir = "books/trans/jp/"
    save_dir = "books/result/"
    random_dir ="books/random/"
    g = Gleu(save_dir,random_dir)
    g.compare(cn_dir, jp_dir, trans_dir)
    end = time.time()
    print("spend time :",end-begin)