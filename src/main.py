#!/usr/bin/env python3

from gst import gstc
import logging
import gi
import sys
import time
import json
import subprocess
import threading

# Setup
GSTD_PROCNAME = 'gstd'
logfile_name =  "gst-inference-demo.log"

# Read Tinyyolo Labels
tinyyolo_labels_file = open("tinyyolov2_labels.txt", "r")
tinyyolo_labels = tinyyolo_labels_file.read()
tinyyolo_labels_file.close()

# Absolute Path where models are found
models_path = "/home/nvidia/gst-inference-demo/src/"

# Pipelines definitions

webrtc_base_pipeline = " rrwebrtcbin start-call=true signaler=GstOwrSignaler signaler::server_url=https://webrtc.ridgerun.com:8443 "
rstp_source_pipeline = " rtspsrc debug=true async-handling=true location=rtsp://"
camera_source_pipeline = " nvarguscamerasrc sensor-id=0 ! nvvidconv ! capsfilter caps=video/x-raw,width=752,height=480 "
video_decode_pipeline = " rtpvp8depay ! omxvp8dec ! nvvidconv ! capsfilter caps=video/x-raw(memory:NVMM) ! nvvidconv "
interpipesink_pipeline = " interpipesink enable-last-sample=false forward-eos=true forward-events=true async=false name="
interpipesrc_pipeline = " interpipesrc format=3 enable-sync=false name="
video_encode_pipeline = " queue max-size-buffers=1 leaky=downstream ! omxvp8enc ! rtpvp8pay"
tee_pipeline = " tee name="
jpeg_base_pipeline = " nvjpegenc name="
multifilesink_pipeline = " multifilesink location=/tmp/output%d.jpeg sync=false"

# Inference (Tinyyolov2)
tinyyolov2_format_pipeline = " capsfilter caps=video/x-raw,width=752,height=480 "
tinyyolov2_base_pipeline = """ tinyyolov2 model-location=""" + models_path + \
    """graph_tinyyolov2_tensorflow.pb backend=tensorflow backend::input-layer=input/Placeholder backend::output-layer=add_8 name=net """
tinyyolov2_net_pipeline = " queue max-size-buffers=1 leaky=downstream ! nvvidconv ! capsfilter caps=video/x-raw(memory:NVMM) ! nvvidconv ! net.sink_model "
tinyyolov2_bypass_pipeline = " queue max-size-buffers=1 leaky=downstream ! net.sink_bypass "
tinyyolov2_overlay_pipeline = """ net.src_bypass ! nvvidconv ! capsfilter caps=video/x-raw(memory:NVMM) ! nvvidconv ! detectionoverlay labels=\"""" + tinyyolo_labels + \
    """\" ! inferencealert name=person-alert label-index=14 ! queue max-size-buffers=1 leaky=downstream ! nvvidconv ! capsfilter caps=video/x-raw(memory:NVMM)  ! nvvidconv ! capsfilter caps=video/x-raw """

def start_gstd(arg1="", arg2=""):
    try:
        gstd_bin = subprocess.check_output(['which',GSTD_PROCNAME])
        gstd_bin = gstd_bin.rstrip()
        logging.info('Startting GStreamer Daemon...')
        subprocess.Popen([gstd_bin, arg1, arg2])
        time.sleep(3)
    except subprocess.CalledProcessError:
        # Did not find gstd
        logging.error("GStreamer Daemon is not running and it is not installed.")
        logging.error("To get GStreamer Daemon, visit https://www.ridgerun.com/gstd.")
        return False


def logger_setup():
    gstd_log = logging.getLogger('GSTD')
    gstd_log.setLevel(logging.ERROR)
    handler = logging.StreamHandler(logfile_name)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    gstd_log.addHandler(handler)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.FileHandler(logfile_name)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def take_snapshot (gstd_client):
    gstd_client.pipeline_play("p1")
    gstd_client.bus_read ("p1")
    gstd_client.pipeline_stop("p1")

def person_alert_handler (name, gstd_client):
    while 1:
        ret = gstd_client.signal_connect("p0", "person-alert", "alert")
        if (ret["code"] == 0):
            logging.info ("Person Detected")
            take_snapshot (gstd_client)
        else:
            break


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
    interpipesink2_name = test_name + "_inferencesink"

    video_receive0 = interpipesink_pipeline + interpipesink0_name

    video_receive1 = video_decode_pipeline + \
        " ! " + tinyyolov2_format_pipeline + " ! "
    video_receive1 += interpipesink_pipeline + interpipesink1_name

    inference = tinyyolov2_base_pipeline
    inference += interpipesrc_pipeline + "src0" + " listen-to=" + interpipesink1_name
    inference += " ! " + tee_pipeline + "t0"
    inference += " t0. ! " + tinyyolov2_net_pipeline
    inference += " t0. ! " + tinyyolov2_bypass_pipeline
    inference += tinyyolov2_overlay_pipeline

    video_send = inference + " ! " + interpipesink_pipeline + interpipesink2_name
    video_send += interpipesrc_pipeline + "src1" + " listen-to=" + interpipesink2_name
    video_send += " ! " + video_encode_pipeline
    
    full_pipe = webrtc + "  " + camera_source_pipeline + " ! " + video_receive0 + \
        rtsp + " ! " + video_receive1 + video_send + " ! " + webrtc_name

    logging.info(" Test name: " + test_name)
    logging.info(
        " Description: RTSP + GstInterpipe + GstInference Detection + GstWebRTC on GStreamer Daemon")
    logging.debug(" Pipeline: " + full_pipe)
    gstd_client.pipeline_create("p0", full_pipe)
    gstd_client.pipeline_play("p0")

    jpeg_pipe = interpipesrc_pipeline + "src2" + " listen-to=" + interpipesink2_name \
        + " num-buffers=1"
    jpeg_pipe += " ! " + jpeg_base_pipeline + test_name + "_jpeg_sink"
    jpeg_pipe += " ! " + multifilesink_pipeline

    gstd_client.pipeline_create("p1", jpeg_pipe)


def main(args=None):
    start_gstd("-n", "2")

    gstd_client = gstc.client(loglevel='ERROR')
    gstd_client2 = gstc.client(port=5001,loglevel='ERROR')

    # Load the JSON default parameters as a dictionary
    with open('./pipe_config.json') as json_file:
        default_params = json.load(json_file)

    # Logger Setup
    logger_setup()

    logging.info("This is a demo application...")
    build_test_0(gstd_client, "Test0", default_params)

    time.sleep(10)

    # Person Alert Thread
    x = threading.Thread(target=person_alert_handler, args=(1,gstd_client2))
    x.daemon = True
    x.start()

    # Bus Filter definition
    gstd_client.bus_filter ("p1", "eos")

    while True:
        choice = input(
            "    ** Menu **\n 1) Camera source\n 2) RTSP source\n 3) Take snapshot\n 4) Exit\n > ")
        choice = choice.lower()  # Convert input to "lowercase"

        if choice == '1':
            gstd_client.element_set(
                "p0",
                "src0",
                "listen-to",
                "Test0_camera")
            print("--> Camera source selected\n")
        if choice == '2':
            gstd_client.element_set(
                "p0",
                "src0",
                "listen-to",
                "Test0_decodesink")
            print("--> RTSP source selected\n")
        if choice == '3':
            take_snapshot (gstd_client)
            print("--> Snapshot has been taken\n")
        if choice == '4':
            print("--> Exit\n")
            break
    gstd_client.pipeline_stop("p0")


if __name__ == "__main__":
    main(None)
