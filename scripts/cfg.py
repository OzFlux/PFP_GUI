version_name = "PyFluxPro"
version_number = "V0.9.2"
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