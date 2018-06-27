import logging
import os
import sys

def init_logger(ch, logger_name="pfp_log", file_handler="pfp.log"):
    """
    Purpose:
     Returns a logger object.
    Usage:
     logger = pfp_log.init_logger(ch)
     where ch is a window where text can be displayed
    Author: PRI with acknowledgement to James Cleverly
    Date: September 2016
    """
    logger = logging.getLogger(name=logger_name)
    logger.setLevel(logging.DEBUG)
    # check the log file directory exists, create if it doesn't
    if not os.path.exists("logfiles"):
        os.makedirs("logfiles")
    log_file_path = os.path.join("logfiles", file_handler)
    # create file handler
    fh = logging.FileHandler(log_file_path)
    fh.setLevel(logging.DEBUG)
    # create formatter and add to handlers
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s','%H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

