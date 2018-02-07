#!/bin/bash
export CLASSPATH=../libs/stanford-corenlp-2017-04-14-build.jar
java edu.stanford.nlp.process.PTBTokenizer -preserveLines ../word.txt > ../result.txt
