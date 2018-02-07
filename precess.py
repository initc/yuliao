#coding:utf-8 -*-  
import math
import time
import os
import pickle
import re

class Gleu(object):
    """对翻译后的文本进行gleu值的匹配"""
    def __init__(self, save_dir, chunking=1000):
        """
        @paras chuncking:对一个文本的分段大小，默认为500
        """
        self.chunking=chunking
        self.save_dir = save_dir
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
        ct = self.chunk_t[ti]
        co = self.chunk_o[oi]
        t_len = len (ct)
        o_len = len(co)
        if not t_len or not o_len:
            return 0.0
        common_length = len(ct&co)
        return min(common_length/t_len,common_length/o_len)


    def compare_s(self, chunk_t, chunk_o,l=3,low_gleu=0.1):
        """chunk是由句子构成的
        对比两个chunking的gleu值，返回一个数据，是一个元组(ti,oi)
        记录他们原始的位置
        @paras chunk_t:翻译后的语料,是一个字符串数组
        @paras chunk_o:原始的语料，是一个字符串数组
        @paras l:对字符串长度的限制
        @paras gleu:对gleu值的限制
        @return pos:对应的位置
        """
        acc_t = []
        acc_o = []
        for i in chunk_t:
            g = self.ngrams(i)
            acc_t.append(g)
        for i in chunk_o:
            g = self.ngrams(i)
            acc_o.append(g)
        self.chunk_t = acc_t
        self.chunk_o = acc_o
        pos=[]
        for in_t,t in enumerate(chunk_t):
            #如果字符串太短，就没有很大的意义
            if len(t) <= l:
                continue
            max_gleu=0
            o_i = None
            t_i = None
            for in_o,o in enumerate(chunk_o):
                if len(o) <= l:
                    continue
                #gleu = self.gleu_compare(t,o)
                gleu = self.acc_gleu_compare(in_t,in_o)
                if gleu > max_gleu:
                    max_gleu=gleu
                    t_i = in_t
                    o_i = in_o
            if max_gleu < low_gleu:
                continue
            pos.append((t_i,o_i,max_gleu))
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

    def read_paras(self, filename, mode='line'):
        """读取一个文件,@filename 里面应该是一个句子
        @paras filename:文件的名称
        @paras mode:['line', 'para']: line:一行是一个句子  para:组合多行形成一个段落
        @return paras:二维的文章
        """
        f = open(filename,'r')
        lines = f.readlines()
        lines_len = len(lines)
        index = 0
        lines_index=0
        para = []
        if mode=='line':
            while True:
                read_len = int(lines[lines_index].split()[0])
                lines_index += 1
                for i in range(read_len):
                    l = lines[lines_index].strip()
                    para.append(l)
                    lines_index += 1
                if lines_index == len(lines):
                    break
        else:
            while True:
                p=[]
                read_len=int(lines[lines_index].split()[0])
                lines_index += 1
                for i in range(read_len):
                    p.append(lines[lines_index].strip())
                    lines_index += 1
                para.append(p)
                if lines_index == len(lines):
                    break
        return para
    
    def divede_paras(self,paras_t,paras_o,paras_c):
        """
        @paras paras_t:目标-翻译后的文章
        @paras paras_o:原始对比的中文文章
        @paras paras_c:翻译前对比的日文文章
        """
        chunking = self.chunking
        len_t = len(paras_t)
        len_o = len(paras_o)
        len_c = len(paras_c)
        if len_c != len_t:
            print('error : 日文与中文长度不等')
            return None,None,None
        if not chunking:
            p_l = math.abs(len_t-len_o)
            if p_l > 300:
                p_l /= p_l
            chunking = 500
            chunking += p_l
        chunk_t = []
        chunk_o = []
        chunk_c = []
        ct = []
        cc = []
        co = []
        count = 0
        chunking_k = math.ceil(len_t / chunking)
        for i in range(len_t):
            ct.append(paras_t[i])
            cc.append(paras_c[i])
            count += 1
            if count == chunking:
                chunk_t.append(ct)
                chunk_c.append(cc)
                count = 0
                ct = []
                cc = []
        if count :
            chunk_t.append(ct)
            chunk_c.append(cc)
            count = 0
        chunking = math.ceil(len_o / chunking_k)
        for i in range(len_o):
            co.append(paras_o[i])
            count += 1
            if count == chunking:
                chunk_o.append(co)
                count += 0
                co = []
        if count :
            chunk_o.append(co)

        return chunk_t,chunk_o,chunk_c
        
    def compare(self ,t_dir ,o_dir ,c_dir ,mode='line'):
        # 获取三个存放的目录
        t_files = os.listdir(t_dir)
        o_files = os.listdir(o_dir)
        c_files = os.listdir(c_dir)
        for fname in t_files:
            # 获取文件夹中的文件名
            t_n = os.path.join("%s/%s"%(t_dir,fname))
            o_n = os.path.join("%s/%s"%(o_dir,fname))
            c_n = os.path.join("%s/%s"%(c_dir,fname))
            try:
                # 读取每一个文件 line模式 或者para模式读取
                paras_t = self.read_paras(t_n,mode)
                paras_o = self.read_paras(o_n,mode)
                paras_c = self.read_paras(c_n,mode)
                # 对读取后的统一分段
                chunks_t,chunks_o,chunks_c = self.divede_paras(paras_t,paras_o,paras_c)
                if mode=='line':
                    chunks_len = len(chunks_t)
                    poss=[]
                    for i in range(chunks_len):
                        #目前只对比相同大小的chunks 日后再来优化
                        if i >= len(chunks_o):continue
                        # 对每一个段 对比获取pos坐标
                        pos = self.compare_s(chunks_t[i], chunks_o[i])
                        poss.append(pos)
                    # 保存分析后的文章
                    self.save_paras(chunks_t,chunks_o,chunks_c,poss,fname)
                else:
                    chunks_len = len(chunks_t)
                    # save_chunks 中保存的是一个系列已经匹配完成的句子集合
                    save_chunks_t = []
                    save_chunks_o = []
                    save_chunks_c = []
                    # 指定的句子集合中的位置
                    poss = []
                    for i in range(chunks_len):
                        if i >= len(chunks_o):continue
                        # 获取每一个段落匹配的坐标
                        pos = self.compare_c(chunks_t[i],chunks_o[i])
                        tmp_chunks_t = chunks_t[i]
                        tmp_chunks_o = chunks_o[i]
                        tmp_chunks_c = chunks_c[i]
                        # 对每一个匹配后的段落在进行一次匹配
                        for p in pos:
                            i = pos[0] # 目标文章--翻译文章
                            j = pos[1] # 原始文章--中文文章
                            # 获取小段落的位置
                            s_pos = self.compare_s(tmp_chunks_t[i],tmp_chunks_o[j])
                            # 存储小段落的信息
                            save_chunks_t.append(tmp_chunks_t[i])
                            save_chunks_o.append(tmp_chunks_o[j])
                            save_chunks_c.append(tmp_chunks_c[i])
                            # 存储位置信息
                            poss.append(s_pos)
                    self.save_paras(save_chunks_t,save_chunks_o,save_chunks_c,poss,fname)
            except Exception as err:
                print("读取文件%s出现错误::"%(fname,str(err)))
    
    def save_paras(self, chunks_t, chunks_o, chunks_c, poss, fname):
        save_dir = self.save_dir
        save_name = '%s/matched_%s'%(save_dir, fname)
        with open(save_name,'w') as f:
            for i,pos in  enumerate(poss):
                c_t = chunks_t[i]
                c_o = chunks_o[i]
                c_c = chunks_c[i]
                for p in pos:
                    f.write('gleu is %.3f :: 目标::%s 原始::%s 日原::%s \n'%(p[2],c_t[p[0]],c_o[p[1]],c_c[p[0]]))




class PrecessParas(object):
    """对日语的语料的预处理，为之后的翻译做准备"""
    def __init__(self,para_dir):
        self.para_dir = para_dir

    def read_paras(self,file_name):
        try :
            with open(file_name,'r') as f :
                paras_lines = f.readlines()
                para_num = 0
                index = 0
                result = []
                tmp_index = []
                while True :
                    #pad之后数字后面加了。号
                    line_num = int(paras_lines[index].split()[0])
                    tmp_index.append(line_num)
                    index += 1
                    for i in range(line_num):
                        # 读取正文 句子 文件名词 段落位置 句子位置
                        result.append([paras_lines[index],file_name.strip().split('/')[-1],para_num,i])
                        index += 1
                    para_num += 1
                    if index >= len(paras_lines):
                        break
        except Exception:
                print("读取文件 %s 出现异常错误"%file_name)
        finally:
            return result,tmp_index
            
    def sort_paras(self):
        files = os.listdir(self.para_dir)
        res=[]
        files_index={}
        #
        for f in files:
            child = os.path.join("%s/%s"%(self.para_dir,f))
            if os.path.isfile(child):
                # 通过行来读取文件
                tmp,file_index = self.read_paras(child)
                files_index[f.strip()]=file_index
                res += tmp
        # 排序完需要知道他在原始的位置
        res.sort(key=lambda x : len(x[0]))
        with open('before_sort.txt','w') as f:
            for l in res:
                f.write("%s\n"%l[0])
        with open('transform/sort.cache','wb') as f:
            pickle.dump((res,files_index),f)
        return res


def recover_paras(paras_txt,paras_cache,zh_dir):
    try:
        with open(paras_cache,'rb') as f:
            sorted_cache,files_index =  pickle.load(f)
        with open(paras_txt,'r') as f:
            lines = f.readlines()
        names = []
        for n in sorted_cache:
            names.append(n[1].strip())
        names = set(names)
        for i,l in enumerate(lines):
            sorted_cache[i][0]=l.strip()
        sorted_cache.sort(key=lambda x : (x[1],x[2],x[3]))
        #dubug 
        #dubug_file = open('dubug.txt','w')
        #for l in sorted_cache:
        #    dubug_file.write('%s===>%s ::  %d ; %d \n'%(l[0].strip(),l[1],l[2],l[3]))
        tmp_file_name = sorted_cache[0][1]
        tmp_file_lines = files_index[tmp_file_name]
        line_size = len(sorted_cache)
        i = 0
        while True:
            file_name = "%s/%s"%(zh_dir,tmp_file_name)
            with open(file_name,'w') as f:
                for j in tmp_file_lines:
                    f.write("%d\n"%j)
                    for k in range(j):
                        f.write("%s\n"%sorted_cache[i+k][0].strip())
                    i += j
                if i < line_size:
                    tmp_file_name = sorted_cache[i][1]
                    tmp_file_lines = files_index[tmp_file_name]
                else:
                    break
    except Exception as err:
        print('读取文件失败！！！%s'%str(err))
    finally:
        print('\nfinally')










