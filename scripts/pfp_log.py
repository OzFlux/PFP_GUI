# standard modules
import datetime
import logging
import os
# 3rd party modules
from PyQt4 import QtCore, QtGui

class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super(QPlainTextEditLogger, self).__init__()
        self.textBox = QtGui.QPlainTextEdit(parent)
        self.textBox.setReadOnly(True)
        logfmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
        self.setFormatter(logfmt)

    def emit(self, record):
        msg = self.format(record)
        self.textBox.appendPlainText(msg)
        QtGui.QApplication.processEvents()

def init_logger():
    """
    Purpose:
     Returns a logger object.
    Usage:
     logger = pfp_log.init_logger()
    Author: PRI with acknowledgement to James Cleverly
    Date: September 2016
    """
    # get the logger
    logger = logging.getLogger(name="pfp_log")
    # set the level
    logger.setLevel(logging.DEBUG)
    # create file handler
    now = datetime.datetime.now()
    file_name = "pfp_" + now.strftime("%Y%m%d%H%M") + ".log"
    log_file_path = os.path.join("logfiles", file_name)
    fh = logging.FileHandler(log_file_path)
    fh.setLevel(logging.DEBUG)
    # create formatter and add to handlers
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
    fh.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)

    return logger
