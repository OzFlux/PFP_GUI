version_name = "PyFluxPro"
version_number = "V0.1.1"
# V0.1.0 - copy of OzFluxQC V2.9.6f
# V0.1.1 - cumulative changes up to 13/07/2017
#        - major change to pfp_utils.CreateSeries()
#          - deprecated "FList=" argument
#          - made all arguments compulsory
#        - QC flag generated for each series immediately
#          prior to pfp_utils.CreateSeries() based solely
#          on series data mask