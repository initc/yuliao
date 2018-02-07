import os
import pickle
import argparse
class PrecessParas(object):
    """对日语的语料的预处理，为之后的翻译做准备"""
    def __init__(self,para_dir):
        self.para_dir = para_dir

    def read_paras(self,file_name):
        '''
        @paras file_name: 需要读取的文件
        @return result : 返回一个四元组的数组，四元组分别存储着【正文句子 文件名子 段落位置 句子位置】
        这个四元组信息用来之后的排序 来获得原始的数据
        @return tmp_index : 存储了每一个段落的句子数目 为之后的复原提供数据
        '''
        try :
            with open(file_name,'r') as f :
                paras_lines = f.readlines()
                #记录段落的位置
                para_num = 0
                #记录读取文件的位置
                index = 0
                #最后的结果集
                result = []
                tmp_index = []
                while True :
                    #pad之后数字后面加了。号
                    line_num = int(paras_lines[index].split()[0])
                    tmp_index.append(line_num)
                    index += 1
                    for i in range(line_num):
                        # 读取正文句子 文件名子 段落位置 句子位置
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
        '''
        读取被token，pad之后的日语文章 然后依文章句子的长短来排序 从短到长 
        把排序后的四元组缓存起来 为之后的恢复提供信息
        '''
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
        print(len(res))
        with open('../books/trans/before_sort.txt','w') as f:
            for l in res:
                f.write("%s\n"%l[0].strip())
        with open('../books/trans/sort.cache','wb') as f:
            pickle.dump((res,files_index),f)
        return res


def recover_paras(paras_txt,paras_cache,zh_dir):
    '''
    @paras paras_txt : 翻译后的句子 
    @paras paras_cache : 翻译之前的缓存
    @paras zh_dir : 最后恢复的文件的存储位置
    '''
    try:
        with open(paras_cache,'rb') as f:
            sorted_cache,files_index =  pickle.load(f)
        with open(paras_txt,'r') as f:
            lines = f.readlines()
        names = []
        for n in sorted_cache:
            names.append(n[1].strip())
        #获取一共有多少个文件名
        names = set(names)
        #把翻译后的句子赋值到翻译之前的句子
        #print('debug 1')
        #print(len(lines),' ',len(sorted_cache))
        for i,l in enumerate(lines):
            sorted_cache[i][0]=l.strip()
        #print('dubug 2')
        #恢复 通过名称  段落数 句子数
        sorted_cache.sort(key=lambda x : (x[1],x[2],x[3]))
        #dubug 
        #dubug_file = open('dubug.txt','w')
        #for l in sorted_cache:
        #    dubug_file.write('%s===>%s ::  %d ; %d \n'%(l[0].strip(),l[1],l[2],l[3]))
        #恢复文件
        tmp_file_name = sorted_cache[0][1]
        #当前名字对应的 段落句子数的数组
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

if __name__ == '__main__':
    parse = argparse.ArgumentParser()
    parse.add_argument('op')
    args = parse.parse_args()
    op = args.op
    trams = PrecessParas('../books/pad/jp')
    if op == 'sort':
        trams.sort_paras()
    else:
        recover_paras('../books/trans/trans_result.txt','../books/trans/sort.cache','../books/trans/jp')

