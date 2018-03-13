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
from functools  import reduce

class Gleu(object):
    """对翻译后的文本进行gleu值的匹配"""
    def __init__(self, save_dir_duan, random_dir_duan,  save_dir_line, random_dir_line, chunking=1000):
        """
        @paras chuncking:对一个文本的分段大小，默认为500
        """
        self.chunking=chunking
        self.save_dir_duan = save_dir_duan
        self.random_dir_duan = random_dir_duan
        self.save_dir_line = save_dir_line
        self.random_dir_line = random_dir_line
        self.pattern = re.compile('(。|``|\?|,|\'\'|\.|\s|")')
        self.trans_pattern = re.compile("^(``|'').*(``|'')\s。?$")


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


    def acc_gleu_compare(self, ti, oi, len_match=3):
        """
        现存在一个bug 就是在两句有一样的gleu值时 会去匹配正确句子的前向更长者
        """
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


    def acc_match(self, zh_i, t_i, t_index):
        ct = self.acc_t[zh_i]
        acc_o = self.acc_o[t_i]
        len_match = len(acc_o)
        if len_match < t_index + 1:
            return None
        co = acc_o[t_index]
        t_len = len (ct)
        o_len = len(co)
        if not t_len or not o_len:
            return None
        common_length = len(ct&co)
        gleu = min(common_length/t_len,common_length/o_len)
        return gleu


    def acc_gleu_match(self, zh_i, t_ceil_i, t_floor_i, len_match=3):
        """
        修复acc_gleu_compare函数的bug
        """
        max_gleu = 0
        max_zh_i = None
        max_trans_i = None
        match_len = None
        for step in range(len_match):
            for trans_i in range(t_ceil_i, t_floor_i):
                gleu = self.acc_match(zh_i, trans_i, step)
                if gleu is None:
                    continue
                if gleu > max_gleu:
                    max_gleu = gleu
                    max_zh_i = zh_i
                    max_trans_i = trans_i
                    match_len = step
        if max_zh_i is None :return None
        return [max_zh_i, max_trans_i, match_len, max_gleu]


    def rule_getpos(self, zh_i, trans_i, matched_len):
        max_gleu = 0.0
        zh_ngram = self.acc_t[zh_i]
        index = None
        for j in range(matched_len):
            trans_ngram = self.acc_o[trans_i][j]
            if not len(zh_ngram) or not len(trans_ngram):
                continue
            common_length = len(zh_ngram&trans_ngram)
            tmp_gleu = min(common_length/len(zh_ngram),common_length/len(trans_ngram))
            if tmp_gleu > max_gleu:
                max_gleu = tmp_gleu
                index = j
        return index, max_gleu


       
    def compare_duan(self, paras_t, paras_o, len_match = 3, low_gleu=0.1):
        '''
        @paras compare_len: 一对多的匹配  最多匹配len_match个
        @paras  : zh paras
        @paras paras_o : translate paras
        @paras info : 文章参数
        '''
        acc_t = [] #中文段落的ngram
        acc_o = [] #翻译段落的ngram
        tmp_o = []
        for i in paras_t:
            i = "".join(i)
            g = self.ngrams(i)
            acc_t.append(g)
        for i in paras_o:
            i = "".join(i)
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

        len_duan_jp = len(paras_o)  # 获取翻译文章的总的段落数
        len_duan_zh = len(paras_t)
        distance = max(len_duan_jp, len_duan_zh)-min(len_duan_zh, len_duan_jp)
        pos=[]

        #进行段落的对比
        for in_t,t in enumerate(acc_t):
            #如果字符串太短，就没有很大的意义
            #if len(t) <= l:
            #    continue
            max_gleu=0
            o_i = None
            t_i = None
            match_len = None 
            # 计算段落的上下界
            #通过使用匹配段落在原始段落中的比例来计算
            rate_zh_d = (in_t+1)/len_duan_zh
            ceil_rate = max(0,rate_zh_d-0.02)
            floor_rate = min(1,rate_zh_d+0.02)
            begin = max(0,int(len_duan_jp*ceil_rate-0.3*distance))
            if abs(begin-in_t) < 3:
                begin = max(0,in_t-3)
            end = min(len_duan_jp-1,int(len_duan_jp*floor_rate)+distance)
            if abs(end-in_t) < 3:
                end = min(len_duan_jp-1, in_t+3)
            #if in_t ==0:
            #    print(ceil_rate," ",floor_rate,  " ", begin_d, " ", end_d, " ", begin, " ", end)
            
            for index_o in range(begin,end):
                in_o = index_o
                gleu,_match_len = self.acc_gleu_compare(in_t,in_o)
                #print(gleu,_match_len)
                if gleu > max_gleu:
                    max_gleu=gleu
                    t_i = in_t
                    o_i = in_o
                    match_len = _match_len
            if o_i==None : continue
            pos.append((t_i,o_i,match_len,max_gleu))
        return pos

    def compare_line(self, zh_paras, trans_paras, pos, len_match=3):
        acc_l_zh = [] #中文句子加速
        tmp_l_t = []
        acc_l_t = [] #翻译句子加速
        zh_duan_line = [] #中文段落到句子的映射
        zh_line_index = 0
        trans_duan_line = [] #翻译段落到句子的映射
        trans_line_index = 0
        #####
        jiec_zh = []
        jiec_jp = []
        for i in zh_paras:
            zh_duan_line.append(zh_line_index)
            zh_line_index += len(i)
            #计算句子的ngram值
            for tp in i:
                acc_l_zh.append(self.ngrams(tp))
                ######
                jiec_zh.append(tp)
        for i in trans_paras:
            #段落到句子的一个映射
            trans_duan_line.append(trans_line_index)
            trans_line_index += len(i)
            #计算句子的ngram值
            for tp in i:
                tmp_l_t.append(self.ngrams(tp))
                jiec_jp.append(tp)
        len_o = len(tmp_l_t)
        for i in range(len_o):
            acc = []
            tmp = set([])
            for j in range(len_match):
                if i + j >= len_o:
                    break
                tmp |= tmp_l_t[i+j]
                acc.append(tmp.copy())
            acc_l_t.append(acc)
        self.acc_t = acc_l_zh
        self.acc_o = acc_l_t
        
        pos_ = []
        result_pos = []
        #进行句子的对比
        self.acc_t = acc_l_zh
        self.acc_o = acc_l_t
        # s="看 到 墙 边 放 着 羽 毛 球 拍 , 怀 念 之 情 不 禁 油 然 而 生 , 他 以 前 大 学 时 也 参 加 过 羽 毛 球 社 。"
        for p in pos:
            zh_index, trans_index, match_len, _ = p
            ceil_zh_index = zh_duan_line[zh_index]
            floor_zh_index = ceil_zh_index + len(zh_paras[zh_index])
            ceil_trans_index = trans_duan_line[trans_index]
            floor_trans_index = trans_duan_line[trans_index+match_len-1] + len(trans_paras[trans_index+match_len-1])
            for zh_i in range(ceil_zh_index,floor_zh_index):
                pos = self.acc_gleu_match(zh_i, ceil_trans_index, floor_trans_index, len_match)
                if pos is None : continue
                _type = 0
                max_zh_i, max_trans_i, match_len, max_gleu = pos
                if match_len+1 > 1 and self.trans_pattern.match(jiec_zh[zh_i]):
                    index, t_gleu = self.rule_getpos(max_zh_i,max_trans_i,match_len+1)
                    if index is not None and self.trans_pattern.match(jiec_jp[max_trans_i+index]):
                        _type = 1
                        max_trans_i += index
                        match_len = 1
                        max_gleu = t_gleu
                result_pos.append([max_zh_i, max_trans_i, match_len+1, max_gleu, _type])
        return result_pos


    def read_full_cn(self, fname, pattern, pattern_len):
        '''
        把一篇文章分成几个片段，这些片段首先是由章节分开，随后依照章节内的序列号分开
        获得基本单位是段落
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
                    paras_len = int("".join(b_sens.split()[:-1]))
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
                    #p.append(b_sens)
                    tmp_p = []
                    for i in range(paras_len):
                        tmp_p.append(full_paras[lines_index+i].strip())
                    p.append(tmp_p)
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
                    paras_len = int("".join(b_sens.split()[:-1]))
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
                    #p.append(b_sens)
                    #译文中文是一样的
                    #tp.append(b_sens)
                    tmp_zp = []
                    tmp_tp = []
                    for i in range(paras_len):
                        tmp_zp.append(full_paras[lines_index+i].strip())
                        tmp_tp.append(trans_paras[lines_index+i].strip())
                    p.append(tmp_zp)
                    tp.append(tmp_tp)
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
                    paras_len = int("".join(b_sens.split()[:-1]))
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
                    #pa.append(b_sens)
                    tmp_p = []
                    for i in range(paras_len):
                        tmp_p.append(full_paras[lines_index+i].strip())
                    pa.append(tmp_p)
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
                    paras_len = int("".join(b_sens.split()[:-1]))
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
                    #o_pa.append(b_sens)
                    #t_pa.append(b_sens)
                    tmp_op = []
                    tmp_tp = []
                    for i in range(paras_len):
                        tmp_op.append(o_full_paras[lines_index+i].strip())
                        tmp_tp.append(t_full_paras[lines_index+i].strip())
                    o_pa.append(tmp_op)
                    t_pa.append(tmp_tp)
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
        return para_ori,duan_line,line_duan
        

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
                    poss_duan = []
                    for chunk_zh, chunk_jp, chunk_trans in zip(cn_paras, jp_paras, trans_paras):
                        pos_d = self.compare_duan(chunk_zh, chunk_trans)
                        poss_duan.append([pos_d])
                        pos = self.compare_line(chunk_zh, chunk_trans, pos_d)
                        poss.append([pos])
                    self.save_paras_duan(cn_paras, trans_paras, jp_paras, poss_duan, f_name)
                    self.save_paras_line(cn_paras, trans_paras, jp_paras, poss, f_name)
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
                    poss_duan = []
                    for _chunk_zh, _chunk_jp, _chunk_trans in zip(cn_paras, jp_paras, trans_paras):
                        for chunk_zh, chunk_jp, chunk_trans in zip(_chunk_zh, _chunk_jp, _chunk_trans):
                            pos_d = self.compare_duan(chunk_zh, chunk_trans)
                            poss_duan.append([pos_d])
                            pos = self.compare_line(chunk_zh, chunk_trans, pos_d)
                            # 保存分析后的文章
                            save_cn.append(chunk_zh)
                            save_jp.append(chunk_jp)
                            save_trans.append(chunk_trans)
                            poss.append([pos])
                    self.save_paras_duan(save_cn, save_trans, save_jp, poss_duan, f_name)
                    self.save_paras_line(save_cn, save_trans, save_jp, poss, f_name)
        except Exception as err:
            traceback.print_exc()
            print("读取文件出现错误::%s"%(str(err)))


    def save_paras_duan(self, _paras_cn, _paras_trasn, _paras_jp, _pos, fname,show_len=1):
        save_dir = self.save_dir_duan
        random_dir = self.random_dir_duan
        save_name = os.path.join(save_dir, fname)
        with open(save_name,'w') as f:
            json_result=[]
            for paras_cn, paras_trasn, paras_jp, pos in zip(_paras_cn, _paras_trasn, _paras_jp, _pos):
                cn_len = len(paras_cn)
                jp_len = len(paras_jp)
                for p in  pos[0]:
                    match_len = p[2]
                    max_gleu = p[3]
                    zh_floor = max(0, p[0]-show_len)
                    zh_ceil = min(cn_len, p[0]+show_len+1)
                    jp_floor = max(0, p[1]-show_len)
                    jp_ceil = min(jp_len, p[1]+match_len+show_len)
                    content = OrderedDict()
                    content["ZH"] = "".join(paras_cn[p[0]])
                    content["JP"] = " 【分段】 ".join(["".join(jp) for jp in paras_jp[p[1]:p[1]+match_len]])
                    content["JP_TRANS"] = " 【分段】 ".join(["".join(trans) for trans in paras_trasn[p[1]:p[1]+match_len]])
                    content["CONTEXT_ZH"] = " 【分段】 ".join(["".join(zh) for zh in paras_cn[zh_floor:zh_ceil]])
                    content["CONTEXT_JP"] = " 【分段】 ".join(["".join(jp) for jp in paras_jp[jp_floor:jp_ceil]])
                    content["CONTEXT_TRANS"] = " 【分段】 ".join(["".join(trans) for trans in paras_trasn[jp_floor:jp_ceil]])
                    content["MATCHED_LEN"] = p[2]
                    content["MATCHED_ZH_PARAS"] = p[0]
                    content["MATCHED_JP_PARAS"] = p[1]
                    content["GLEU"]=p[3]
                    content["ZH_DUAN_LEN"] = cn_len
                    content["JP_DUAN_LEN"] = jp_len
                    content["MATCHED"] = 0
                    json_result.append(content)
            #print(fname,":",len(json_result),"\n")
            f.write(json.dumps(json_result,ensure_ascii=False,indent=4))
            random_name = os.path.join(random_dir,"%s_.random"%fname)
            with open(random_name,"w") as rf:
                rf.write(json.dumps(self.random_select(json_result,50),ensure_ascii=False,indent=4))


    def save_paras_line(self, zh_paras, trans_paras, jp_paras, poss, fname, show_len=3):
        save_dir = self.save_dir_line
        random_dir = self.random_dir_line
        save_name = os.path.join(save_dir, fname)
        with open(save_name,'w') as f:
            json_result=[]
            for paras_cn, paras_trans, paras_jp, pos in zip(zh_paras, trans_paras, jp_paras, poss):
                f1 = lambda x,y:x+y
                paras_cn = reduce(f1, paras_cn)
                paras_trans = reduce(f1, paras_trans)
                paras_jp = reduce(f1, paras_jp)
                cn_len = len(paras_cn)
                jp_len = len(paras_jp)
                for p in  pos[0]:
                    match_len = p[2]
                    max_gleu = p[3]
                    _type = p[4]
                    if max_gleu < 0.09:
                        _type = 2 if not _type else 3
                    zh_floor = max(0, p[0]-show_len)
                    zh_ceil = min(cn_len, p[0]+show_len+1)
                    jp_floor = max(0, p[1]-show_len)
                    jp_ceil = min(jp_len, p[1]+match_len+show_len)
                    content = OrderedDict()
                    content["ZH"] = paras_cn[p[0]]
                    content["JP"] = "【分行】".join(paras_jp[p[1]:p[1]+p[2]])
                    content["JP_TRANS"] = "【分行】".join(paras_trans[p[1]:p[1]+p[2]])
                    content["CONTEXT_ZH"] = " 【分行】 ".join(paras_cn[zh_floor:zh_ceil])
                    content["CONTEXT_JP"] = " 【分行】 ".join(paras_jp[jp_floor:jp_ceil])
                    content["CONTEXT_TRANS"] = " 【分行】 ".join(paras_trans[jp_floor:jp_ceil])
                    content["MATCHED_LEN"] = p[2]
                    content["GLEU"] = p[3]
                    content["TYPE"] = _type
                    content["MATCHED"] = 0
                    json_result.append(content)
            #print(fname,":",len(json_result),"\n")
            f.write(json.dumps(json_result,ensure_ascii=False,indent=4))
            random_name = os.path.join(random_dir,"%s_.random"%fname)
            with open(random_name,"w") as rf:
                rf.write(json.dumps(self.random_select(json_result,50),ensure_ascii=False,indent=4))

    def random_select(self,l,l_len):
        return random.sample(l,l_len)

    def deep(self,a):
        if isinstance(a,list):
            if len(a) > 0:
                return 1 + self.deep(a[0])
        else:
            return 0


if __name__ == "__main__":
    begin = time.time()
    cn_dir = "books/pad/cn/"
    jp_dir = "books/pad/jp/"
    trans_dir = "books/trans/jp/"
    save_dir_duan = "books/result2/duan/"
    random_dir_duan ="books/random2/duan/"

    save_dir_line = "books/result2/line/"
    random_dir_line = "books/random2/line/"

    g = Gleu(save_dir_duan, random_dir_duan, save_dir_line, random_dir_line)
    g.compare(cn_dir, jp_dir, trans_dir)
    end = time.time()
    print("spend time :",end-begin)