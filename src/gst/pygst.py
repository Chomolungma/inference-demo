import logging
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

class MediaEngine(object):
    """
    Class used to Manage Gstreamer Pipelines
    Media Engine abstracts the Gstreamer control
    """
    def __init__(self, session_name, loop):
        self._session_name = session_name
        self._pipes = {}
        self._loop = loop

    def create_pipe(self, pipe_name, pipe_desc):
        """
        Creates Gstreamer Pipeline from a description
        Parameters
        ----------
        pipe_name : Pipeline Name
            Name of the pipeline to create
        pipe_desc : Pipeline Description
            Pipeline Description to create
        Raises
        ------
        RuntimeError:
            In case the pipeline hasn't been created yet
            In case the pipelines fails stopping

        """
        if not pipe_desc:
            raise RuntimeError("Invalid Pipeline Description")

        logging.info("Creating pipeline {} with description: {}".format(pipe_name, pipe_desc))
        pipeline = Pipeline(pipe_name, pipe_desc)

        try:
            gst_pipe = Gst.parse_launch(pipe_desc)
        except GLib.Error as e:
            raise RuntimeError("Gstreamer Failed Parsing pipeline", str(e))

        bus = gst_pipe.get_bus()

        pipeline.gst_pipe = gst_pipe
        pipeline.bus = bus
        self._pipes[pipe_name] = pipeline

        try:
            bus.add_signal_watch()
            bus.connect("message", self._bus_call, self._loop)
        except GLib.Error as e:
            raise RuntimeError("Gstreamer Failed Connecting Bus: ", str(e))

    def play_pipe(self, pipe_name):
        """
        Plays the Gstreamer Pipeline initially created
        Parameters
        ----------
        pipe_name : Pipeline Name
            Name of the pipeline to play
        Raises
        ------
        RuntimeError:
            In case the pipeline hasn't been created yet
            In case the pipelines fails stopping
        """
        try:
            pipeline = self._pipes[pipe_name]
        except KeyError:
            logging.error("Pipeline {} has not been created".format(pipe_name))
            return

        logging.info("Playing pipeline {}".format(pipe_name))

        try:
            pipeline.gst_pipe.set_state(Gst.State.PLAYING)
        except GLib.Error as e:
            raise RuntimeError("Gstreamer Failed Playing Pipeline: ", str(e))

    def stop_pipe(self, pipe_name):
        """
        Stops the Gstreamer Pipeline initially played
        Parameters
        ----------
        pipe_name : Pipeline Name
            Name of the pipeline to stop
        Raises
        ------
        RuntimeError:
            In case the pipeline hasn't been created yet
            In case the pipelines fails stopping
        """
        try:
            pipeline = self._pipes[pipe_name]
        except KeyError:
            logging.error("Pipeline {} has not been created".format(pipe_name))
            return

        logging.info("Stopping pipeline {}".format(pipe_name))

        try:
            if(pipeline.gst_pipe.get_state(1 * Gst.SECOND)[1] == Gst.State.NULL):
                logging.debug("Pipeline has already been stopped")
            pipeline.gst_pipe.set_state(Gst.State.NULL)
        except GLib.Error as e:
            raise RuntimeError("Gstreamer Failed Stopping Pipeline: ", str(e))

    def _bus_call(self, bus, message, loop):
        """
        Gstreamer Bus Callback to handle Gstreamer Messages
        Parameters
        ----------
        bus : GstBus
            Gstreamer Bus owner of the callback
        message : GstMessage
            Gstreamer Message arriving to the bus
        loop : GObject MainLoop
            GObject Mainloop
        Returns
        -------
        bool
            Callback result
        """
        mtype = message.type
        if mtype == Gst.MessageType.EOS or mtype == Gst.MessageType.ERROR:
            if mtype == Gst.MessageType.EOS:
                logging.warn('Detected EOS from session {}'.format(self._session_name))
            else:
                logging.warn('Detected ERROR from session {}'.format(self._session_name))
            for pipe in self._pipes:
                self.stop_pipe(pipe)
            loop.quit()
        return True


class Pipeline(object):
    """
    Class used to store the Pipeline parameters
    """
    def __init__(self, name, pipe_desc):
        self.name = name
        self.pipe_desc = pipe_desc
