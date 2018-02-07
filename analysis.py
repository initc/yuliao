import os
import argparse
import json
from collections import OrderedDict

DIR_ = "books/evaluate"
ANALYSIS = "analysis.txt"


if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument('-f','--file',help='analyze the file')
    args = parse.parse_args()
    if args.file :
        file_name = args.file
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
        with open(ANALYSIS,'w') as f:
            f.write(json.dumps(analysis, ensure_ascii=False, indent=4))
