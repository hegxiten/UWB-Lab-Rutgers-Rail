import time, serial
import inspect


ERROR_CLS = {
        0 : "OK",
        1 : "unknown command or broken TLV frame",
        2 : "internal error",
        3 : "invalid parameter",
        4 : "busy",
        5 : "operation not permitted",
        6 : "unknown error (non API error)"
    }

SCALE_TO_MM = {
        "mm"    : 1,
        "cm"    : 10,
        "m"     : 1000,
        }

SCALE_TO_100MS = {
        "100ms" : 1,
        "s"     : 10,
        "min"   : 600,
        }

def read_single_TLV_frame(port, cutoff_bytes=0):
    if not cutoff_bytes:
        _TL_header = port.read(2)
        if _TL_header:
            _frame_value = port.read(_TL_header[1])
            return _TL_header + _frame_value
        else:
            return b''
    else:
        return port.read(cutoff_bytes)
    
def read_all_TLV(port, expecting=0, timeout=1):
    if expecting:
        TLV_frames = [read_single_TLV_frame(port) for n in range(expecting)]
    else:
        TLV_frames = []
        _time_cnt = 0
        while port.inWaiting() or _time_cnt < timeout:
            if port.inWaiting():
                TLV_frames.append(read_single_TLV_frame(port))
                _time_cnt = 0
            elif _time_cnt < timeout:
                time.sleep(0.01)
                _time_cnt += 0.01
            else:
                break
    return TLV_frames


def hex_in_string(bytes_to_show):
    """ Show hexadecimal in string format
    """
    return ''.join('0x{:02x} '.format(letter) for letter in bytes_to_show)


def verbose_request(TLV_bytes):
    _func_name = inspect.stack()[1][3]
    print("[{}] TLV Written to serial: {}".format(_func_name, hex_in_string(TLV_bytes)))


def verbose_response(TLV_bytes, err_code, func_name):
    print("[{}] Responded TLV: {}".format(func_name, hex_in_string(TLV_bytes)))
    if err_code == 0:
        print("[{}] Success".format(func_name))
    else:
        print("[{}] Error with error code: {}, message: {}"
        .format(func_name, err_code, ERROR_CLS[err_code]))


def error_handler(TLV_response, err_code, func_name):
    if err_code != 0:
        raise ValueError("[{}]: Error returned as code {}: {}."
                        .format(func_name, err_code, ERROR_CLS[err_code]))


def pg_delay_encode(pg_delay):
    return -1


def tx_power_encode(tx_power):
    return -1


def pg_delay_decode(pg_delay_bytes):
    return -1, -1


def tx_power_decode(tx_power_bytes):
    return -1, -1

#------------------------------------------------------------------------------------------#
############################################################################################
############################################################################################
############################################################################################
#------------------------------------------------------------------------------------------#
# DWM1001 API functions start

def dwm_pos_set(t, coords, qual_fact_percent, unit="mm", verbose=False):
    """ API Section 5.3.1
    API Sample TLV Request:
    Type    |Length |Value-position (13B)
    0x01    |0x0D   |x (4B, little), y (4B, little), z (4B, little), 
                    |percentage quality factor (1B)

    API Sample TLV Resonse:
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00
    ------------------------------------
    This API function set the default position of the node. Default position is not used when in tag mode
    but is stored anyway so the module can be configured to anchor mode and use the value previously
    set by dwm_pos_set. This call does a write to internal flash in case of new value being set, hence
    should not be used frequently as can take, in worst case, hundreds of milliseconds.
    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    if unit not in ("mm", "cm", "m"):
        raise ValueError("[{}]: Invalid input unit".format(_func_name))
    TYPE, LENGTH, VALUE = b'\x01', b'\x0D', b''
    
    [x, y, z] = [c * SCALE_TO_MM[unit] for c in coords]
    pos_bytes = b''
    for dim in [x, y, z]:
        pos_bytes += dim.to_bytes(4, byteorder='little', signed=True)
    pos_bytes += qual_fact_percent.to_bytes(1, byteorder='little', signed=False)
    
    VALUE = pos_bytes
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # Parsing the returned TLV value
    # do nothing
    return [err_code]


def dwm_pos_get(t, verbose=False):
    """ API Section 5.3.2
    API Sample TLV Request:
    Type    |Length
    0x02    |0x00  

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-position (13B)
    0x41    |0x0D   |x (4B, little), y (4B, little), z (4B, little), 
                    |percentage quality factor (1B)
    ------------------------------------
    This API function obtain position of the node. If the current position of the node is not available, the
    default position previously set by dwm_pos_set will be returned.
    ------------------------------------
    :return: 
        [x, y, z, qual_fact_percent, err_code] unit in millimeter
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x02', b'\x00', b''  
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    # Parsing the returned TLV value
    _dim_idx_pos = [5, 9, 13]
    x, y, z, qual_fact_percent = [float("nan")] * 4
    [x, y, z] = [
        int.from_bytes(dim_bytes, byteorder='little', signed=True) 
        for dim_bytes in [TLV_response[idx:idx+4] for idx in _dim_idx_pos]
        ]
    qual_fact_percent = TLV_response[-1]

    return [x, y, z, qual_fact_percent, err_code]


def dwm_upd_rate_set(t, act_upd_intval, sta_upd_intval, unit="100ms", verbose=False):
    """ API Section 5.3.3
    API Sample TLV Request:
    Type    |Length |Value-update_rate (4B)
    0x03    |0x04   |active/stationary position update interval in multiples
                    |of 100 milliseconds (2B each, little, unsigned)

    API Sample TLV Resonse:
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00
    ------------------------------------
    This API function sets the update rate and the stationary update rate of the position in unit of 100
    milliseconds. Stationary update rate must be greater or equal to normal update rate. This call does a
    write to the internal flash in case of new value being set, hence should not be used frequently as can
    take, in worst case, hundreds of milliseconds.
    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    if unit not in ("100ms", "s", "min"):
        raise ValueError("[{}]: Invalid input unit".format(_func_name))
    
    TYPE, LENGTH, VALUE = b'\x03', b'\x04', b''
    
    [act_upd_intval, sta_upd_intval] = [i * SCALE_TO_100MS[unit] 
                                for i in [act_upd_intval, sta_upd_intval]]
    if act_upd_intval > sta_upd_intval:
        raise ValueError("[{}]: Stationary interval must be greater or equal to \
                          Active interval".format(_func_name))
    upd_bytes = b''
    for upd in [act_upd_intval, sta_upd_intval]:
        upd_bytes += upd.to_bytes(2, byteorder='little', signed=False)
    
    VALUE = upd_bytes
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # Parsing the returned TLV value
    # do nothing
    return [err_code]

def dwm_upd_rate_get(t, verbose=False):
    """ API Section 5.3.4
    API Sample TLV Request:
    Type    |Length
    0x04    |0x00  

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-update_rate (4B)
    0x45    |0x04   |active/stationary position update interval in multiples
                    |of 100 milliseconds (2B each, little, unsigned)
    ------------------------------------
    This API function gets position update rate. 
    ------------------------------------
    :return: 
        [act_upd_intval, sta_upd_intval, err_code] unit in milliseconds
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x04', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    # Parsing the returned TLV value
    _upd_idx_pos = [5, 7]
    act_upd_intval, sta_upd_intval = [float("nan")] * 2
    [act_upd_intval, sta_upd_intval] = [
        100 * int.from_bytes(upd_bytes, byteorder='little', signed=False) 
        for upd_bytes in [TLV_response[idx:idx+2] for idx in _upd_idx_pos]
        ]
    
    return [act_upd_intval, sta_upd_intval, err_code]


def dwm_cfg_tag_set(t, 
                    stnry_en=True, 
                    meas_mode=0, 
                    low_power_en=False, 
                    loc_engine_en=True, 
                    enc_en=False, 
                    led_en=True, 
                    ble_en=True, 
                    uwb_mode=2, 
                    fw_upd_en=True, 
                    verbose=False):
    """ API Section 5.3.5
    API Sample TLV Request:
    Type    |Length |Value-cfg_tag (2B)
    0x05    |0x02   |16-bit integer, 2-byte, configuration of the tag
                    |(* BYTE 1 *)
                    |(bits 3-7) reserved
                    |(bit 2) stnry_en
                    |(bits 0-1) meas_mode : 0 - TWR, 1-3 reserved
                    |(* BYTE 0 *)
                    |(bit 7) low_power_en
                    |(bit 6) loc_engine_en
                    |(bit 5) enc_en
                    |(bit 4) led_en
                    |(bit 3) ble_en
                    |(bit 2) fw_update_en
                    |(bits 0-1) uwb_mode 
    API Sample TLV Resonse:
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00
    ------------------------------------
    This API function configures the node as tag with given options.
    BLE option can't be enabled together with encryption otherwise the configuration is considered
    invalid and it is refused. Encryption can't be enabled if encryption key is not set.
    This call does a write to internal flash in case of new value being set, hence should not be used
    frequently as can take, in worst case, hundreds of milliseconds. Note that this function only sets the
    configuration parameters. To make effect of the settings, users should issue a reset command
    (dwm_reset()), see section 5.3.13 for more detail.
    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x05', b'\x02', b''
    
    if ble_en and enc_en:
        raise ValueError("[{}]: Refused. BLE option can't be enabled together \
                          with encryption.".format(_func_name))
    cfg_tag_byte_1 = 0b00000000
    cfg_tag_byte_0 = 0b00000000
    
    cfg_tag_byte_1 = cfg_tag_byte_1 | (stnry_en << 5)
    cfg_tag_byte_1 = cfg_tag_byte_1 | (meas_mode << 6)
    
    cfg_tag_byte_0 = cfg_tag_byte_0 | (low_power_en << 0)
    cfg_tag_byte_0 = cfg_tag_byte_0 | (loc_engine_en << 1)
    cfg_tag_byte_0 = cfg_tag_byte_0 | (enc_en << 2)
    cfg_tag_byte_0 = cfg_tag_byte_0 | (led_en << 3)
    cfg_tag_byte_0 = cfg_tag_byte_0 | (ble_en << 4)
    cfg_tag_byte_0 = cfg_tag_byte_0 | (fw_upd_en << 5)
    cfg_tag_byte_0 = cfg_tag_byte_0 | (uwb_mode << 6)
    
    VALUE = cfg_tag_byte_0.to_bytes(1, byteorder='little', signed=False) + \
            cfg_tag_byte_1.to_bytes(1,  byteorder='little', signed=False)
    output_bytes = TYPE + LENGTH + VALUE
    print(output_bytes)
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # Parsing the returned TLV value
    # do nothing
    return [err_code]
    

def dwm_cfg_anchor_set( t, 
                        initiator=True, 
                        bridge=False, 
                        enc_en=False, 
                        led_en=True, 
                        ble_en=True, 
                        uwb_mode=2, 
                        fw_upd_en=True, 
                        verbose=False):
    """ API Section 5.3.6
    API Sample TLV Request:
    Type    |Length |Value-cfg_anchor (2B)
    0x07    |0x02   |16-bit integer, 2-byte, configuration of the anchor
                    |(* BYTE 1 *)
                    |(bits 2-7) reserved
                    |(bits 0-1) reserved
                    |(* BYTE 0 *)
                    |(bit 7) initiator
                    |(bit 6) bridge
                    |(bit 5) enc_en
                    |(bit 4) led_en
                    |(bit 3) ble_en
                    |(bit 2) fw_update_en
                    |(bits 0-1) uwb_mode 
    API Sample TLV Resonse:
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00
    ------------------------------------
    Configure node as anchor with given options. BLE option can't be enabled together with encryption
    otherwise the configuration is considered invalid and it is refused.
    Encryption can't be enabled if encryption key is not set. This call requires reset for new configuration
    to take effect (dwm_reset). Enabling encryption on initiator will cause automatic enabling of
    encryption of all nodes that have the same encryption key set (dwm_enc_key_set). This allows to
    enable encryption for whole network that has the same pan ID (network ID) and the same
    encryption key remotely from one place.
    This call does a write to internal flash in case of new value being set, hence should not be used
    frequently and can take in worst case hundreds of milliseconds.
    ------------------------------------
    :return: 
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x07', b'\x02', b''

    if ble_en and enc_en:
        raise ValueError("[{}]: Refused. BLE option can't be enabled together \
                          with encryption.".format(_func_name))

    cfg_anc_byte_1 = 0b00000000
    cfg_anc_byte_0 = 0b00000000

    cfg_anc_byte_0 = cfg_anc_byte_0 | (initiator << 0)
    cfg_anc_byte_0 = cfg_anc_byte_0 | (bridge << 1)
    cfg_anc_byte_0 = cfg_anc_byte_0 | (enc_en << 2)
    cfg_anc_byte_0 = cfg_anc_byte_0 | (led_en << 3)
    cfg_anc_byte_0 = cfg_anc_byte_0 | (ble_en << 4)
    cfg_anc_byte_0 = cfg_anc_byte_0 | (fw_upd_en << 5)
    cfg_anc_byte_0 = cfg_anc_byte_0 | (uwb_mode << 6)
    
    VALUE = cfg_anc_byte_0.to_bytes(1, byteorder='little', signed=False) + \
            cfg_anc_byte_1.to_bytes(1,  byteorder='little', signed=False)
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # Parsing the returned TLV value
    # do nothing
    return [err_code]

def dwm_cfg_get(t, verbose=False):
    """ API Section 5.3.7
    API Sample TLV Request:
    Type    |Length
    0x08    |0x00  

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-cfg_node (2B)
    0x46    |0x02   |16-bit integer, configuration of the node
                    |(* BYTE 1 *)
                    |(bit 5) mode : 0 - tag, 1 - anchor
                    |(bit 4) initiator
                    |(bit 3) bridge
                    |(bit 2) stnry_en
                    |(bits 0-1) meas_mode : 0 - TWR, 1-3 not supported
                    |(* BYTE 0 *)
                    |(bit 7) low_power_en
                    |(bit 6) loc_engine_en
                    |(bit 5) enc_en 
                    |(bit 4) led_en
                    |(bit 3) ble_en
                    |(bit 2) fw_update_en
                    |(bits 0-1) uwb_mode
    ------------------------------------
    This API function obtains the configuration of the node.
    ------------------------------------
    :return: 
        [node_cfg, err_code]
    """ 
    _func_name = inspect.stack()[0][3]

    TYPE, LENGTH, VALUE = b'\x08', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)

    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    # Parsing the returned TLV value
    cfg_node_byte_0, cfg_node_byte_0_str = TLV_response[-2], bin(TLV_response[-2])[2:]
    cfg_node_byte_1, cfg_node_byte_1_str = TLV_response[-1], bin(TLV_response[-1])[2:]
    
    cfg_node = {
        "mode":         int(cfg_node_byte_1_str[5]),
        "initiator":    True if int(cfg_node_byte_1_str[4]) else False,
        "bridge":       True if int(cfg_node_byte_1_str[3]) else False,
        "stnry_en":     True if int(cfg_node_byte_1_str[2]) else False,
        "meas_mode":    int(cfg_node_byte_1_str[0:2], 2),
        "low_power_en": True if int(cfg_node_byte_0_str[7]) else False,
        "loc_engine_en":True if int(cfg_node_byte_0_str[6]) else False,
        "enc_en":       True if int(cfg_node_byte_0_str[5]) else False,
        "led_en":       True if int(cfg_node_byte_0_str[4]) else False,
        "ble_en":       True if int(cfg_node_byte_0_str[3]) else False,
        "fw_update_en": True if int(cfg_node_byte_0_str[2]) else False,
        "uwb_mode":     int(cfg_node_byte_0_str[0:2], 2),
    }
    
    return [cfg_node, err_code]

def dwm_sleep(t, verbose=False):
    """ API Section 5.3.8
    API Sample TLV Request:
    Type    |Length
    0x0A    |0x00  
    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           
    ------------------------------------
    This API function puts the module into sleep mode. Low power option must be enabled otherwise an
    error will be returned.
    ------------------------------------
    """
    _func_name = inspect.stack()[0][3]

    TYPE, LENGTH, VALUE = b'\x0A', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]


def dwm_anchor_list_get(t, verbose=False, timeout=5):
    """ API Section 5.3.9, modified by Zezhou Wang
    API Sample TLV Request:
    Type    |Length |Value
    0x0B    |0x01   |page_number

    page_number: when the returned values become greater than 253 Bytes (maximum TLV length), 
    it will separate into extra pages.
    
    API Sample TLV Resonse Example 1 (3 anchors):
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value (1 + 16 * Anchors bytes).............................................           
    0x56    |0x31   |uint8_t (1B)               |...
                    |number of elements         |...
                    |encoded in the value       |...
                    |0x03                       |...
    |Value (Cont.) .........................................................................|..................................
    |uint16_t (2B)          |3×int32_t (12B)    |int8_t - RSSI (1B) |uint8_t - seat (1B)    |..................................
    |UWB address in little  |position coords xyz|                   |                       |(Cont.) anchor nr.2 anchor nr.3...
    |endian                 |in little endian   |                   |                       |..................................
    |-----------------------------------anchor nbr.1 (16B)----------------------------------|..................................

    Sample (4 anchors):
    "40 01 00 56 41 04" 
    "84 c5 (Addr)| 3c 05 00 00 (x) | da 07 00 00 (y) | f4 0b 00 00 (z) | b2 (RSSI) | 00 (seat)" 
    "0c 0c (Addr)| dc 05 00 00 (x) | c4 09 00 00 (y) | b8 0b 00 00 (z) | b2 (RSSI) | 01 (seat)" 
    "28 13 (Addr)| 18 06 00 00 (x) | ce 04 00 00 (y) | 52 0d 00 00 (z) | b3 (RSSI) | 02 (seat)" 
    "1c 9a (Addr)| 00 fa 00 00 (x) | 50 c3 00 00 (y) | 50 46 00 00 (z) | 81 (RSSI) | 04 (seat)"

    API Sample TLV Resonse Example 2 (no anchor):
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00          
    Type    |Length |Value              
    0x56    |0x01   |uint8_t -              
                    |number of elements     
                    |encoded in the value   
                    |0x0F                   

    ------------------------------------
    This API function reads list of surrounding anchors. Works for anchors only. Anchors in the list can be
    from the same network or from the neighbor network as well.
    Requesting page number that ain't exist will make the device frozen. Power-off and restart is needed. 
    ------------------------------------
    :return:
        list of hash maps (key-value pairs for anchors), length unit in millimeter
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x0B', b'\x01', b''

    _page_nbr = 0
    _anchor_bytes_nbr_by_page = []
    # while loop used for determining how many pages are there.
    # if polling a page number that doesn't exist, the device crashes.
    while True:
        _page_polling_bytes = TYPE + LENGTH + _page_nbr.to_bytes(1, byteorder="little", signed=False)
        t.reset_output_buffer()
        t.reset_input_buffer()
        t.write(_page_polling_bytes)
        TLV_frames = read_all_TLV(t, expecting=2)
        _page_polling_response = TLV_frames[0]
        err_code = _page_polling_response[2] if _page_polling_response[0:2] == b'\x40\x01' else 6
        error_handler(_page_polling_response, err_code, _func_name)
        anchor_nbr_in_this_page = TLV_frames[1][2]
        if anchor_nbr_in_this_page != 0:
            anchor_bytes = TLV_frames[1][3:]
            if len(anchor_bytes) != anchor_nbr_in_this_page * 16:
                raise ValueError("[{}]: Bytes for anchors do not match specs: 16 bits per anchor on page {}. Expecting {} anchors. Got {} Bytes."
                                    .format(_func_name, _page_nbr, anchor_nbr_in_this_page, t.inWaiting()))
            if verbose:
                verbose_response(anchor_bytes, err_code, _func_name)
            _anchor_bytes_nbr_by_page.append([anchor_bytes, anchor_nbr_in_this_page])
        else:
            break
        _page_nbr += 1

    # parse TLV frames into anchor hashmaps
    anchors = []
    for [B, nbr] in _anchor_bytes_nbr_by_page:
        for i in range(nbr):
            _anchor_i = {}
            _anchor_i['addr'] = "{0:0{1}X}"\
                            .format(int.from_bytes(B[i*16 + 0:i*16 + 2],        byteorder='little', signed=False), 4)
            _anchor_i['x'] =        int.from_bytes(B[i*16 + 2  :i*16 + 6],      byteorder='little', signed=True)
            _anchor_i['y'] =        int.from_bytes(B[i*16 + 6  :i*16 + 10],     byteorder='little', signed=True)
            _anchor_i['z'] =        int.from_bytes(B[i*16 + 10 :i*16 + 14],     byteorder='little', signed=True)
            _anchor_i['RSSI'] = B[i*16 + 14]
            _anchor_i['seat'] = B[i*16 + 15]
            anchors.append(_anchor_i)

    return [anchors, err_code]


def dwm_loc_get(t, verbose=False):
    """ API Section 5.3.10, modified by Zezhou Wang
    API Sample TLV Request:
    Type    |Length 
    0x0C    |0x00   
    
    API Sample TLV Resonse Example 1 (Tag node):
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-position (13B)                               |...    
    0x41    |0x0D   |x (4B, little), y (4B, little), z (4B, little),    |...
            |       |percentage quality factor (1B)                     |...
    Type    |Length |Value-Number of anchors w. distances (1B) .............    
    0x49    |0x3d   |0x03                                               |...
    |Value (cont.) (13 * Anchors bytes).................................................................|..........
    |UWB address (2B)       |distance_to (4B)   |distance quality factoir (1B)  |anchor position (13B)  |..................................
    |-----------------------------------distance to anchor nbr.1 (20B)----------------------------------|(Cont.) anchor nr.2 anchor nr.3...
    
    Sample (3 anchors used for tag ranging)
    *Note*: the distance to anchor is not always non-zero.
    "40 01 00"
    "41 0d 9e 05 00 00 30 05 00 00 00 03 00 00 16" 
    "49 3d 03 ... 
    87 82 (Addr)| 32 01 00 00 (dist) | 64 (qual) | 78 05 00 00 (x) | 9a 06 00 00 (y) | e8 03 00 00 (z) | 64 (qual) AN1
    28 13 (Addr)| 03 01 00 00 (dist) | 64 (qual) | e0 06 00 00 (x) | 1a 04 00 00 (y) | e8 03 00 00 (z) | 64 (qual) AN2
    84 c5 (Addr)| 5e 02 00 00 (dist) | 64 (qual) | 74 04 00 00 (x) | fc 03 00 00 (y) | e8 03 00 00 (z) | 64 (qual) AN3
    ------------|-----(another anchor could be here as ranging with 4 anchors simulatenously)----------|----------(AN4)

    
    API Sample TLV Resonse Example 2 (Anchor node):
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-position (13B)                               |...    
    0x41    |0x0D   |x (4B, little), y (4B, little), z (4B, little),    |...
            |       |percentage quality factor (1B)                     |...
    Type    |Length |Value-Number of anchors w. distances (1B) .............    
    0x48    |0xC4   |0x0F                                               |...
    |Value (cont.) (13 * Anchors bytes).........................................|..................................
    |UWB address (8B)       |distance_to (4B)   |distance quality factoir (1B)  |..................................
    |-----------------------distance to anchor nbr.1 (13B)----------------------|(Cont.) anchor nr.2 anchor nr.3...


    Sample (4 anchors):
    "40 01 00"
    "48 c4 0f ... 
    "84 c5 (Addr)| 3c 05 00 00 (x) | da 07 00 00 (y) | f4 0b 00 00 (z) | b2 (RSSI) | 00 (seat)" 
    "0c 0c (Addr)| dc 05 00 00 (x) | c4 09 00 00 (y) | b8 0b 00 00 (z) | b2 (RSSI) | 01 (seat)" 
    "28 13 (Addr)| 18 06 00 00 (x) | ce 04 00 00 (y) | 52 0d 00 00 (z) | b3 (RSSI) | 02 (seat)" 
    "1c 9a (Addr)| 00 fa 00 00 (x) | 50 c3 00 00 (y) | 50 46 00 00 (z) | 81 (RSSI) | 04 (seat)"

    API Sample TLV Resonse Example 2 (no anchor):
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00          
    Type    |Length |Value              
    0x56    |0x01   |uint8_t -              
                    |number of elements     
                    |encoded in the value   
                    |0x0F                   

    ------------------------------------
    Get last distances to the anchors (tag is currently ranging to) and the associated position. The
    interrupt is triggered when all TWR measurements have completed and the LE has finished. If the LE
    is disabled, the distances will just be returned. This API works the same way in both Responsive and
    Low-Power tag modes. 
    ------------------------------------
    :return:
        [pos, anchors, node_mode, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x0C', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=3)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)

    # Parsing the returned TLV value
    # node mode: 0x49/0d73 (Tag - 0) - Tag; 0x48/0d72 (Anchor - 1)
    node_mode = abs(73 - TLV_frames[2][0])
    is_tag = True if node_mode == 0 else False

    pos = {}
    pos_bytes = TLV_frames[1][2:]
    _dim_idx_pos = [0, 4, 8]
    pos['x'], pos['y'], pos['z'], pos['qual'] = [float("nan")] * 4
    [pos['x'], pos['y'], pos['z']] = [
        int.from_bytes(dim_bytes, byteorder='little', signed=True) 
        for dim_bytes in [pos_bytes[idx:idx+4] for idx in _dim_idx_pos]
        ]
    pos['qual'] = pos_bytes[-1]
    
    anchors = []
    anchor_nbr = TLV_frames[2][2]
    anchor_bytes = TLV_frames[2][3:]
    if is_tag:
        if len(anchor_bytes) == anchor_nbr * 20:
            for i in range(anchor_nbr):
                _anchor_i = {}
                _anchor_i['addr'] = "{0:0{1}X}"\
                                .format(int.from_bytes(anchor_bytes[i*20 + 0  :i*20 + 2],   byteorder='little', signed=False), 4)
                _anchor_i['dist_to'] =  int.from_bytes(anchor_bytes[i*20 + 2  :i*20 + 6],   byteorder='little', signed=False)
                _anchor_i['qual'] =     anchor_bytes[6]
                _anchor_i['x'] =        int.from_bytes(anchor_bytes[i*20 + 7  :i*20 + 11],  byteorder='little', signed=True)
                _anchor_i['y'] =        int.from_bytes(anchor_bytes[i*20 + 11 :i*20 + 15],  byteorder='little', signed=True)
                _anchor_i['z'] =        int.from_bytes(anchor_bytes[i*20 + 15 :i*20 + 19],  byteorder='little', signed=True)
                anchors.append(_anchor_i)
        else:
            raise ValueError("[{}] (Mode in {}): Bytes for anchors do not match specs: 20 bits per anchor. Expecting {} anchors. Got {} Bytes."
                                    .format(_func_name, "tag" if is_tag else "anchor", anchor_nbr, len(anchor_bytes)))
    else:
        # It seems like the firmware has not implemented the following codes. 
        # The returns are always zero
        if len(anchor_bytes) == anchor_nbr * 13:
            for i in range(anchor_nbr):
                _anchor_i = {}
                _anchor_i['addr'] = "{0:0{1}X}"\
                                .format(int.from_bytes(anchor_bytes[i*13 + 0  :i*13 + 8],   byteorder='little', signed=False), 8)
                _anchor_i['dist_to'] =  int.from_bytes(anchor_bytes[i*13 + 8  :i*13 + 12],   byteorder='little', signed=False)
                _anchor_i['qual'] =     anchor_bytes[12]
                anchors.append(_anchor_i)
        else:
            raise ValueError("[{}] (Mode in {}): Bytes for anchors do not match specs: 13 bits per anchor. Expecting {} anchors. Got {} Bytes."
                                    .format(_func_name, "tag" if is_tag else "anchor", anchor_nbr, len(anchor_bytes)))
    
    return [pos, anchors, node_mode, err_code]

def dwm_baddr_set(t, ble_addr, verbose=False):
    """ API Section 5.3.11
    API Sample TLV Request:
    Type    |Length |Value-ble_addr (6B in little endian)
    0x0F    |0x06   |0x01 0x23 0x45 0x67 0x89 0xab
    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           
    ------------------------------------
    Sets the public Bluetooth address used by device. New address takes effect after reset. This call does
    a write to internal flash in case of new value being set, hence should not be used frequently as can
    take, in worst case, hundreds of milliseconds.
    ------------------------------------
    :return: 
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x0F', b'\x06', b''
    
    ble_addr_bytes = bytearray.fromhex(ble_addr)
    ble_addr_bytes.reverse()
    # Convert to little endian

    VALUE = ble_addr_bytes
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # Parsing the returned TLV value
    # do nothing
    return [err_code]

def dwm_baddr_get(t, verbose=False):
    """ API Section 5.3.12
    API Sample TLV Request:
    Type    |Length 
    0x10    |0x00   
    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-ble_addr (6B in little endian)
    0x5F    |0x06   |0x01 0x23 0x45 0x67 0x89 0xab
    ------------------------------------
    Get Bluetooth address currently used by device.
    ------------------------------------
    :return: 
        [BLE Address, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x10', b'\x00', b''
    
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    # Parsing the returned TLV value
    ble_addr_bytes = TLV_frames[1][-6:]
    ble_addr = "{0:0{1}X}".format(int.from_bytes(ble_addr_bytes, byteorder='little', signed=False), 6)
    
    return [ble_addr, err_code]

def dwm_stnry_cfg_set(t, stnry_sensitivity=0, verbose=False):
    """ API Section 5.3.13
    API Sample TLV Request:
    Type    |Length |Value-stnry_sensitivity (1B)
    0x11    |0x01   |stnry_sensitivity = 8-bit integer, valid values:
                    |0: low [512 mg]
                    |1: normal [2048 mg]
                    |2: high [4064 mg]

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00       
    ------------------------------------
    Writes configuration of the stationary mode which is used by tag node. The configuration can be
    written even if stationary detection is disabled (see dwm_cfg_tag_set). Writes internal nonvolatile
    memory so should be used carefully. New sensitivity setting takes effect immediately if stationary
    mode is enabled. Default sensitivity is “HIGH”.
    ------------------------------------
    :return: 
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    if stnry_sensitivity not in (0, 1, 2):
        raise ValueError("[{}]: Invalid input unit".format(_func_name))
    
    TYPE, LENGTH, VALUE = b'\x11', b'\x01', b''
    stnry_sensitivity_bytes = stnry_sensitivity.to_bytes(1, byteorder='little', signed=False)
    VALUE = stnry_sensitivity_bytes
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # Parsing the returned TLV value
    # do nothing
    return [err_code]

def dwm_stnry_cfg_get(t, verbose=False):
    """ API Section 5.3.14
    API Sample TLV Request:
    Type    |Length 
    0x12    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-stnry_sensitivity (1B)
    0x4A    |0x01   |0: low [512 mg]
                    |1: normal [2048 mg]
                    |2: high [4064 mg]
                    
    ------------------------------------
    Reads configuration of the stationary mode which is used by tag node. The configuration can be read
    even if stationary detection is disabled (see dwm_cfg_tag_set).
    ------------------------------------
    :return: 
        [stnry_sensitivity, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x12', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    # Parsing the returned TLV value
    stnry_sensitivity = TLV_frames[1][-1]
    
    return [stnry_sensitivity, err_code]

def dwm_factory_reset(t, verbose=False):
    """ API Section 5.3.15
    API Sample TLV Request:
    Type    |Length 
    0x13    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-stnry_sensitivity (1B)
    0x4A    |0x01   |0: low [512 mg]
                    |1: normal [2048 mg]
                    |2: high [4064 mg]
                    
    ------------------------------------
    This API function puts node to factory settings. Environment is erased and set to default state.
    Resets the node. This call does a write to internal flash, hence should not be used frequently and can
    take in worst case hundreds of milliseconds.
    ------------------------------------
    :return: 
        [stnry_sensitivity, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x13', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    #do nothing
    return [err_code]

def dwm_reset(t, verbose=False):
    """ API Section 5.3.16
    API Sample TLV Request:
    Type    |Length 
    0x14    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           
                    
    ------------------------------------
    This API function reboots the module.
    ------------------------------------
    :return: 
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x14', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    #do nothing
    return [err_code]

def dwm_ver_get(t, verbose=False):
    """ API Section 5.3.17
    API Sample TLV Request:
    Type    |Length 
    0x15    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |Type   |Length |Value-fw_version (4B)                              |...
    0x40    |0x01   |0x00           |0x50   |0x04   |maj, min, patch, ver: bytes 0-3, firmware version  |
                                                    |maj : byte 0, 8-bit number, MAJOR                  |
                                                    |min : byte 1, 8-bit number, MINOR                  |
                                                    |patch:byte 2, 8-bit number, PATCH                  |
                                                    |ver : byte 3, 8-bit number, res and var            |
                                                    |   res : byte 3, bits 4-7, 4-bit number, RESERVED  |
                                                    |   var : byte 3, bits 0-3, 4-bit number, VARIANT   |
    Type    |Length |Value-cfg_version (4B) |Type   |Length |Value-hw_version (4B) 
    0x51    |0x04   |0x00 0x07 0x01 0x00    |0x52   |0x04   |0x2a 0x00 0xca 0xde
                    
    ------------------------------------
    This API function obtains the firmware version of the module. 
    ------------------------------------
    :return: 
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x15', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE

    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=4)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    ver = {}
    # Parsing the returned TLV value
    fw_version = {}
    fw_version_bytes = TLV_frames[1][-4:]
    fw_version['maj'], fw_version['min'], fw_version['patch'] \
        = fw_version_bytes[0], fw_version_bytes[1], fw_version_bytes[2]
    fw_version['res'] = fw_version_bytes[3] >> 4
    fw_version['var'] = fw_version_bytes[3] & 0x0F
    ver['fw_version'] = fw_version

    cfg_version = int.from_bytes(TLV_frames[2][-4:], byteorder='little', signed=False)
    ver['cfg_version'] = cfg_version
    hw_version = int.from_bytes(TLV_frames[3][-4:], byteorder='little', signed=False)
    ver['hw_version'] = hw_version
    
    return [ver, err_code]

def dwm_uwb_cfg_set(t, pg_delay, tx_power, verbose=False):
    """ API Section 5.3.18. Modified by Zezhou Wang
    API Sample TLV Request:
    Type    |Length |Value-pg_delay (1B); tx_power(4B) 
    0x17    |0x05   |0xC3 (pg_delay) 0x85 0x65 0x45 0x25 (tx_power)
                    |pg_delay: Transmitter Calibration – Pulse Generator Delay (TC_PGDELAY)
                    |tx_power: TX Power Control (TX_POWER)

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00 
                    
    ------------------------------------
    Sets UWB configuration parameters.

    TC_PGDELAY is set to 0xC5 by default, which is the incorrect value for channel 5. This value should be set to
    0xC0 before proceeding to use the default configuration. TC_PGDELAY sets an 8-bit configuration register (2A:0B) 
    for setting the Pulse Generator Delay value. This effectively sets the width of transmitted pulses effectively
    setting the output bandwidth. 
    The value used here depends on the TX channel selected by               | Tx_Channel | Recommended PGDELAY values |
    the TX_CHAN configuration in Register file: 0x1F – Channel Control.     |     1      |           0xC9             |
    Recommended values are given on right table. note however that these    |     2      |           0xC2             |
    values may need to be tuned for spectral regulation compliance          |     3      |           0xC5             |
    depending on external circuitry.                                        |     4      |           0x95             |
                                                                            |     5      |           0xC0             |
                                                                            |     7      |           0x93             |

    The TX_POWER setting is 0x1E080222 by default. This value should be set to 0x0E082848 before proceeding
    to use the default configuration. The TX_POWER (transmitter output power) can be adjusted using this Register file: 
    0x1E – Transmit Power Control. This contains four octets each of which specifies a separate transmit power setting. 
    These separate settings are applied by the IC in one of two ways. These two alternatives are described in section 
    7.2.31.2 – Smart Transmit Power Control and section 7.2.31.3 – Manual Transmit Power Control below. The choice 
    between these two alternatives is selected by the setting of the DIS_STXP bit in Register file: 0x04 – System
    Configuration.

    The transmitter output power can be adjusted using this Register file: 0x1E – Transmit Power Control. This
    contains four octets each of which specifies a separate transmit power setting. These separate settings are
    applied by the IC in one of two ways. These two alternatives are described in section 7.2.31.2 – Smart
    Transmit Power Control and section 7.2.31.3 – Manual Transmit Power Control below. The choice between
    these two alternatives is selected by the setting of the DIS_STXP bit in Register file: 0x04 – System
    Configuration.

    Units of TX Power Control:
    Each power control octet, in Register file: 0x1E – Transmit Power Control, specifies the power as a
    combination of a coarse gain parameter and a fine         |Bit 7 |6 |5      |4  |3  |2  |1  |0  |
    gain parameter.                                           | Coarse (DA)     |   Fine (Mixer)    |
    The gain control range is 33.5 dB consisting of 32 fine   |  Setting        |      Setting      |
    (mixer gain) control steps of 0.5 dB and 7 coarse (DA     |_________________|___________________|
    gain) steps of 3 dB, see Figure 26. For the best          |000 = 18 dB gain |00000 =0.0 dB gain |
    first.                                                    |010 = 12 dB gain |00001 =0.5 dB gain |
    For optimum performance, (as noted in section             |011 = 9 dB gain  |00010 =1.0 dB gain |
    7.2.31), manufacturers have to calibrate the TX power     |100 = 6 dB gain  |00011 =1.5 dB gain |
    of each unit to account for IC to IC variations and       |101 = 3 dB gain  |00100 =2.0 dB gain |
    different IC to antenna losses. Usually the TX power is   |110 = 0 dB gain  |00101 =2.5 dB gain |
    set to the maximum allowed by spectral emission           |111 = OFF –      |......             |
    regulations (-41.3 dBm/MHz) and such that no other        |     No output   |11010 =13.0 dB gain|
    out-of-band limits are exceeded.                          |                 |11011 =13.5 dB gain|
                                                              |                 |11100 =14.0 dB gain|
                                                              |                 |11101 =14.5 dB gain|
                                                              |                 |11110 =15.0 dB gain|
                                                              |                 |11111 =15.5 dB gain|

    REG:1E:00 – TX_POWER – Smart Transmit Power Control (When DIS_STXP = 0)
    |31 30 29 28 27 26 25 24 | 23 22 21 20 19 18 17 16 | 15 14 13 12 11 10 9 8 | 7 6 5 4 3 2 1 0
    |       BOOSTP125        |       BOOSTP250         |        BOOSTP500      |     BOOSTNORM
    |       0x0E             |       0x08              |        0x02           |     0x22

    REG:1E:00 – TX_POWER – Manual Transmit Power Control (When DIS_STXP = 1)
    |31 30 29 28 27 26 25 24 | 23 22 21 20 19 18 17 16 | 15 14 13 12 11 10 9 8 | 7 6 5 4 3 2 1 0
    |       Not applicable   |       TXPOWSD           |        TXPOWPHR       |     Not applicable
    |       0x0E             |       0x08              |        0x02           |     0x22

    ------------------------------------
    :return: 
        [error_code]
    """
    
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x17', b'\x00', b''
    
    pg_delay_bytes = pg_delay_encode(pg_delay)
    tx_power_bytes = tx_power_encode(tx_power)
    VALUE = VALUE + pg_delay_bytes + tx_power_bytes
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    #do nothing
    return [err_code]

def dwm_uwb_cfg_get(t, verbose=False):
    """ API Section 5.3.19. Modified by Zezhou Wang
    API Sample TLV Request:
    Type    |Length 
    0x18    |0x00   
                    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-pg_delay (1B); tx_power(4B); pg_delay_comp (1B); tx_power_comp (4B)
    0x4F    |0x0A   |0xC3 0x85 0x65 0x45 0x25 0xC4 0x85 0x65 0x45 0x25
                    |1st byte: pg_delay
                    |2nd-5th byte: tx_power
                    |6th byte: pg_delay_comp
                    |7th-10th byte: tx_power_comp

    ------------------------------------
    Gets UWB configuration parameters. Refer to 5.3.18 (dwm_uwb_cfg_set) for details. 
    ------------------------------------
    :return:
        [pg_delay, tx_power, pg_delay_comp, tx_power_comp, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x18', b'\x00', b''
    
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)

    pg_delay, pg_delay_comp = pg_delay_encode(TLV_response)
    tx_power, tx_power_comp = tx_power_encode(TLV_response)
    return [pg_delay, tx_power, pg_delay_comp, tx_power_comp, err_code]

def dwm_usr_data_read(t, verbose=False):
    """ API Section 5.3.20 
    API Sample TLV Request:
    Type    |Length 
    0x19    |0x00   
                    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-label (max 34 Bytes); tx_power(4B); pg_delay_comp (1B); tx_power_comp (4B)
    0x4B    |0x22   |0x01 0x02 0x03 … 0x21 0x22

    ------------------------------------
    Reads downlink user data from the node. The new data cause setting of dedicated flag in the status
    and also cause generation of an event in user application (see dwm_evt_listener_register).
    ------------------------------------
    :return:
        [length, data, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x19', b'\x00', b''
    
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    length = TLV_frames[1][1]
    data = TLV_frames[1][-length:]
    return [data, err_code]

def dwm_usr_data_write(t, data, overwrite=False, verbose=False):
    """ API Section 5.3.21 
    API Sample TLV Request:
    Type    |Length |Value-overwrite (1B) and user_data (max 34B)
    0x1A    |0x23   |0x01 (overwrite) 0x01 0x02 0x03 … 0x21 0x22 (user_data)
                    |overwrite: Forced write. Will overwrite data that is not yet
                    |sent through uplink
    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    Writes user data to be sent through uplink to the network.
    ------------------------------------
    :return:
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x1A', bytes([len(data) + 1]), b''

    VALUE += b'\x00' if not overwrite else b'\x01'
    VALUE += data

    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]


def dwm_label_read(t, verbose=False):
    """ API Section 5.3.22 
    API Sample TLV Request:
    Type    |Length 
    0x1C    |0x00   
                    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-label (6B)
    0x4C    |0x06   |0x01 0x23 0x45 0x67 0x89 0xab

    ------------------------------------
    Reads the node label.
    ------------------------------------
    :return:
        [label, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x1C', b'\x00', b''
    
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    label = TLV_frames[1][-6:]
    #TODO: determine if the label needs to be string or raw bytes
    return [label, err_code]

def dwm_label_write(t, label, verbose=False):
    """ API Section 5.3.23 
    API Sample TLV Request:
    Type    |Length |Value-label (max 16B)
    0x1D    |length |0x01 0x23 0x45 0x67 0x89 0xab
                    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    Writes the node label.
    ------------------------------------
    :return:
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x1D', b'', b''
    #TODO: determine if the label needs to be string or raw bytes
    VALUE, LENGTH = label, len(label)
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]


def dwm_gpio_cfg_output(t, gpio_idx, gpio_value, verbose=False):
    """ API Section 5.3.24
    API Sample TLV Request:
    Type    |Length |Value-gpio_idx (1B) gpio_value (1B)
    0x28    |0x02   |0x0d 0x01
                    |gpio_idx: 8-bit integer, valid values: 2, 8, 9, 10, 12, 13, 14, 15, 22, 23, 27, 30, 31
                    |gpio_value = 8-bit integer, valid values:
                    |0 : set the I/O port pin to a LOW voltage, logic 0 value
                    |1 : set the I/O port pin to a HIGH voltage, logic 1 value
                    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    This API function configures a specified GPIO pin as an output and also sets its value to 1 or 0, giving
    a high or low digital logic output value.
    Note: During the module reboot, the bootloader (as part of the firmware image) blinks twice the
    LEDs on GPIOs 22, 30 and 31 to indicate the module has restarted. Thus these GPIOs should be used
    with care during the first 1s of a reboot operation.
    ------------------------------------
    :return:
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x28', b'\x02', b''

    VALUE = gpio_idx.to_bytes(1, byteorder='little', signed=False) \
            + gpio_value.to_bytes(1, byteorder='little', signed=False)
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]

def dwm_gpio_cfg_input(t, gpio_idx, gpio_pull, verbose=False):
    """ API Section 5.3.25
    API Sample TLV Request:
    Type    |Length |Value-gpio_idx (1B) gpio_pull (1B)
    0x29    |0x02   |0x0d 0x01
                    |gpio_idx: 8-bit integer, valid values: 2, 8, 9, 10, 12, 13, 14, 15, 22, 23, 27, 30, 31
                    |gpio_pull:GPIO pull status = 8-bit integer, valid values:
                    |0 : DWM_GPIO_PIN_NOPULL
                    |1 : DWM_GPIO_PIN_PULLDOWN
                    |3 : DWM_GPIO_PIN_PULLUP

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    This API function configure GPIO pin as input.
    Note: During the module reboot, the bootloader (as part of the firmware image) blinks twice the
    LEDs on GPIOs 22, 30 and 31 to indicate the module has restarted. Thus these GPIOs should be used
    with care during the first 1s of a reboot operation.
    ------------------------------------
    :return:
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x29', b'\x02', b''

    VALUE = gpio_idx.to_bytes(1, byteorder='little', signed=False) \
            + gpio_value.to_bytes(1, byteorder='little', signed=False)
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]

def dwm_gpio_value_set(t, gpio_idx, gpio_pvalue, verbose=False):
    """ API Section 5.3.26
    API Sample TLV Request:
    Type    |Length |Value-gpio_idx (1B) gpio_value (1B)
    0x2A    |0x02   |0x0d 0x01
                    |gpio_idx: 8-bit integer, valid values: 2, 8, 9, 10, 12, 13, 14, 15, 22, 23, 27, 30, 31
                    |gpio_value = 8-bit integer, valid values:
                    |0 : set the I/O port pin to a LOW voltage, logic 0 value
                    |1 : set the I/O port pin to a HIGH voltage, logic 1 value

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    This API function sets the value of the GPIO pin to high or low.
    Note: During the module reboot, the bootloader (as part of the firmware image) blinks twice the
    LEDs on GPIOs 22, 30 and 31 to indicate the module has restarted. Thus these GPIOs should be used
    with care during the first 1s of a reboot operation.
    ------------------------------------
    :return:
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x2A', b'\x02', b''

    VALUE = gpio_idx.to_bytes(1, byteorder='little', signed=False) \
            + gpio_value.to_bytes(1, byteorder='little', signed=False)
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]

def dwm_gpio_value_get(t, gpio_idx, verbose=False):
    """ API Section 5.3.27
    API Sample TLV Request:
    Type    |Length |Value-gpio_idx (1B)
    0x2B    |0x01   |0x0d
                    |gpio_idx: 8-bit integer, valid values: 2, 8, 9, 10, 12, 13, 14, 15, 22, 23, 27, 30, 31

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-gpio_value
    0x55    |0x01   |gpio_value = 8-bit integer, valid values:
                    |0 : set the I/O port pin to a LOW voltage, logic 0 value
                    |1 : set the I/O port pin to a HIGH voltage, logic 1 value

    ------------------------------------
    This API function reads the value of the GPIO pin
    ------------------------------------
    :return:
        [gpio_value, error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x2B', b'\x01', b''
    VALUE = gpio_idx.to_bytes(1, byteorder='little', signed=False) 
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    gpio_value = TLV_frames[1][-1]
    return [gpio_value, err_code]

def dwm_gpio_value_toggle(t, gpio_idx, verbose=False):
    """ API Section 5.3.28
    API Sample TLV Request:
    Type    |Length |Value-gpio_idx (1B)
    0x2C    |0x01   |0x0d
                    |gpio_idx: 8-bit integer, valid values: 2, 8, 9, 10, 12, 13, 14, 15, 22, 23, 27, 30, 31

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    This API function toggles the value of the GPIO pin.
    Note: During the module reboot, the bootloader (as part of the firmware image) blinks twice the
    LEDs on GPIOs 22, 30 and 31 to indicate the module has restarted. Thus these GPIOs should be used
    with care during the first 1s of a reboot operation.
    ------------------------------------
    :return:
        [error_code]
    """
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x2C', b'\x01', b''
    VALUE = gpio_idx.to_bytes(1, byteorder='little', signed=False) 
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    return [err_code]

def dwm_panid_set(t, panid, verbose=False):
    """ API Section 5.3.29
    API Sample TLV Request:
    Type    |Length |Value-panid (2B)
    0x2E    |0x02   |panid: 2-byte unsigned integer (UWB panid)

    API Sample TLV Resonse:
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00
    ------------------------------------
    This API function sets UWB network identifier for the node. The ID is stored in nonvolatile memory.
    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x2E', b'\x02', b''
    
    if isinstance(panid, str):
        VALUE = bytes.fromhex(panid)
    elif isinstance(panid, int):
        VALUE = int.to_bytes(2, byteorder='little', signed=False)
    else:
        raise ValueError("[{}]: Input panid invalid. Got {} (type: {}). Expecting hex string or integer."
                            .format(_func_name, panid, type(panid)))
    
    output_bytes = TYPE + LENGTH + VALUE
    
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)   
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # do nothing
    return [err_code]

def dwm_panid_get(t, verbose=False):
    """ API Section 5.3.30
    API Sample TLV Request:
    Type    |Length 
    0x2F    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-panid
    0x4D    |0x02   |panid: 2-byte unsigned integer (UWB panid, little endian)

    ------------------------------------
    This API function gets UWB network identifier from the node.
    ------------------------------------
    :return: 
        [panid, error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x2F', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    panid = int.from_bytes(TLV_frames[1][-2:], byteorder='little', signed=False)
    return [panid, err_code]

def dwm_nodeid_get(t, verbose=False):
    """ API Section 5.3.31
    API Sample TLV Request:
    Type    |Length 
    0x30    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-nodeid (8B, little endian)
    0x4E    |0x08   |0x99 0x0c 0x80 0x8d 0x63 0xef 0xca 0xde

    ------------------------------------
    This API function gets UWB address of the node.
    ------------------------------------
    :return: 
        [nodeid, error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x30', b'\x00', b''
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    nodeid = int.from_bytes(TLV_frames[1][-8:], byteorder='little', signed=False)
    #TODO: determine if the nodeid needs to be represented by string format
    return [nodeid, err_code]

def dwm_status_get(t, verbose=False):
    """ API Section 5.3.32
    API Sample TLV Request:
    Type    |Length 
    0x32    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-status (2B)
    0x5A    |0x02   |0x01 0x00 (loc_ready: yes)
                    |status:
                    |bit 0: loc_ready: new location data are ready
                    |bit 1: uwbmac_joined: node is connected to UWB network
                    |bit 2: bh_data_ready: UWB MAC backhaul data ready
                    |bit 3: bh_status_changed: UWB MAC status has changed, used in
                    |backhaul
                    |bit 4: reserved
                    |bit 5: uwb_scan_ready: UWB scan results are ready
                    |bit 6: usr_data_ready: User data over UWB received
                    |bit 7: usr_data_sent: User data over UWB sent
                    |bit 8: fwup_in_progress: Firmware update is in progress
                    |bits 9-15 : reserved

    ------------------------------------
    This API function reads the system status. Flags including:
    - Location Data ready
    - Node joined the UWB network
    - New backhaul data ready
    - Backhaul status has changed
    - UWB scan result is ready
    - User data over UWB received
    - User data over UWB sent
    - Firmware update in progress
    All flags are cleared after the call.
    ------------------------------------
    :return: 
        [status, error_code] status in hashmap (bool)
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x32', b'\x00', b''

    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    status_bytes = TLV_frames[1][-2:]
    status_int = int.from_bytes(status_bytes, byteorder='little', signed=False)
    status_binary_string = "{0:0{1}b}".format(status_int, 16)[::-1]
    status = {
        "loc_ready":        True if int(status_binary_string[0]) else False,
        "uwbmac_joined":    True if int(status_binary_string[1]) else False,
        "bh_data_ready":    True if int(status_binary_string[2]) else False,
        "bh_status_changed":True if int(status_binary_string[3]) else False,
        "reserved":         True if int(status_binary_string[4]) else False,    
        "uwb_scan_ready":   True if int(status_binary_string[5]) else False,
        "usr_data_ready":   True if int(status_binary_string[6]) else False,
        "usr_data_sent":    True if int(status_binary_string[7]) else False,
        "fwup_in_progress": True if int(status_binary_string[8]) else False,
    }
    return [status, err_code]

def dwm_int_cfg_set(t, 
                    loc_ready, 
                    spi_data_ready,
                    bh_status_changed,
                    bh_data_ready,
                    bh_initialized_changed,
                    uwb_scan_ready,
                    uwb_data_ready,
                    uwbmac_joined_changed,
                    usr_data_sent,
                    verbose=False):
    """ API Section 5.3.33
    API Sample TLV Request:
    Type    |Length |Value-int_cfg (2B)
    0x34    |0x02   |16 bits (2 bytes), enable and disable configuration of interrupt through dedicated GPIO pin (pin 19:
                    |READY). Each bit represents different thing. For all the flags, 0=disabled, 1=enabled.
                    |int_cfg = spi_data_ready, loc_ready, bh_status_changed, bh_data_ready, bh_initialized_changed,
                    |uwb_scan_ready, usr_data_ready, uwbmac_joined_changed, usr_data_sent
                    |bit 0: loc_ready: interrupt is generated when location data are ready
                    |bit 1: spi_data_ready: new SPI data generates interrupt on dedicated GPIO pin
                    |bit 2: bh_status_changed: UWBMAC status changed
                    |bit 3: bh_data_ready: UWBMAC backhaul data ready
                    |bit 4: bh_initialized_changed: UWBMAC route configured
                    |bit 5: uwb_scan_ready: UWB scan result is available
                    |bit 6: usr_data_ready: user data received over UWBMAC
                    |bit 7: uwbmac_joined_changed: UWBMAC joined
                    |bit 8: usr_data_sent: user data TX completed over UWBMAC
                    |bit 9-15: reserved

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    Enables/disables setting of the dedicated GPIO pin in case of an event. Interrupts/events are
    communicated to the user by setting of GPIO pin CORE_INT1. User can use the pin as source of an
    external interrupt. The interrupt can be processed by reading the status (dwm_status_get) and react
    according to the new status. The status is cleared when read. This call is available only on UART/SPI
    interfaces. This call do a write to internal flash in case of new value being set, hence should not be
    used frequently and can take in worst case hundreds of milliseconds.
    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x34', b'\x02', b''
           
    int_cfg_1 = 0b00000000
    int_cfg_0 = 0b00000000

    int_cfg_0 = int_cfg_0 | (loc_ready << 0)
    int_cfg_0 = int_cfg_0 | (spi_data_ready << 1)
    int_cfg_0 = int_cfg_0 | (bh_status_changed << 2)
    int_cfg_0 = int_cfg_0 | (bh_data_ready << 3)
    int_cfg_0 = int_cfg_0 | (bh_initialized_changed << 4)
    int_cfg_0 = int_cfg_0 | (uwb_scan_ready << 5)
    int_cfg_0 = int_cfg_0 | (uwb_mode << 6)
    int_cfg_0 = int_cfg_0 | (uwbmac_joined_changed << 7)
    int_cfg_1 = int_cfg_1 | (usr_data_sent << 0)
    
    VALUE = int_cfg_0.to_bytes(1, byteorder='little', signed=False) + \
            int_cfg_1.to_bytes(1, byteorder='little', signed=False)

    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]

def dwm_int_cfg_get(t, verbose=False):
    """ API Section 5.3.34
    API Sample TLV Request:
    Type    |Length 
    0x35    |0x00   
                    
    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-int_cfg
    0x47    |0x02   |0x03 0x00 (2B)
                    |int_cfg: 16 bits (2 bytes), enable and disable configuration of interrupt through dedicated GPIO pin (pin 19:
                    |READY). Each bit represents different thing. For all the flags, 0=disabled, 1=enabled.
                    |int_cfg = spi_data_ready, loc_ready, bh_status_changed, bh_data_ready, bh_initialized_changed,
                    |uwb_scan_ready, usr_data_ready, uwbmac_joined_changed, usr_data_sent
                    |bit 0: loc_ready: interrupt is generated when location data are ready
                    |bit 1: spi_data_ready: new SPI data generates interrupt on dedicated GPIO pin
                    |bit 2: bh_status_changed: UWBMAC status changed
                    |bit 3: bh_data_ready: UWBMAC backhaul data ready
                    |bit 4: bh_initialized_changed: UWBMAC route configured
                    |bit 5: uwb_scan_ready: UWB scan result is available
                    |bit 6: usr_data_ready: user data received over UWBMAC
                    |bit 7: uwbmac_joined_changed: UWBMAC joined
                    |bit 8: usr_data_sent: user data TX completed over UWBMAC
                    |bit 9-15: reserved

    ------------------------------------
    This API function reads the configuration flags that, if set, enables the setting of dedicated GPIO pin
    (CORE_INT) in case of an event internal to DWM module. This call is available only on UART/SPI
    interfaces.
    ------------------------------------
    :return: 
        [int_cfg, error_code] hashmap for interrupt configuration flags
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x35', b'\x00', b''
    
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=2)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    # parse TLV frames into anchor hashmaps
    int_cfg_bytes = TLV_frames[1][-2:]
    int_cfg_int = int.from_bytes(int_cfg_bytes, byteorder='little', signed=False)
    int_cfg_binary_string = "{0:0{1}b}".format(int_cfg_int, 16)[::-1]
    int_cfg = {
            'loc_ready'             : True if int(int_cfg_binary_string[0]) else False,
            'spi_data_ready'        : True if int(int_cfg_binary_string[1]) else False,
            'bh_status_changed'     : True if int(int_cfg_binary_string[2]) else False,
            'bh_data_ready'         : True if int(int_cfg_binary_string[3]) else False,
            'bh_initialized_changed': True if int(int_cfg_binary_string[4]) else False,
            'uwb_scan_ready'        : True if int(int_cfg_binary_string[5]) else False,
            'usr_data_ready'        : True if int(int_cfg_binary_string[6]) else False,
            'uwbmac_joined_changed' : True if int(int_cfg_binary_string[7]) else False,
            'usr_data_sent'         : True if int(int_cfg_binary_string[8]) else False,
    }

    return [int_cfg, err_code]

def dwm_enc_key_set(t, enc_key, verbose=False):
    """ API Section 5.3.35
    API Sample TLV Request:
    Type    |Length |Value-enc_key (16B)
    0x3C    |0x10   |16-byte array: 128 bit encryption key

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    This API function Sets encryption key. The key is stored in non-volatile memory. The key that consists
    of just zeros is considered as invalid. If key is set, the node can enable encryption automatically.
    Automatic enabling of the encryption is triggered via UWB network when the node detects
    encrypted message and is capable of decrypting the messages with the key. BLE option is disabled
    when encryption is enabled automatically. The encryption can be disabled by clearing the key
    (dwm_enc_key_clear).
    This call writes to internal flash in case of new value being set, hence should not be used frequently
    and can take in worst case hundreds of milliseconds! Requires reset for new configuration to take
    effect.
    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x3C', b'\x10', b''
           
    if isinstance(enc_key, str):
        VALUE = bytes.fromhex(panid)
    elif isinstance(enc_key, int):
        VALUE = int.to_bytes(16, byteorder='little', signed=False)
    else:
        raise ValueError("[{}]: invalid encryption key. Got {} (type: {}). Expecting hex string or integer."
                            .format(_func_name, enc_key, type(enc_key)))
    
    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]

def dwm_enc_key_clear(t, verbose=False):
    """ API Section 5.3.36
    API Sample TLV Request:
    Type    |Length 
    0x3D    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code 
    0x40    |0x01   |0x00           

    ------------------------------------
    This API function clears the encryption key and disables encryption option if enabled. Does nothing if
    the key is not set.
    This call writes to internal flash in case of new value being set, hence should not be used frequently
    and can take in worst case hundreds of milliseconds! Requires reset for new configuration to take
    effect.

    ------------------------------------
    :return: 
        [error_code]
    """ 
    _func_name = inspect.stack()[0][3]
    TYPE, LENGTH, VALUE = b'\x3D', b'\x10', b''

    output_bytes = TYPE + LENGTH + VALUE
    t.reset_output_buffer()
    t.reset_input_buffer()
    t.write(output_bytes)
    if verbose:
        verbose_request(output_bytes)
    TLV_frames = read_all_TLV(t, expecting=1)
    TLV_response = b''.join(TLV_frames)
    err_code = TLV_response[2] if TLV_response[0:2] == b'\x40\x01' else 6
    if verbose:
        verbose_response(TLV_response, err_code, _func_name)
    error_handler(TLV_response, err_code, _func_name)
    
    return [err_code]

def dwm_nvm_usr_data_set():
    """ API Section 5.3.37
    ------------------------------------
    Stores user data to non-volatile memory. Writes internal non-volatile memory so should be used
    carefully. Old data are overwritten.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1 

def dwm_nvm_usr_data_get():
    """ API Section 5.3.38
    ------------------------------------
    Reads user data from non-volatile memory. Reads from internal flash.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1  

def dwm_gpio_irq_cfg():
    """ API Section 5.3.39
    ------------------------------------
    This API function registers GPIO pin interrupt call back functions.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1  

def dwm_gpio_irq_dis():
    """ API Section 5.3.40
    ------------------------------------
    This API function disables GPIO pin interrupt on the selected pin.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1 

def dwm_i2c_read():
    """ API Section 5.3.41
    ------------------------------------
    This API function read data from I2C slave. 
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1 

def dwm_i2c_write():
    """ API Section 5.3.42
    ------------------------------------
    This API function writes data to I2C slave.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1 

def dwm_evt_listener_register():
    """ API Section 5.3.43
    ------------------------------------
    Registers events listener. User application can wait for the events that are registered to listen to by
    dwm_evt_wait. The event can be triggered for example when LE finishes position calculation and
    when distances are calculated. This call applies only for end user application. Can not be used with
    SPI or UART. In low power mode in order to wake up from the sleep, the event listener has to be
    registered, otherwise the user application will remain sleeping.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1 

def dwm_evt_wait():
    """ API Section 5.3.44
    ------------------------------------
    Used to wait for an event from DWM module. The event listener must be first registered by
    dwm_evt_listener_register. If event listener is registered and dwm_evt_wait is not used to consume
    events the event buffer will overflow. When there are no events in the buffer, the dwm_evt_wait
    will block and sleep until next event.
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1 

def dwm_wake_up():
    """ API Section 5.3.45
    ------------------------------------
    Prevents entering of the sleep state (if in low power mode). Should be called only from the thread
    context. Wakes up dwm_sleep().
    ------------------------------------
    :return:
        -1 This command is not available on external interfaces (UART/SPI).
    """
    return -1   

def dwm_bh_status_get():
    """ API Section 5.4.1
    API Sample TLV Request:
    Type    |Length 
    0x3A    |0x00   

    API Sample TLV Resonse:
    Type    |Length |Value-err_code |...
    0x40    |0x01   |0x00           |...
    Type    |Length |Value-sf_number, bh_seat_map and node_id are in little endian
    0x5D    |0x13   |0x6c 0x00 0x07 0x00 0x00 0x00 0x03 0xf3 0x11 0x00 0x01 0xc3 0x11 0x01 0x01 0x66 0x11 0x02 0x01
                    |sf_number 16-bit integer current superframe number
                    |bh_seat_map 32-bit integer seat map in the current superframe
                    |origin_cnt 8-bit integer range is from 0 to 8 
                    |origin_info
                        node_id 16-bit integer origin address
                        bh_seat 8-bit integer seat that the origin occupies, range from 0 to 8
                        hop_lvl 8-bit integer hop level

    ------------------------------------
    This section describes API commands that are used to periodically transfer data over SPI interface
    when the DWM module is configured as “bridge” (see API call dwm_cfg_anchor_set). 
    ------------------------------------
    :return:
        Not Yet Implemented.
    """
    return -1 

def dwm_backhaul_xfer():
    """ API Section 5.4.2
    
    API Sample TLV Request Example 1:
    communication from SPI master (normally the RPi) to node other than Bridge (as SPI slave):
    Type    |Length |Value-downlink_byte_cnt = size of downlink data (2B)
    0x37    |0x02   |0xf4 0x00
    TLV Response:
    Type    |Length |Value-err_code
    0x40    |0x01   |0x00

    API Sample TLV Request Example 2:
    communication from SPI master (normally the RPi) with Bridge (as SPI slave)
    Downlink bytes count: 244
    Uplink bytes count: 980: SIZE = 255, NUM = 4
    Type    |Length |Value-downlink_byte_cnt = size of downlink data (2B)
    0x37    |0x02   |0xf4 0x00
    Response:
    SIZE    |NUM
    0xFF    |0x04
    
    On receiving SIZE = 255 and NUM= 4, the SPI Master initiates 4 transfers, each of 255 bytes
    Master Out data: TLV downlink number 1, 2, 3, 4
    Type    |Length |Value                          |Dummy bytes
    0x64    |0xF4   |0x01 0x02 … 0xf4 (244 in total)|0xff 0xff … 0xff (9 in total)
    0xff 0xff…0xff (255 in total)
    0xff 0xff…0xff (255 in total)
    0xff 0xff…0xff (255 in total)
    
    Slave Out data: TLV uplink number 1, 2, 3, 4
    Type    |Length |Value
    0x6E    |0xFD   |0x01 0x02 … 0xf4 (253 in total)
    0x6F    |0xFD   |0x01 0x02 … 0xf4 (253 in total)
    0x70    |0xFD   |0x01 0x02 … 0xf4 (253 in total)
    0x71    |0xDD   |0x01 0x02 … 0xf4 (221 in total) |0xff 0xff … 0xff (dummy bytes: 32 in total)
    ------------------------------------
    Writes downlink data and reads uplink data chunks. The DWM module must be configured as bridge.
    This API must be used with SPI Scheme: TLV communication using data ready pin.
    Both the uplink and the downlink data are encoded into TLV frames when transferred by SPI
    interface as described in SPI Scheme: TLV communication using data ready pin.
    SPI master tells slave how many downlink bytes it wants to transfer by downlink_byte_cnt. The
    downlink_byte_cnt is read by slave in first SPI transfer. Slave has some uplink data ready that it
    wants to transfer to the master as it is reading the downlink. In order to transfer both the downlink
    from the master to the slave and the uplink from the slave to the master, the slave has to calculate
    how many bytes and how many SPI transfers are needed. The master reads SIZE (the number of the
    bytes) and NUM (the number of the transfers) in the second SPI transfer as explained in SPI Scheme:
    TLV communication using data ready pin. Finally, the transfers are executed and both uplink and
    downlink are transferred. Maximum number of transfers currently supported is 5 with maximum
    payload 253 bytes, which is 255 - sizeof(TLV header). At most 5 uplink frames and at most 2
    downlink frames are supported in one call to dwm_backhaul_xfer.
    TLV types 100-104 (0x64-0x68) are reserved for uplink data chunks. TLV types 110-114
    (0x6E-0x72) are reserved for downlink data chunks.
    ------------------------------------
    :return:
        Not Yet Implemented.
    """
    return -1 