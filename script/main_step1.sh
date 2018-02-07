#!/bin/bash
python3 addToken.py
ruby fenju_cn.rb
ruby fenju_jp.rb
./token.sh
./pad.sh
python3 ParasTools.py sort
