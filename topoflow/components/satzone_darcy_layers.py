#
#  Copyright (c) 2001-2021, Scott D. Peckham
#
#  Nov 2016.
#  Sep 2014. 
#  Nov 2013.  Converted TopoFlow to Python package.
#  Jan 2013.  Revised handling of input/output names.
#  Oct 2012.  CSDMS Standard Names and BMI.
#  May 2010.  Changes to initialize(), read_cfg_file() and unit_test().
#  Aug 2009.  Updates.
#  Jul 2009.  Updates.
#  Jan 2009,  Converted from IDL.
#
#-----------------------------------------------------------------------
#  NOTES:  This file defines a "Darcy layers" groundwater component
#          and related functions.  It inherits from the groundwater
#          "base class" in "satzone_base.py".
#-----------------------------------------------------------------------
#
#  class satzone_component
#
#      get_component_name()
#      get_attribute()          # (10/26/11)
#      get_input_var_names()    # (5/16/12, Bolton)
#      get_output_var_names()   # (5/16/12, Bolton)
#      get_var_name()           # (5/16/12, Bolton)
#      get_var_units()          # (5/16/12, Bolton)
#      ------------------------------------------------------------     
#      Move all "update_*" methods from satzone_base.py to here ?
#      ------------------------------------------------------------    
#
#-----------------------------------------------------------------------

import numpy as np
import os

from topoflow.components import satzone_base

#-----------------------------------------------------------------------
class satzone_component( satzone_base.satzone_component ):

    _att_map = {
        'model_name':         'TopoFlow_Saturated_Zone_Darcy_Layers',
        'version':            '3.1',        
        'author_name':        'Scott D. Peckham',
        'grid_type':          'uniform',
        'time_step_type':     'fixed',
        'step_method':        'explicit',
        'time_units':         'seconds', 
        #-------------------------------------------------------------
        'comp_name':          'SatZoneDarcyLayers',
        'model_family':       'TopoFlow',
        'cfg_template_file':  'Satzone_Darcy_Layers.cfg.in',
        'cfg_extension':      '_satzone_darcy_layers.cfg' }
        # 'cmt_var_prefix':     '/SatZoneDarcyLayers/Input/Var/',
        # 'gui_xml_file':       '/home/csdms/cca/topoflow/3.1/src/share/cmt/gui/Satzone_Darcy_Layers.xml',
        # 'dialog_title':       'Saturated Zone: Darcy Layers Parameters',

      
    #----------------------------------------------
    # What about ET? (Taking water off the ground
    # water surface???  (Bolton, 5/16/2012)
    #----------------------------------------------
    _input_var_names = [
        'channel_water_x-section__mean_depth',              # (d@channels)
        'land_surface_water__evaporation_volume_flux',      # (ET@evap)
        'soil_water_sat-zone_top__recharge_volume_flux'  ]  # (Rg@infil)     

    _output_var_names = [
        'land_surface__elevation',                          # elev
        'land_surface_water__baseflow_volume_flux',         # GW
        'land_surface_water__domain_time_integral_of_baseflow_volume_flux',  # vol_GW
        'model__time_step',                                 # dt
        'model_soil_layer-0__porosity',                     # qs[0]
        'model_soil_layer-0__saturated_thickness',          # y[0,:,:]
        'model_soil_layer-0__thickness',                    # th[0,:,:]
        'model_soil_layer-1__porosity',                     # qs[1]
        'model_soil_layer-1__saturated_thickness',          # y[1,:,:]
        'model_soil_layer-1__thickness',                    # th[1,:,:]
        'model_soil_layer-2__porosity',                     # qs[2]
        'model_soil_layer-2__saturated_thickness',          # y[2,:,:]
        'model_soil_layer-2__thickness',                    # th[2,:,:]
        #----------------------------------------------
        # These are for *all* soil layers (not used).
        #----------------------------------------------
        # 'model_soil_layer__porosity',                       # qs
        # 'model_soil_layer__saturated_thickness',            # y
        # 'model_soil_layer__thickness',                      # th
        #----------------------------------------
        # The "top_layer" is same as "layer_0".
        #----------------------------------------
        'soil_water_sat-zone_top_surface__elevation',   # h_table  #############
        'soil_top-layer__porosity',                     # qs[0,:,:]
        'soil_top-layer__saturated_thickness',          # y[0,:,:]
        'soil_top-layer__thickness' ]                   # th[0,:,:]

        #-------------------------------------------
        # These are read from GUI/file, but could
        # still be returned.
        #-------------------------------------------
        # 'soil_water_sat-zone_top_surface__initial_elevation' ]   # h0_table

    #-------------------------------------------------------------------
    # Note: The variables qs, th and y are ndarrays.  If we define
    #       another variable as a slice or subset of these, such as
    #       qs_top = qs[0], or y_top = y[0,:,:], then they will
    #       also change whenever the main ndarray changes.
    #       To see this, try:
    #           >>> a = np.ones((3,3))
    #           >>> b = a[0,:]
    #           >>> print a
    #           >>> print b
    #           >>> a[0,:] = 2
    #           >>> print a
    #           >>> print b
    #       With this trick, we can avoid slices and subscripts in
    #       the var_name_map, which getattr and setattr don't support.
    #-------------------------------------------------------------------
    _var_name_map = {
        'channel_water_x-section__mean_depth':           'd',      # channels comp
        'soil_water_sat-zone_top__recharge_volume_flux': 'Rg',
        #------------------------------------------------------------------------
        'land_surface__elevation': 'elev',
        'land_surface_water__baseflow_volume_flux': 'GW',  
        'land_surface_water__domain_time_integral_of_baseflow_volume_flux': 'vol_GW',
        'land_surface_water__evaporation_volume_flux': 'ET',
        'model__time_step': 'dt',
        #----------------------------------------------------------------
        # These may be defined in satzone_base.py.  (9/22/14)
#         'model_soil_layer-0__porosity':            'qs_layer_0', ## 'qs[0]',
#         'model_soil_layer-0__saturated_thickness': 'y_layer_0',  ## 'y[0,:,:]',
#         'model_soil_layer-0__thickness':           'th_layer_0', ## 'th[0,:,:]',
#         'model_soil_layer-1__porosity':            'qs_layer_1',
#         'model_soil_layer-1__saturated_thickness': 'y_layer_1',
#         'model_soil_layer-1__thickness':           'th_layer_1',
#         'model_soil_layer-2__porosity':            'qs_layer_2',
#         'model_soil_layer-2__saturated_thickness': 'y_layer_2',
#         'model_soil_layer-2__thickness':           'th_layer_2',

        #----------------------------------------------
        # These are for *all* soil layers (not used).
        #----------------------------------------------
        # 'model_soil_layers__porosity':            'qs',
        # 'model_soil_layers__saturated_thickness': 'y',
        # 'model_soil_layers__thickness':           'th',
        #----------------------------------------
        # The "top_layer" is same as "layer_0".
        #----------------------------------------
        'soil_water_sat-zone_top_surface__elevation': 'h_table',
        'soil_top-layer__porosity':                   'qs_layer_0',  ## 'qs[0]',
        'soil_top-layer__saturated_thickness':        'y_layer_0',   ## 'y[0,:,:]',  
        'soil_top-layer__thickness':                  'th_layer_0' } ## 'th[0],
        
    _var_units_map = {
        'channel_water_x-section__mean_depth': 'm',      # channels comp
        'soil_water_sat-zone_top__recharge_volume_flux': 'm s-1',
        #----------------------------------------------------------------
        'land_surface__elevation': 'm',
        'land_surface_water__baseflow_volume_flux': 'm s-1',
        'land_surface_water__domain_time_integral_of_baseflow_volume_flux': 'm3',
        'land_surface_water__evaporation_volume_flux': 'm s-1',
        'model__time_step': 's',         ############# CHECK UNITS
        'model_soil_layer-0__porosity': '1',
        'model_soil_layer-0__saturated_thickness': 'm',
        'model_soil_layer-0__thickness':'m',
        'model_soil_layer-1__porosity': '1',
        'model_soil_layer-1__saturated_thickness': 'm',
        'model_soil_layer-1__thickness': 'm',
        'model_soil_layer-2__porosity': '1',
        'model_soil_layer-2__saturated_thickness': 'm',
        'model_soil_layer-2__thickness': 'm',
        #----------------------------------------------
        # These are for *all* soil layers (not used).
        #----------------------------------------------
        # 'model_soil_layers__porosity': '1',
        # 'model_soil_layers__saturated_thickness': 'm',
        # 'model_soil_layers__thickness': 'm',
        #----------------------------------------
        # The "top_layer" is same as "layer_0".
        #----------------------------------------
        'soil_water_sat-zone_top_surface__elevation': 'm',
        'soil_top-layer__porosity': '1',
        'soil_top-layer__saturated_thickness': 'm',
        'soil_top-layer__thickness': 'm' }

    #------------------------------------------------    
    # Return NumPy string arrays vs. Python lists ?
    #------------------------------------------------
    ## _input_var_names  = np.array( _input_var_names )
    ## _output_var_names = np.array( _output_var_names )

    #-------------------------------------------------------------------
    def get_component_name(self):
  
        return 'TopoFlow_Satzone_Darcy_Layers'

    #   get_component_name()     
    #-------------------------------------------------------------------
    def get_attribute(self, att_name):

        try:
            return self._att_map[ att_name.lower() ]
        except:
            print('###################################################')
            print(' ERROR: Could not find attribute: ' + att_name)
            print('###################################################')
            print(' ')

    #   get_attribute()
    #-------------------------------------------------------------------
    def get_input_var_names(self):

        #--------------------------------------------------------
        # Note: These are currently variables needed from other
        #       components vs. those read from files or GUI.
        #--------------------------------------------------------   
        return self._input_var_names
    
    #   get_input_var_names()
    #-------------------------------------------------------------------
    def get_output_var_names(self):
 
        return self._output_var_names
    
    #   get_output_var_names()
    #-------------------------------------------------------------------
    def get_var_name(self, long_var_name):
            
        return self._var_name_map[ long_var_name ]

    #   get_var_name()
    #-------------------------------------------------------------------
    def get_var_units(self, long_var_name):

        return self._var_units_map[ long_var_name ]
   
    #   get_var_units()
    #-------------------------------------------------------------------

