#!/usr/bin/env python3

import logging
import gi
import sys
import time
import json
gi.require_version('Gst', '1.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib
from gst import pygstd

webrtc_base_pipeline = " rrwebrtcbin start-call=true signaler=GstOwrSignaler signaler::server_url=https://webrtc.ridgerun.com:8443 "
rstp_source_pipeline = " rtspsrc debug=true async-handling=true location=rtsp://"
video_decode_pipeline = " rtpvp8depay ! omxvp8dec ! nvvidconv ! capsfilter caps=video/x-raw(memory:NVMM) ! nvvidconv "
interpipesink_pipeline = " interpipesink enable-last-sample=false forward-eos=true forward-events=true async=false name="
interpipesrc_pipeline = " interpipesrc format=3 listen-to="
video_encode_pipeline = " queue max-size-buffers=1 leaky=downstream ! omxvp8enc ! rtpvp8pay"

pipeline_counter = 0

def logger_setup():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

def play_pipeline(gstd_client, pipeline):
    global pipeline_counter
    [ret, description] = gstd_client.pipeline_create ("p" + str(pipeline_counter), pipeline)
    if (ret!=0):
        print ("Error creating the pipeline: "+ str(ret) + " " + description)
        return
    [ret, description] = gstd_client.pipeline_play ("p" +  str(pipeline_counter))
    if (ret!=0):
        print ("Error playing the pipeline: "+ str(ret) + " " + description)
        return

    pipeline_counter = pipeline_counter + 1

def build_test_0(gstd_client, test_name, default_data):
    session_id = default_data[test_name]["session_id"]
    rtsp_ip_address = default_data[test_name]["rtsp_ip_address"]
    rtsp_port = default_data[test_name]["rtsp_port"]

    # Create Pipelines
    webrtc_name = test_name + ".video_sink"
    webrtc = webrtc_base_pipeline + "signaler::session_id=" + session_id
    webrtc += " name=" + test_name

    rtsp = rstp_source_pipeline + rtsp_ip_address + ":" + rtsp_port + "/test"

    interpipesink0_name = test_name + "_decodesink"

    video_receive = video_decode_pipeline + " ! "
    video_receive += interpipesink_pipeline + interpipesink0_name

    video_send = interpipesrc_pipeline + interpipesink0_name
    video_send += " ! " + video_encode_pipeline

    full_pipe = webrtc + "  " + rtsp + " ! " + video_receive + video_send + " ! " + webrtc_name
    logging.info(" Test name: " + test_name)
    logging.info(" Description: RTSP + GstInterpipe + GstWebRTC on GStreamer Daemon")
    logging.info(" Pipeline: " + full_pipe)
    play_pipeline(gstd_client, full_pipe)

def main (args=None):
    gstd_client = pygstd.GSTD()

    # Load the JSON default parameters as a dictionary
    with open('./pipe_config.json') as json_file:
        default_params = json.load(json_file)

    # Logger Setup
    logger_setup()

    logging.info("This is a demo application...")
    loop = GObject.MainLoop()
    build_test_0(gstd_client, "Test0", default_params)

    try:
        loop.run()
    except GLib.Error:
        pass

if __name__ == "__main__":
    main(None)
