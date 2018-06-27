import glob
import ntpath
import os
import sys
# check the scripts directory is present
if not os.path.exists("../scripts/"):
    print "erai2nc: the scripts directory is missing"
    sys.exit()
# since the scripts directory is there, try importing the modules
sys.path.append('../scripts')
import qcio

cf = qcio.load_controlfile(path="../controlfiles")

base_pattern = "HM01X_Data*.txt"
in_file_pattern = cf["Files"]["In"]["file_path"]+base_pattern
in_file_list = sorted(glob.glob(in_file_pattern))
for in_filename in in_file_list:
    p = ntpath.basename(in_filename).split("_")
    out_filename = cf["Files"]["Out"]["file_path"]+p[0]+"_"+p[1]+"_"+p[2]+".csv"
    # open the output file
    out_file = open(out_filename,"a")
    # open the first input file and append
    print "Adding contents of "+in_filename+" to "+out_filename
    for line in open(in_filename):
        out_file.write(line)
    # now loop over the folders containing the files to be appended
    add_path_list = [cf["Files"]["Add"][i] for i in cf["Files"]["Add"].keys()]
    bom_id = in_filename.split("_")[2]
    for add_path in add_path_list:
        # build the file name
        add_filepattern = add_path+"HM01X_Data_"+bom_id+"*.txt"
        add_filename_list = sorted(glob.glob(add_filepattern))
        for add_filename in add_filename_list:
            #print "Appending contents of "+add_filename+" to "+out_filename
            add_file = open(add_filename)
            add_file.next()
            for line in add_file:
                out_file.write(line)
            add_file.close()
    out_file.close()