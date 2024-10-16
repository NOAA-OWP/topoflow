

# Copyright (c) 2001-2013, Scott D. Peckham

#---------------------------------------------------------------------
#
#   unit_test()
#   test_resolve_array()   # (9/20/11)
#
#---------------------------------------------------------------------
def unit_test(TREYNOR=False, KY_SUB=False, BEAVER=False,
              SILENT=False, REPORT=True):

    #---------------------------------------------------------------
    # NOTE! The tests will appear to fail if the existing flow
    #       grid used for comparison was computed using a flat
    #       resolution method other than "Iterative linking".
    #
    # The KY_Sub and Beaver DEMs were processed using RiverTools
    # 3.0 using the WGS_1984 ellipsoid model for computing lengths
    # and areas.  The "Iterative linking" method was used for both
    # as the "Flat resolution method", to make them comparable to
    # the ones generated by functions in d8_base.py and
    # fill_pits.py.  Older version of these data sets used other
    # methods and can't be compared directly.
    #
    # Make sure that LINK_FLATS=True, LR_PERIODIC=False, and
    # TB_PERIODIC=False in CFG file.
    #
    # NB! There is another "local" test in update_area_grid().
    #
    # NB! "d8.A_units" is read from CFG file "*_d8.cfg" and needs
    #     to be km^2 whenever RT3_TEST is used.
    #---------------------------------------------------------------
    if not(TREYNOR or KY_SUB or BEAVER):
        TREYNOR = True
    start = time.time()

    #------------------------------------------------------
    # Example of DEM with fixed-angle pixels (Geographic)
    #     min(da) = 6802.824074169645  [m^2]
    #     max(da) = 6837.699120083246  [m^2]
    #     min(A)  =    0.000000000000  [km^2]
    #     max(A)  =  807.063354492188  [km^2]
    #------------------------------------------------------
    if (KY_SUB):
        # cfg_directory = '/Applications/Erode/Data/KY_Sub/'
        cfg_directory = '/home/csdms/models/erode/0.5/share/data/KY_Sub/'
        cfg_prefix    = 'KY_Sub'

    #------------------------------------------------
    # Example of DEM with fixed-length pixels (UTM)
    #     min(da) = 900.000  [m^2]
    #     max(da) = 900.000  [m^2]
    #     min(A)  =   0.000000000000  [km^2]
    #     max(A)  = 681.914184570312  [km^2]
    #------------------------------------------------
    if (BEAVER):
        # cfg_directory = '/Applications/Erode/Data/Beaver/'
        cfg_directory = '/home/csdms/models/erode/0.5/share/data/Beaver_Creek_KY/'
        cfg_prefix    = 'Beaver'
    if (TREYNOR):
        # cfg_directory = '/Applications/Erode/Data/Treynor_Iowa/'
        cfg_directory = '/home/csdms/models/erode/0.5/share/data/Treynor_Iowa/'
        cfg_prefix    = 'Treynor'
    
    #-------------------------------------------------
    # NOTE: The Treynor_Iowa DEM has no depressions!
    #-------------------------------------------------   
##    cfg_directory = tf_utils.TF_Test_Directory()
##    cfg_prefix    = tf_utils.TF_Test_Data_Prefix()
  
    d8 = d8_component()
    d8.CCA    = False
    d8.DEBUG  = True # (check flow and area grid against existing)
    d8.SILENT = SILENT
    d8.REPORT = REPORT

    #--------------------------
    # Change to cfg_directory
    #--------------------------
    os.chdir( cfg_directory )
    d8.initialize(cfg_prefix=cfg_prefix, mode="main",
                  SILENT=SILENT, REPORT=REPORT)
    d8.RT3_TEST = True  # (compare flow and area grid to RT3)
    d8.update(SILENT=SILENT, REPORT=REPORT)
    print('grid nx =', d8.nx)
    print('grid ny =', d8.ny)
    print('Run time =', (time.time() - start), ' [secs]')
    print('Finished with unit_test().')
    print(' ')
                
#   unit_test()
#-----------------------------------------------------------------------
def test_resolve_array():

    #---------------------------------------------------
    # Notes: Identical to RT3 resolve array (9/20/11).
    #        total(resolve) = 10161.   # (in RT3)
    #        RT3 resolve array is:
    #-------------------------------------------------------------------
    ##   0   1   2   2   4   1   2   2   8   8   2   2   8   8   2   2
    ##  16   1   2   2   4   4   2   2   8   8   8   2   8   8   8   2
    ##  32  32   2   2  32  32   2   2   8   8   8   2   8   8   8   2
    ##  32  32  32  32  32  32   2   2   8   8   8   8   8   8   8   8
    ##  64  64   2   2   4   1   2   2   8   8   2   2   8   8   2   2
    ##  16  64   2   2  16   1   2   2   8   8   8   2   8   8   8   2
    ##  32  32  32  32  32  32   2   2  32  32  32   2   8   8   8   2
    ##  32  32  32  32  32  32  32   2  32  32  32  32   8   8   8   8
    ## 128 128 128 128 128 128   2   2   8 128   2   2   8 128   2   2
    ## 128 128 128 128 128 128   2   2   8   8   8   2   8   8   8   2
    ##  32 128 128 128  32 128   2   2  32 128   2   2   8   8   8   2
    ##  32  32  32 128  32  32  32   2  32  32  32   8   8   8   8   2
    ## 128 128 128 128 128 128 128 128 128 128 128 128 128 128   2   2
    ## 128 128 128 128 128 128 128 128   8 128 128 128   8   8   8   2
    ##  32 128 128 128  32 128 128 128  32 128 128 128  32 128   2 128
    ##  32  32  32 128  32  32  32 128  32  32  32  32  32  32   8   8
    #------------------------------------------------------------------- 
    d8 = d8_component()
    d8.get_resolve_array(REPORT=True)
    print('d8.resolve.shape =', d8.resolve.shape)
    print('d8.resolve[252:]  =', d8.resolve[252:])
    print('d8.resolve[227]   =', d8.resolve[227])
    # print 'd8.resolve[5,5]  =', d8.resolve[5,5]  # (error)
    print(' ')
    
#   test_resolve_array()   
#-----------------------------------------------------------------------
