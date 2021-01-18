mosquitto_sub -h localhost -t test -q 2 -d | xargs -d '\n' -L1 bash -c 'date "+%s%3N ---- $0"' |
  while IFS= read -r line
  do
	  array=($line)
	  #echo "${array[0]}"
	  sent="${array[0]}"
	  echo $sent
	  now=$(date "+%s%3N")
	  diff=`expr $now - $sent`
	  echo ${diff}
  done
