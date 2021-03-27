#!/bin/bash
# starting the python publisher, with console standard output/errors
# both stored in /home/pi/uwb_ranging/ranging_log.log
PROCESS_NAME="uwb_master.py"
while true;
do
	time=$(date "+%Y-%m-%d %H:%M:%S.%6N local")
	# number of ranging processes, expecting 1
	NUM=`ps aux | grep "python3 -u" | grep -v "grep" | grep -w ${PROCESS_NAME} | wc -l`
	if [ "${NUM}" -lt "1" ];then
		echo "\n\n[${time} Daemon] publisher process killed or not yet started. Starting..." >> /home/pi/uwb_ranging/ranging_log.log
		nohup python3 -u "/home/pi/uwb_ranging/${PROCESS_NAME}" >> /home/pi/uwb_ranging/ranging_log.log 2>&1 &
	elif [ "${NUM}" -gt "1" ];then
		echo "\n\n[${time} Daemon] multiple publisher processes killed all. Restarting..." >> /home/pi/uwb_ranging/ranging_log.log
		killall -9 $PROCESS_NAME
	fi
	# kill the zombie process (STAT T)
	NUM_STAT=`ps aux | grep ${PROCESS_NAME} | grep T | grep -v grep | wc -l`
	if [ "${NUM_STAT}" -gt "1" ];then
		echo "\n\n[${time} Daemon] zomebie publisher processes found. killed all. Restarting..." >> /home/pi/uwb_ranging/ranging_log.log
		killall -9 $PROCESS_NAME
	fi
	sleep 5s
done
exit 0

