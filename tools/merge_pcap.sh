#!/bin/bash

folder=$1

for sub_folder in "$folder"/*; do
    find . -name ".DS_Store" -print -delete
    for simfolder in "$sub_folder"/*; do
    	for qosfolder in "$simfolder"/*; do
        	echo "$qosfolder"
		find . -name ".DS_Store" -print -delete
		for locfolder in "$qosfolder"/*; do
			echo "$locfolder"
			find . -name ".DS_Store" -print -delete
			#for file in "$locfolder"/*_fix.pcap; do
			#	echo "-->$file"
			#done
			mergecap -w "${locfolder}"/merged.pcap "$locfolder"/*_fix.pcap
		done
	done
    done
done
