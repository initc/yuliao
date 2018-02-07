#!/usr/bin/ruby
# -*- coding: utf-8 -*-
require 'pragmatic_segmenter'
FILE_DIR = "../books/origin/jp"
SAVE_DIR = "../books/fenju/jp"

puts 'segmenter starting'
i = 0
file_list = Dir::entries(FILE_DIR)
file_list.each do |file_name|
    if file_name == '.' or file_name == '..'
        next
    end
    file_path = FILE_DIR + '/' + file_name
    save_path = SAVE_DIR + '/' + file_name
    if File.exist?(save_path)
    	next
    end
    puts file_name
    count=Hash.new(0)
    size = 0
    lines = IO.readlines(file_path)
    lines.each do |text|
        ps = PragmaticSegmenter::Segmenter.new(text:text) #ja zh   
        if ps.segment.length < 1
            next
        end
        line = Array.new
        len = 0
        ps.segment.each do |seg|
            if seg.strip().length < 2
                next
            end
            len += 1
            line.push(seg)
        end
        if len < 1
            next
        end
        count[len]+=1
        size += 1
        f = File.open(save_path,'a+')
        f.puts len
        f.puts line
        f.close
    end
    puts count.to_s
    puts "一共有 #{size.to_s} 段落，段落只有一句的一共有 #{count[1]} 行"
    puts "一段以一句子的概率是 : " + (count[1] / size.to_f).to_s
    i += 1
    if i%100 == 0
        puts i.to_s + ' file has been segment'
    end

end

puts "DOWN"
