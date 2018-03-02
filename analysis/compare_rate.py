import json
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="compare precess1 to precess2")
    parser.add_argument("origin", action="store")
    parser.add_argument("target", action="store")
    args = parser.parse_args()
    origin = json.loads(open(args.origin,"r").read())
    target = json.loads(open(args.target,"r").read())
    succ = 0
    fail = 0
    for o in origin:
        if o["MATCHED"] != 0:
            continue
        for t in target:
            if o["ZH"] == t["ZH"]:
                if o["JP"] == t["JP"]:
                    print("匹配成功")
                    succ += 1
                    break
                else:
                    print("匹配失败")
                    fail += 1
                    break
    print("success rate is :",succ/(succ+fail))