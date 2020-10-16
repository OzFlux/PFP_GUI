version_name = "PyFluxPro"
version_number = "V1.1.0"
# V1.1.0 - major changes (to be documented later)
# V1.0.2 - 6th August 2020 (long oerdue version change)
#        - check GitHub for what has been done since
#          5th August 2019
#        - most recent changes are:
#          - implementation of pfp_gui.TreeView() subclassed from QTreeView
#            to get the drag and drop behaviour we want
#          - rename Eva's second ustar filter method to "ustar (EvGb)"
# V1.0.1 - 5th August 2019
#        - remove redundant SOLO code at L6
#        - implement L1 to L4 batch processing
# V1.0.0 - 16th June 2019
#        - MAJOR CHANGES
#          - implement detection and filling of long gaps
#            at L5
#          - implement consistent way of handling program
#            settings and options at L4, L5 and L6
#          - move from PyQt4 to PyQt5
#          - many other changes along the way
# V0.9.2 - 7th October 2018
#        - implemented output to ECOSTRESS CSV file
#        - implemented L5 and L6 processing
#        - cleaned up the GUI routines in pfp_gui.py
# V0.9.1 - updated to PyFluxPro V0.1.5
#        - working steps at this stage are:
#          - L1 to L4
#          - concatenation
#          - climatology
# V0.9.0 - fork from main PyFluxPro at V0.1.1
#        - implement integrated GUI
# V0.1.1 - cumulative changes up to 13/07/2017
#        - major change to pfp_utils.CreateSeries()
#          - deprecated "FList=" argument
#          - made all arguments compulsory
#        - QC flag generated for each series immediately
#          prior to pfp_utils.CreateSeries() based solely
#          on series data mask
# V0.1.0 - copy of OzFluxQC V2.9.6f