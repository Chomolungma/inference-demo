#!/usr/bin/env python3

import logging
import gi
import sys
import time
import json
gi.require_version('Gst', '1.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib
from gst import gstc

webrtc_base_pipeline = " rrwebrtcbin start-call=true signaler=GstOwrSignaler signaler::server_url=https://webrtc.ridgerun.com:8443 "
rstp_source_pipeline = " rtspsrc debug=true async-handling=true location=rtsp://"
camera_source_pipeline = " nvarguscamerasrc sensor-id=0 "
video_decode_pipeline = " rtpvp8depay ! omxvp8dec ! nvvidconv ! capsfilter caps=video/x-raw(memory:NVMM) ! nvvidconv "
interpipesink_pipeline = " interpipesink enable-last-sample=false forward-eos=true forward-events=true async=false name="
interpipesrc_pipeline = " interpipesrc name=src format=3 listen-to="
video_encode_pipeline = " queue max-size-buffers=1 leaky=downstream ! omxvp8enc ! rtpvp8pay"

def logger_setup():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

def create_pipeline(gstd_client, name, pipeline):
    global pipeline_counter
    ret = gstd_client.pipeline_create (name, pipeline)
    if (ret!=0):
        print ("Error creating the pipeline: "+ str(ret))
        return

def play_pipeline(gstd_client, name):
    ret = gstd_client.pipeline_play (name)
    if (ret!=0):
        print ("Error playing the pipeline: "+ str(ret))
        return

def set_element_prop(gstd_client, name, element, prop, value):
    ret = gstd_client.element_set(name, element, prop, value)
    if (ret!=0):
        print ("Error setting element property: "+ str(ret))
        return

def stop_pipeline(gstd_client, name):
    ret = gstd_client.pipeline_stop (name)
    if (ret!=0):
        print ("Error stopping the pipeline: "+ str(ret))
        return

def build_test_0(gstd_client, test_name, default_data):
    session_id = default_data[test_name]["session_id"]
    rtsp_ip_address = default_data[test_name]["rtsp_ip_address"]
    rtsp_port = default_data[test_name]["rtsp_port"]

    # Create Pipelines
    webrtc_name = test_name + ".video_sink"
    webrtc = webrtc_base_pipeline + "signaler::session_id=" + session_id
    webrtc += " name=" + test_name

    rtsp = rstp_source_pipeline + rtsp_ip_address + ":" + rtsp_port + "/test"

    interpipesink0_name = test_name + "_camera"
    interpipesink1_name = test_name + "_decodesink"

    video_receive0 = interpipesink_pipeline + interpipesink0_name

    video_receive1 = video_decode_pipeline + " ! "
    video_receive1 += interpipesink_pipeline + interpipesink1_name

    video_send = interpipesrc_pipeline + interpipesink0_name
    video_send += " ! " + video_encode_pipeline

    full_pipe = webrtc + "  " + camera_source_pipeline + " ! " + video_receive0 +  rtsp + " ! " + video_receive1 + video_send + " ! " + webrtc_name
    logging.info(" Test name: " + test_name)
    logging.info(" Description: RTSP + GstInterpipe + GstWebRTC on GStreamer Daemon")
    logging.info(" Pipeline: " + full_pipe)
    create_pipeline(gstd_client, "p0", full_pipe)
    play_pipeline(gstd_client, "p0")

def main (args=None):
    gstd_client = gstc.client(loglevel='DEBUG')

    # Load the JSON default parameters as a dictionary
    with open('./pipe_config.json') as json_file:
        default_params = json.load(json_file)

    # Logger Setup
    logger_setup()

    logging.info("This is a demo application...")
    build_test_0(gstd_client, "Test0", default_params)

    time.sleep(1)
    while True:
        choice = input("    ** Menu **\n 1) Camera source\n 2) RTSP source\n 3) Exit\n > ")
        choice = choice.lower() #Convert input to "lowercase"

        if choice == '1':
            set_element_prop(gstd_client, "p0", "src", "listen-to", "Test0_camera")
            print("--> Camera source selected\n")
        if choice == '2':
            set_element_prop(gstd_client, "p0", "src", "listen-to", "Test0_decodesink")
            print("--> RTSP source selected\n")
        if choice == '3':
            print("--> Exit\n")
            break

    stop_pipeline(gstd_client, "p0")

if __name__ == "__main__":
    main(None)
