To setup a new Raspi-GPIO-Tag: 
1. Get a clean-and-new image of Raspbian 
2. Update and upgrade
3. Enable UART for GPIO on Raspi (https://www.circuits.dk/setup-raspberry-pi-3-gpio-uart/#:~:text=Setup%20UART%20on%20the%20raspi,1%20in%20%2Fboot%2Fconfig.)
4. check minicom -D with /dev/serial0.
5. Check the status of rc.local service
    5.1 if rc.local is not working, fix it https://www.linuxbabe.com/linux-server/how-to-enable-etcrc-local-with-systemd
    (sudo systemctl status rc-local) to check
    5.2 (sudo systemctl status rc-local) to check
6. create tag_pub_service.sh at ~/tag_mqtt_publisher/ with content as following. Make it executable using chmod +x
    #!/bin/bash
    # starting the python publisher, with console standard output/errors
    # both stored in /home/pi/tag_mqtt_publisher/tag_pub_out.log
    echo "initialization of mqtt pub service - tag"
    nohup python3 -u /home/pi/tag_mqtt_publisher.py >> /home/pi/tag_pub_out.log 2>&1 &
7. copy tag_mqtt_publisher.py to ~/tag_mqtt_publisher/
8. git clone the repo to ~/git/ to sync. (OPTIONAL)
9. modify the /etc/rc.local with the following content:
    #!/bin/sh -x
    #
    # rc.local
    #
    # This script is executed at the end of each multiuser runlevel.
    # Make sure that the script will "exit 0" on success or any other
    # value on error.
    #
    # In order to enable or disable this script just change the execution
    # bits.
    #
    # By default this script does nothing.

    # Print the IP address
    _IP=$(hostname -I) || true
    if [ "$_IP" ]; then
    printf "My IP address is %s\n" "$_IP"
    fi

    chmod +x /home/pi/tag_mqtt_publisher/tag_pub_service.sh
    sh /home/pi/tag_mqtt_publisher/tag_pub_service.sh &

    exit 0
10. make the rc.local executable by chmod +x
11. enable rc-local service following https://www.linuxbabe.com/linux-server/how-to-enable-etcrc-local-with-systemd
12. sudo pip3 install paho-mqtt
    12.1 have to be sudo because rc.local is executed in root, while booting up
    12.2 pip3 because the Python environment is python3


