# standard modules
import datetime
import os
import sys
# 3rd party modules
from configobj import ConfigObj
# PFP modules
sys.path.append('scripts')
import pfp_batch
#import pfp_io
import pfp_log

# create pfp_log when called from the command line
now = datetime.datetime.now()
log_file_name = "batch_" + now.strftime("%Y%m%d%H%M") + ".log"
logger = pfp_log.init_logger("pfp_log", log_file_name, to_console=True)

# get the control file name
if len(sys.argv) == 1:
    # not on the command line, so ask the user
    cfg_file_path = raw_input("Enter the control file name: ")
    # exit if nothing selected
    if len(cfg_file_path) == 0:
        sys.exit()
else:
    # control file name on the command line
    if not os.path.exists(sys.argv[1]):
        # control file doesn't exist
        logger.error("Control file %s does not exist", sys.argv[1])
        sys.exit()
    else:
        cfg_file_path = sys.argv[1]

# read the control file
cf_batch = ConfigObj(cfg_file_path, indent_type="    ", list_values=False)
# call the processing
pfp_batch.do_levels_batch(cf_batch)
