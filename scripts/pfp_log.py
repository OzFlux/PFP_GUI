# standard modules
import datetime
import logging
import os
# 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets

class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super(QPlainTextEditLogger, self).__init__()
        self.textBox = QtWidgets.QPlainTextEdit(parent)
        self.textBox.setReadOnly(True)
        logfmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
        self.setFormatter(logfmt)

    def emit(self, record):
        msg = self.format(record)
        self.textBox.appendPlainText(msg)
        QtWidgets.QApplication.processEvents()

def init_logger(logger_name="pfp_log", to_file=True):
    """
    Purpose:
     Returns a logger object.
    Usage:
     logger = pfp_log.init_logger()
    Author: PRI with acknowledgement to James Cleverly
    Date: September 2016
    """
    # create formatter
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
    # create the logger and set the level
    logger = logging.getLogger(name=logger_name)
    logger.setLevel(logging.DEBUG)
    if to_file:
        # create file handler for all messages
        now = datetime.datetime.now()
        log_file_name = "pfp_" + now.strftime("%Y%m%d%H%M") + ".log"
        log_file_path = os.path.join("logfiles", log_file_name)
        fh1 = logging.FileHandler(log_file_path)
        fh1.setLevel(logging.DEBUG)
        fh1.setFormatter(formatter)
        # add the file handler to the logger
        logger.addHandler(fh1)
        # set up a separate file for errors
        error_file_name = log_file_name.replace(".","_errors.")
        error_file_path = os.path.join("logfiles", error_file_name)
        fh2 = logging.FileHandler(error_file_path)
        fh2.setLevel(logging.ERROR)
        fh2.setFormatter(formatter)
        logger.addHandler(fh2)
    return logger
