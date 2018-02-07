#!/bin/bash
path=("../books/token/jp" "../books/token/cn")
out=("../books/pad/jp" "../books/pad/cn")
for((i=0;i<2;i++));do
    echo "pad......  ${path[$i]}"
    filelist=`ls ${path[$i]}`
    if [ $i -eq 0 ];then
        type='jp'
    else
        type='cn'
    fi
    for ff in $filelist;do
    echo $ff
    python2 ../libs/generate_training_sample_shooter.py "${path[$i]}/$ff" "$type"
    mv "${path[$i]}/$ff.padded" "${out[$i]}/pad_$ff"
    done

done
