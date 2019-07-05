#!/usr/bin/env python3

import logging
import gi
import sys
import time
gi.require_version('Gst', '1.0')
gi.require_version('GObject', '2.0')
from gi.repository import GObject, Gst, GLib
from gst import pygst

def logger_setup():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    
def main (args=None):
    # Gstreamer Init
    GObject.threads_init()
    Gst.init(args)

    # Logger Setup
    logger_setup()

    logging.info("This is a demo application...")
    loop = GObject.MainLoop()
    mengine = pygst.MediaEngine("mediaengine0", loop)

    mengine.create_pipe("vtest0", "videotestsrc pattern=ball is-live=true ! capsfilter caps=video/x-raw,width=640,height=480 ! xvimagesink")
    mengine.play_pipe("vtest0")
    mengine.create_pipe("vtest1", "videotestsrc is-live=true ! xvimagesink")
    mengine.play_pipe("vtest1")

    try:
        loop.run()
    except GLib.Error:
        pass

if __name__ == "__main__":
    main(None)
