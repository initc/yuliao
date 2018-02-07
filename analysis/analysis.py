import os
import argparse
import json
import math
import numpy as np
from collections import OrderedDict

DIR_ = "../books/evaluate"
ANALYSIS = "result/analysis_basic.txt"
PARAS_ANALYSIS = "result/analysis_paras.txt"

def basic_info(file, p=True):
    file_name = file
    with open(os.path.join(DIR_, file_name),"r") as f:
        json_result = json.loads(f.read())
    analysis = OrderedDict()
    analysis["success"] = 0
    analysis["one_to_many"] = 0
    analysis["one_to_one"] = 0
    analysis["one_no_match"] = 0
    analysis["many_to_one"] = 0
    analysis["many_to_many"] = 0
    analysis["many_no_match"] = 0
    count = 0
    for r in json_result:
        match_type = r["MATCHED"]
        if match_type == 0:
            analysis["success"] = analysis.get("success",0)+1
            count += 1
        elif match_type ==1:
            analysis["one_to_many"] = analysis.get("one_to_many",0)+1
        elif match_type ==2:
            analysis["one_to_one"] = analysis.get("one_to_one",0)+1
        elif match_type ==3:
            analysis["one_no_match"] = analysis.get("one_no_match",0)+1
        elif match_type ==4:
            analysis["many_to_one"] = analysis.get("many_to_one",0)+1
        elif match_type ==5:
            analysis["many_to_many"] = analysis.get("many_to_many",0)+1
        elif match_type ==6:
            analysis["many_no_match"] = analysis.get("many_no_match",0)+1
        elif match_type ==7:
            analysis["zh_lenght_error"] = analysis.get("many_no_match",0)+1
    analysis["success_rate"] = count / len(json_result)
    if p:
        print(json.dumps(analysis, ensure_ascii=False, indent=4))
    else:
        with open(ANALYSIS,'w') as f:
            f.write(json.dumps(analysis, ensure_ascii=False, indent=4))

def paras_info(filename,p=True):
    file_name = filename
    with open(os.path.join(DIR_, file_name),"r") as f:
        json_result = json.loads(f.read())
    analysis = OrderedDict()
    analysis["success"] = []
    analysis["one_to_many"] = []
    analysis["one_to_one"] = []
    analysis["one_no_match"] = []
    analysis["many_to_one"] = []
    analysis["many_to_many"] = []
    analysis["many_no_match"] = []
    analysis["zh_lenght_error"] = []
    count = 0
    for r in json_result:
        match_type = r["MATCHED"]
        if match_type == 0:
            info = analysis["success"]
        elif match_type ==1:
            info = analysis["one_to_many"]
        elif match_type ==2:
            info = analysis["one_to_one"]
        elif match_type ==3:
            info = analysis["one_no_match"]
        elif match_type ==4:
            info = analysis["many_to_one"]
        elif match_type ==5:
            info = analysis["many_to_many"]
        elif match_type ==6:
            info = analysis["many_no_match"]
        elif match_type ==7:
            info = analysis["zh_lenght_error"]
        info.append(abs(r["MATCHED_ZH_PARAS"]-r["MATCHED_JP_PARAS"]))
    result = OrderedDict()
    for k,v in analysis.items():
        if not len(v): continue
        v = np.array(v)
        result[k] = [len(v),np.mean(v),0 if len(v)==1 else np.cov(v).tolist(), int(np.min(v)), int(np.max(v))]
    if p:
        print(json.dumps(result, ensure_ascii=False, indent=4))
    else:
        with open(PARAS_ANALYSIS,'w') as f:
            f.write(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument('-b', action="store_true", dest="b", help="get basic info")
    parse.add_argument("-d", action="store_true", dest="d", help="分析段落差距值")
    parse.add_argument("-p", action="store_true", default=False, dest="p", help="print the result")
    parse.add_argument('-f', '--file', help='analyze the file')
    args = parse.parse_args()
    if args.b:
        file_name = args.file
        basic_info(file_name, args.p)
    elif args.d:
        file_name = args.file
        paras_info(file_name, args.p)
    else:
        pass
