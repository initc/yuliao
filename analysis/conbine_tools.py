#coding:utf-8 -*-
import argparse
import json
if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument("origin", action="store")
    parse.add_argument("target", action="store")
    args = parse.parse_args()
    origin = args.origin
    target_ = args.target
    with open(origin,"r") as f1,open(target_,"r") as f2:
        origin = json.loads(f1.read())
        target = json.loads(f2.read())
        for t in target:
            for o in origin:
                if t["ZH"] == o["ZH"]:
                    #print(999)
                    t["ZH_DUAN_LEN"] = o["ZH_DUAN_LEN"]
                    t["JP_DUAN_LEN"] = o["JP_DUAN_LEN"]
                    t["MATCHED_ZH_PARAS"] = o["MATCHED_ZH_PARAS"]
                    t["MATCHED_JP_PARAS"] = o["MATCHED_JP_PARAS"]
                    break
        f2 = open("%s_a"%target_,"w")
        f2.write(json.dumps(target, ensure_ascii=False, indent=4))
