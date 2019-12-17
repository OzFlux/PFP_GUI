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

def init_logger(logger_name, log_file_name, to_file=True, to_screen=False):
    """
    Purpose:
     Returns a logger object.
    Usage:
     logger = pfp_log.init_logger()
    Author: PRI with acknowledgement to James Cleverly
    Date: September 2016
    """
    # create formatter
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
    # create the logger and set the level
    logger = logging.getLogger(name=logger_name)
    logger.setLevel(logging.DEBUG)
    if to_file:
        # create file handler for all messages
        fh1 = logging.FileHandler(log_file_name)
        fh1.setLevel(logging.DEBUG)
        fh1.setFormatter(formatter)
        # add the file handler to the logger
        logger.addHandler(fh1)
        # set up a separate file for errors
        ext = os.path.splitext(log_file_name)[1]
        error_file_name = log_file_name.replace(ext, ".errors")
        fh2 = logging.FileHandler(error_file_name)
        fh2.setLevel(logging.ERROR)
        fh2.setFormatter(formatter)
        logger.addHandler(fh2)
    if to_screen:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.DEBUG)
        logger.addHandler(console)
    return logger

def change_logger_filename(logger_name, new_file_name):
    # get the logger
    logger = logging.getLogger(name=logger_name)
    # create formatter
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
    # remove the existing file handlers
    for hdlr in logger.handlers[:]:
        if isinstance(hdlr, logging.FileHandler):
            old_log_path = hdlr.baseFilename
            old_log_level = hdlr.level
            old_log_formatter = hdlr.formatter
            logger.removeHandler(hdlr)
            old_dir_name = os.path.dirname(os.path.abspath(old_log_path))
            old_base_name = os.path.basename(os.path.abspath(old_log_path))
            old_file_name = os.path.splitext(old_base_name)[0]
            new_base_name = old_base_name.replace(old_file_name, new_file_name)
            new_log_path = os.path.join(old_dir_name, new_base_name)
            fh = logging.FileHandler(new_log_path)
            fh.setLevel(old_log_level)
            fh.setFormatter(old_log_formatter)
            logger.addHandler(fh)
    return logger

def get_batch_log_path(log_path):
    if not os.path.isdir(log_path):
        os.mkdir(log_path)
    batch_log_path = os.path.join(log_path, "batch")
    if not os.path.isdir(batch_log_path):
        os.mkdir(batch_log_path)
    now = datetime.datetime.now()
    batch_log_now_path = os.path.join(batch_log_path, now.strftime("%Y%m%d%H%M"))
    if not os.path.isdir(batch_log_now_path):
        os.mkdir(batch_log_now_path)
    return batch_log_now_path
