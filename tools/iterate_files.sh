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
			for file in "$locfolder"/*.pcap; do
				echo "-->$file"
				#rm "$file"
				new_file="${file::-5}_fix.pcap"
				FIX_OUT=$(~/pcapfix/pcapfix "$file" -o "$new_file")
				#echo "${FIX_OUT}"	
				if grep -q pcap\ file\ looks\ proper <<<"$FIX_OUT"; then
					cp "$file" "$new_file" 
				fi
				tshark -r "$new_file" -T fields -e frame.number -e frame.time -e ip.src -e ip.dst -e ip.proto -e frame.len -e _ws.col.Protocol -e _ws.col.Info  -E header=y -E separator=, -E quote=d -E occurrence=f > "${new_file::-5}.csv"
			done
		done
	done
    done
done
