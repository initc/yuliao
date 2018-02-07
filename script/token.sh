#!/bin/bash
export CLASSPATH=../libs/stanford-corenlp-2017-04-14-build.jar
path=('../books/fenju/cn' '../books/fenju/jp')
out=('../books/token/cn' '../books/token/jp')
for ((i=0;i<2;i++));do
echo "token.....   ${path[$i]}"
filelist=`ls ${path[$i]}`
for ff in $filelist;do
echo $ff
java edu.stanford.nlp.process.PTBTokenizer -preserveLines "${path[$i]}/$ff" > "${out[$i]}/token_$ff"
done
echo "done"
done
