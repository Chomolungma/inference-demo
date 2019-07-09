#!/usr/bin/env python3

import logging
import gi
import sys
import time
gi.require_version('Gst', '1.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib
from gst import pygstd

pipeline1 = "videotestsrc pattern=ball is-live=true ! capsfilter caps=video/x-raw,width=640,height=480 ! xvimagesink"
pipeline2 = "videotestsrc is-live=true ! xvimagesink"

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
    
def main (args=None):
    gstd_client = pygstd.GSTD()

    # Logger Setup
    logger_setup()

    logging.info("This is a demo application...")
    loop = GObject.MainLoop()
    logging.info(" Pipeline: " + pipeline1)
    play_pipeline(gstd_client, pipeline1)
    logging.info(" Pipeline: " + pipeline2)
    play_pipeline(gstd_client, pipeline2)

    try:
        loop.run()
    except GLib.Error:
        pass

if __name__ == "__main__":
    main(None)
