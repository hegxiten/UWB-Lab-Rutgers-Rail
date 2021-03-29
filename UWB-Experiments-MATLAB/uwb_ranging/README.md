# Decawave PANS Rail Vehicle Ranging Application (updated on 03.28.2021)

## Major function and fundamental protocols:
* Range the coupler-to-coupler distances between neighbor vehicles.
    * (with relative short ranging of UWB - nominally 60 meters/180 feet). 

* Designed for maintenance-of-way vehicles in work mode 
    * Can be scaled-up for any other feasible rail (or general) vehicle ranging applications
* Master/Slave configuration on rail vehicles.

## Getting Started

### Hardware
* For each vehicle: 4 x DWM1001-Dev devices, 1 x Raspberry Pi 3 B+, USB Cables, and other applicances
* (Optionally) MHS-3.5inch Display w. case, or similar portable displays: 
    * available at https://www.amazon.com/gp/product/B07N38B86S/ref=ppx_yo_dt_b_asin_title_o03_s00?ie=UTF8&psc=1 (by 03.28.2021)
    * install the corresponding driver if display is added. 
* (Optionally) 1602A LCD Display w. breadboard. 
    * available at https://www.amazon.com/gp/product/B08F7S2GZ4/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1 (by 03.28.2021)
    * use ./lcd.py to drive this LCD display.  Necessary code adjustment is needed. 

### Software Dependencies

* Dependencies:
    * Python 3.7
        * pySerial 

* Notes:
    * An updated firmware is needed for master devices of the vehicle. No need for slaves.
        * Firmware binary: ./dwm-accelerometer-enabled_fw2.bin (or request the access via email)
    * An Android application needs to be installed into a Android smart phone. 
        * Compile from: https://github.com/hegxiten/DRTLS_Manager_RU_Dev
    * Raspberry Pi driver/control scripts are available at this folder. 
        * Main script: ./uwb_master.py


### Installing

* Compile Android on the Android controlling device to control over BLE. 
* Compile and download the Firmware to the master devices. Can optionally use UWB OTA/BLE OTA to download the firmware. 
* On the Raspberry Pi:
    ```
    mkdir ~/git && cd ~/git && mkdir ~/uwb_ranging
    git clone https://github.com/hegxiten/UWB-Lab-Rutgers-Rail
    cd ~/git/UWB-Lab-Rutgers-Rail/UWB_Experiments-MATLAB/uwb_ranging/
    cp * ~/uwb_ranging
    mkdir ~/.config/autostart
    cp ./uwb_ranging.desktop ~/.config/autostart/
    sudo reboot
    ```

### Executing program

* The program should be executed on start of the Rasperry Pi. 
* logs are saved into ~/uwb_ranging/ranging_log.log


## Author and Contributor
Zezhou Wang (https://github.com/hegxiten)
Sanyam Jain (https://github.com/jainsanyam786)
