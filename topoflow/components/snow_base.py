"""
This file defines a "base class" for snowmelt components as well
as functions used by most or all snowmelt methods.  That is, all
snowmelt components inherit methods from this class.  The methods
of this class should be over-ridden as necessary (especially the
"update_meltrate() method) for different methods of modeling
snowmelt.  This class, in turn, inherits from the "BMI base class"
in BMI_base.py.

See snow_degree_day.py and snow_energy_balance.py.
"""
#-----------------------------------------------------------------------
#
#  Copyright (c) 2001-2023, Scott D. Peckham
#
#  Sep 2023.  Added update_density_ratio().
#             Fixed bug in enforce_max_meltrate().
#             Moved initialize_cold_content() from snow_energy_balance.py
#               back to this base class.  Note that T0 plays 2 roles in
#               the degree-day component, in meltrate and cold_content.
#               Degree-day comp now has option to set T0_cc in its CFG.
#  Aug 2023.  Added update_total_snowpack_water_volume(),
#               called from initialize() and finalize() and
#               removed update_swe_integral().
#             More careful to distinguish volumes that are area-time
#             integrals of fluxes and those that are area integrals.
#  May 2020.  Added update_swe_integral() and vol_swe.
#             Added disable_all_output().
#  Sep 2014.  Bug fix: enforce_max_meltrate() was called after update_SM_integral().
#             Moved open_input_files(), read_input_files() and close_input_files()
#             as special versions into degree-day and energy-balance components.
#  Aug 2014.  Cleaned up enforce_max_meltrate().
#  Nov 2013.  Converted TopoFlow to Python package.
#  May 2010.  Changes to initialize() and read_cfg_file().
#  Aug 2009.  Updates.
#  Jul 2009.  Updates.
#  May 2009.  Updates.
#  Jan 2009,  Converted from IDL.
#
#-----------------------------------------------------------------------
#  NOTES:  This file defines a "base class" for snowmelt
#          components as well as functions used by most or
#          all snowmelt methods.  The methods of this class
#          should be over-ridden as necessary for different
#          methods of modeling snowmelt.

#          update_snow_vars() in precip.py sets values here.
#-----------------------------------------------------------------------
#
#  class snow_component    (inherits from BMI_base.py)
#
#      set_constants()
#      -----------------------
#      initialize()
#      update()
#      finalize()
#      set_computed_input_vars()
#      --------------------------
#      set_missing_cfg_options()   # 2023-09-25 (placeholder)
#      check_input_types()
#      initialize_computed_vars()
#      initialize_cold_content()   # NEED TO RENAME T0 for CC
#      ----------------------------
#      update_meltrate()
#      enforce_max_meltrate()
#      update_SM_integral()
#      update_cold_content()
#      update_swe()
#      update_density_ratio()
#      update_depth()
#      update_total_snowpack_water_volume()
#      -----------------------
#      open_input_files()
#      read_input_files()
#      close_input_files()
#      -----------------------
#      update_outfile_names()
#      open_output_files()
#      write_output_files()
#      close_output_files()
#      save_grids()
#      save_pixel_values()
#
#-----------------------------------------------------------------------

import numpy as np
import os

from topoflow.utils import BMI_base
# from topoflow.utils import model_input  # (not used here)
from topoflow.utils import model_output

#-----------------------------------------------------------------------
class snow_component( BMI_base.BMI_component ):


    #------------------------------------------------------------
    # Notes: rho_H2O, Cp_snow, rho_air and Cp_air are currently
    #        hardwired (not adjustable with GUI).
    #------------------------------------------------------------
    def set_constants(self):

        #-----------------------------------
        # Constants not changeable by user
        #---------------------------------------------------------
        # Cp_snow = mass-specific isobaric heat capacity of snow
        #           value from:  NCAR CSM Flux Coupler web page
        #---------------------------------------------------------
        # Lf = latent heat of fusion for water [J kg -1]
        #---------------------------------------------------------        
        self.Cp_snow  = np.float64( 2090.0 )  # [J kg-1 K-1]
        self.Lf       = np.float64( 334000 )  # [J kg-1]

        #--------------------------------------
        # Not a constant; read from CFG file.
        #--------------------------------------
        ## self.rho_snow = np.float64(300)
        ## self.rho_H2O  = np.float64(1000)  # (See initialize() method.)
                
    #   set_constants()  
    #-------------------------------------------------------------------
    def latent_heat_of_sublimation(self):

        #----------------------------------------------------------    
        # Notes:  See:  http://en.wikipedia.org/wiki/Latent_heat
        #         Valid for T in [-40, 0] deg C.
        #----------------------------------------------------------
        # sublimation/deposition.  What about fusion/melting?
        # deposition, desublimation and resublimation are synonyms
        #----------------------------------------------------------
        a = np.float64( 2834.1 )
        b = np.float64( -0.29 )
        c = np.float64( -0.004 )
        T = self.T_air
        
        self.Lf = a + (b * T) + (c * (T**2))  # [J g-1]
        self.Lf *= np.float64( 1000 ) # [J kg-1]
        
    #   latent_heat_of_sublimation()       
    #-------------------------------------------------------------------
    def initialize(self, cfg_file=None, mode="nondriver",
                   SILENT=False):

        self.SILENT = SILENT

        #---------------------------------------------------------
        # Notes:  Need to make sure than h_swe matches h_snow ?
        #         User may have entered incompatible values.
        #---------------------------------------------------------
        # (3/14/07) If the Energy Balance method is used for ET,
        # then we must initialize and track snow depth even if
        # there is no snowmelt method because the snow depth
        # affects the ET rate.  Otherwise, return to caller.
        #---------------------------------------------------------
        if not(self.SILENT):
            print(' ')
            print('Snow component: Initializing...')
            
        self.status     = 'initializing'  # (OpenMI 2.0 convention)
        self.mode       = mode
        self.cfg_file   = cfg_file
        
        #-----------------------------------------------
        # Load component parameters from a config file
        #-----------------------------------------------       
        self.set_constants()
        self.initialize_config_vars()
        self.set_missing_cfg_options() 
        ## self.read_grid_info()    # NOW IN initialize_config_vars()
        self.initialize_basin_vars()  # (5/14/10)
        #-----------------------------------------
        # This must come before "Disabled" test.
        #-----------------------------------------
        self.initialize_time_vars()
   
        if (self.comp_status.lower() == 'disabled'):
            if not(self.SILENT):
                print('Snow component: Disabled in CFG file.')
            self.disable_all_output()
            self.h_snow  = self.initialize_scalar(0, dtype='float64')
            self.h_swe   = self.initialize_scalar(0, dtype='float64')
            self.SM      = self.initialize_scalar(0, dtype='float64')
            # vol_SM is an area-time integral over all cells in DEM
            self.vol_SM  = self.initialize_scalar(0, dtype='float64') # [m3]
            # vol_swe is an area integral over all cells in DEM.
            self.vol_swe_start = self.initialize_scalar(0, dtype='float64') # [m3]
            self.vol_swe = self.initialize_scalar(0, dtype='float64') # [m3]
            self.DONE    = True
            self.status  = 'initialized'
            return
 
        #----------------------------------------
        # Initialize vars to be read from files
        #----------------------------------------
        self.initialize_input_file_vars()
 
        #---------------------------------------------
        # Open input files needed to initialize vars 
        #---------------------------------------------
        self.open_input_files()
        self.read_input_files()

        #---------------------------
        # Initialize computed vars
        #---------------------------
        self.check_input_types()  # (maybe not used yet)
        self.initialize_computed_vars()  # (h_snow, h_swe, etc.)

        self.open_output_files()
        self.status = 'initialized'        
        
    #   initialize()
    #-------------------------------------------------------------------
    def update(self, dt=-1.0):

        #----------------------------------------------------------
        # Note: The read_input_files() method is first called by
        #       the initialize() method.  Then, the update()
        #       method is called one or more times, and it calls
        #       other update_*() methods to compute additional
        #       variables using input data that was last read.
        #       Based on this pattern, read_input_files() should
        #       be called at end of update() method as done here.
        #       If the input files don't contain any additional
        #       data, the last data read persists by default.
        #----------------------------------------------------------

        #--------------------------------
        # Has component been disabled ?
        #-------------------------------------------------
        # Note: self.SM already set to 0 by initialize()
        #-------------------------------------------------
        if (self.comp_status.lower() == 'disabled'):
            # Note: self.status should be 'initialized'.
            return

        #-----------------------------------------
        # Read next snow vars from input files ?
        #-----------------------------------------------------       
        # Note: read_input_files() is called by initialize()
        # and those values must be used for the "update"
        # calls before reading new ones.
        #-----------------------------------------------------
        self.status = 'updating'
        if (self.time_index > 0):
            self.read_input_files()
                   
        #-------------------------
        # Update computed values 
        #-------------------------
        self.update_meltrate()       # (meltrate = SM)
        self.enforce_max_meltrate()  # (before SM integral!)
        self.update_SM_integral()
        self.update_cold_content()

        #------------------------------------------
        # Call update_swe() before update_depth()
        #------------------------------------------
        self.update_swe()
        self.update_density_ratio()  # 2023-09-11
        self.update_depth()

        #----------------------------------------------
        # Write user-specified data to output files ?
        #----------------------------------------------
        # Components use own self.time_sec by default.
        #-----------------------------------------------
        self.write_output_files()
        ## self.write_output_files( time_seconds )

        #-----------------------------
        # Update internal clock
        # after write_output_files()
        #-----------------------------
        self.update_time( dt )
        self.status = 'updated'  # (OpenMI)
        
    #   update()
    #-------------------------------------------------------------------
    def finalize(self):

        #--------------------------------
        # Has component been disabled ?
        #--------------------------------
        if (self.comp_status.lower() == 'disabled'):
            # Note: self.status should be 'initialized'.
            return

        self.status = 'finalizing'
        self.update_total_snowpack_water_volume()  # (2023-08-31)
        self.close_input_files()   ##  TopoFlow input "data streams"
        self.close_output_files()
        if not(self.SILENT):
            self.print_final_report(comp_name='Snow component')
        self.status = 'finalized'
               
    #   finalize()
    #-------------------------------------------------------------------
    def set_computed_input_vars(self):

        #---------------------------------------------------------
        # Make sure that all "save_dts" are larger or equal to
        # the specified process dt.  There is no point in saving
        # results more often than they change.
        # Issue a message to this effect if any are smaller ??
        #---------------------------------------------------------
        np.maximum(self.save_grid_dt,   self.dt, out=self.save_grid_dt)
        np.maximum(self.save_pixels_dt, self.dt, out=self.save_pixels_dt)
        
    #   set_computed_input_vars()
    #-------------------------------------------------------------------
    def set_missing_cfg_options(self):

        #-------------------------------------------------------  
        # Note: This is called in initialize() AFTER calling
        #       initialize_config_vars().  It is used to set
        #       newer toggles, etc. that may not have been
        #       set in the CFG file.
        #-------------------------------------------------------    
        pass
        
    #   set_missing_cfg_options()            
    #-------------------------------------------------------------------
    def check_input_types(self):

        #----------------------------------------------------
        # Notes: Usually this will be overridden by a given
        #        method of computing snow meltrate.
        #----------------------------------------------------
        # Notes: rho_H2O, Cp_snow, rho_air and Cp_air are
        #        currently always scalars.
        #----------------------------------------------------        
        are_scalars = np.array([
                          self.is_scalar('P_snow'),
                          self.is_scalar('rho_H2O'),
                          self.is_scalar('rho_air'),
                          self.is_scalar('Cp_air'),
                          #----------------------------------
                          self.is_scalar('rho_snow'),
                          self.is_scalar('Cp_snow'),
                          self.is_scalar('h0_snow'),
                          self.is_scalar('h0_swe') ])

        self.ALL_SCALARS = np.all(are_scalars)
  
    #   check_input_types()
    #-------------------------------------------------------------------
    def initialize_computed_vars(self):

        #------------------------------------------
        # If T_air or precip are grids, then make
        # sure that h_snow and h_swe are grids
        #------------------------------------------
        T_IS_GRID = self.is_grid('T_air')
        P_IS_GRID = self.is_grid('P_snow')
        H0_SNOW_IS_SCALAR = self.is_scalar('h0_snow')
        H0_SWE_IS_SCALAR  = self.is_scalar('h0_swe') 
        comp_name = self.get_component_name()
        EN_BAL_COMP = (comp_name == 'TopoFlow_Snow_Energy_Balance')
        
        # Used to make sure this was working as expected.
#         print('###############################################')
#         print(' In snow_base.initialize_computed_vars():')
#         print(' EN_BAL_COMP =', EN_BAL_COMP)
#         print('###############################################')

        #------------------------------------------------------
        # If h0_snow or h0_swe are scalars, the use of copy()
        # here requires they were converted to numpy scalars.
        # Using copy() may not be necessary for scalars.
        #------------------------------------------------------
        h_snow = self.h0_snow.copy()    # [meters]
        h_swe  = self.h0_swe.copy()     # [meters]
          
        if (T_IS_GRID or P_IS_GRID or EN_BAL_COMP):
            self.SM = np.zeros([self.ny, self.nx], dtype='float64')
            #------------------------------------------------------       
            # For the Energy Balance method, SM, h_snow and h_swe
            # are always grids because Q_sum is always a grid.
            #------------------------------------------------------
            # Convert both h_snow and h_swe to grids, if not
            # already grids.
            #------------------------------------------------------
            if (H0_SNOW_IS_SCALAR):
                self.h_snow = h_snow + np.zeros([self.ny, self.nx], dtype='float64')
            else:
                self.h_snow = h_snow  # (is already a grid)
            #------------------------------------------------
            if (H0_SWE_IS_SCALAR):
                self.h_swe = h_swe + np.zeros([self.ny, self.nx], dtype='float64')
            else:
                self.h_swe = h_swe    # (is already a grid)              
        else:
            #--------------------------------------------------------
            # Both are scalars and that's OK for snow_degree_day.py
            #--------------------------------------------------------
            self.SM     = self.initialize_scalar( 0, dtype='float64')
            self.h_snow = self.initialize_scalar( h_snow, dtype='float64')
            self.h_swe  = self.initialize_scalar( h_swe,  dtype='float64')

        #---------------------------------------------------------------------
        # vol_SM is the time integral of the total volume (over all
        #   grid cells in the DEM) of snow that has ever melted.
        # vol_swe is the current (or final) total volume (over all
        #   grid cells in the DEM) of liquid water stored in the snowpack.
        #---------------------------------------------------------------------
        self.vol_SM  = self.initialize_scalar( 0, dtype='float64') # (m3)
        self.vol_swe = self.initialize_scalar( 0, dtype='float64') # (m3)
        
        self.update_total_snowpack_water_volume()
        self.vol_swe_start = self.vol_swe.copy()

        #----------------------------------------------------
        # Compute density ratio for water to snow.
        # rho_H2O is for liquid water close to 0 degrees C.
        # Water is denser than snow, so density_ratio > 1.
        #----------------------------------------------------
        # Since rho_snow varies in time when rho_type is
        # Time Series or Grid Grid Sequence, we now have
        # an update_density_ratio() function.
        #----------------------------------------------------
        self.density_ratio = (self.rho_H2O / self.rho_snow)
                
        #------------------------------------------
        # Initialize the cold content of snowpack
        #------------------------------------------
        self.initialize_cold_content()
        
    #   initialize_computed_vars()
    #---------------------------------------------------------------------
    def initialize_cold_content( self ):

        #----------------------------------------------------------------
        # NOTES: This function is used to initialize the cold content
        #        of a snowpack.
        #        The cold content has units of [J m-2] (_NOT_ [W m-2]).
        #        It is an energy (per unit area) threshold (or deficit)
        #        that must be overcome before melting of snow can occur.
        #        Cold content changes over time as the snowpack warms or
        #        cools, but must always be non-negative.
        #
        #        K_snow is between 0.063 and 0.71  [W m-1 K-1]
        #        All of the Q's have units of W m-2 = J s-1 m-2).
        #
        #        T0 is read from the config file.
        #        The degree-day component has another T0 for meltrate,
        #        but now T0_cc can also be specified in its CFG file.
        #        See it's "set_missing_cfg_options()" method.
        #        For the energy-balance comp, it's T0 is T0_cc.
        #        This is the last var to be set in initialize().
        #---------------------------------------------------------------
        if not(hasattr(self, 'T0_cc')):
           self.T0_cc = self.T0   # synonyms

        #--------------------------------------------
        # Compute initial cold content of snowpack
        # See equation (10) in Zhang et al. (2000).
        #--------------------------------------------
        T_snow   = self.T_surf
        del_T    = (self.T0_cc - T_snow)
        self.Ecc = (self.rho_snow * self.Cp_snow) * self.h0_snow * del_T

        #------------------------------------        
        # Cold content must be nonnegative.
        #----------------------------------------------
        # Ecc > 0 if (T_snow < T0).  i.e. T_snow < 0.
        #----------------------------------------------
        np.maximum( self.Ecc, np.float64(0), out=self.Ecc)  # (in place)
        
    #   initialize_cold_content()
    #-------------------------------------------------------------------
    def update_meltrate(self):
 
        #---------------------------------------------------------
        # Notes: This is for a "potential" meltrate, which can't
        #        be realized unless there is enough snow.
        #        See snow_base.enforce_max_meltrate().   
        #---------------------------------------------------------
        # Note: We don't need to update any variables if
        #       the snowmelt method is None.  But we need
        #       to make sure that self.SM = 0.0.
        #       This "method" will be over-ridden by a
        #       particular snowmelt method.
        #--------------------------------------------------
        print('ERROR: update_meltrate() method for Snow component')
        print('       has not been implemented.')
       
    #   update_meltrate()
    #-------------------------------------------------------------------
    def enforce_max_meltrate(self):

        #--------------------------------------------------------
        # New version to fix bug:  2023-09-12. 
        # The max possible meltrate would be if all snow (given
        # by snow depth, h_snow, were to melt in the one time
        # step, dt.  Meltrate should never exceed this value.
        # Recall that: (h_snow / h_swe) = (rho_H2O / rho_snow)
        #                               = density_ratio > 1
        # So h_swe = h_snow / density_ratio.
        # Previous version had a bug; see below. 
        # Now also using "out" keyword for "in-place".  
        #-------------------------------------------------------- 
        SM_max = self.h_swe / self.dt
        np.minimum(self.SM, SM_max, out=self.SM)  # [m s-1]

        #------------------------------------------------------
        # Make sure meltrate is positive, while we're at it ?
        # Is already done by "Energy-Balance" component.
        #------------------------------------------------------
        np.maximum(self.SM, np.float64(0), out=self.SM)
                    
    #   enforce_max_meltrate()
#     #-------------------------------------------------------------------
#     def enforce_max_meltrate_BUG(self):
#   
#         #-------------------------------------------------------
#         # This version has a bug.  Should have been:
#         # SM_max = self.h_snow / (density_ratio * self.dt)
#         # The max possible meltrate would be if all snow (given
#         # by snow depth, h_snow, were to melt in the one time
#         # step, dt.  Meltrate should never exceed this value.
#         #------------------------------------------------------- 
#         density_ratio = (self.rho_H2O / self.rho_snow)
#         SM_max = (density_ratio / self.dt) * self.h_snow 
#         self.SM = np.minimum(self.SM, SM_max)  # [m s-1]
#         
#         #------------------------------------------------------
#         # Make sure meltrate is positive, while we're at it ?
#         # Is already done by "Energy-Balance" component.
#         #------------------------------------------------------
#         self.SM = np.maximum(self.SM, np.float64(0))
#    
#     #   enforce_max_meltrate_BUG()
    #-------------------------------------------------------------------
    def update_SM_integral(self):

        #------------------------------------------------
        # Update mass total for SM, sum over all pixels
        #------------------------------------------------   
        volume = np.float64(self.SM * self.da * self.dt)  # [m^3]
        if (np.size(volume) == 1):
            self.vol_SM += (volume * self.rti.n_pixels)
        else:
            self.vol_SM += np.sum(volume)
            
    #   update_SM_integral()
    #-------------------------------------------------------------------
    def update_cold_content(self):

        #-----------------------------------------------------------    
        # 2023-09-25. This is overridden in snow_energy_balance.py
        # and could do the same in snow_degree_day.py using some
        # other (temperature-based) method.
        #-----------------------------------------------------------
        pass

    #   update_cold_content()
    #-------------------------------------------------------------------
    def update_swe(self):

        #--------------------------------------------------------
        # Note: The Meteorology component uses air temperature
        # to compute P_rain (precip that falls as liquid) and
        # P_snow (precip that falls as snow or ice) separately.
        # P_snow = (self.P * (self.T_air <= 0)) 
        #----------------------------------------------------------
        # Note: This method must be written to work regardless
        # of whether P_rain and T are scalars or grids. (3/14/07)
        #------------------------------------------------------------
        # If P or T_air is a grid, then h_swe and h_snow are grids.
        # This is set up in initialize_computed_vars().
        #------------------------------------------------------------
        # All updates to h_swe are done using "in-place" methods.
        #------------------------------------------------------------
              
        #------------------------------------------------
        # Increase snow water equivalent due to snowfall
        #------------------------------------------------
        # P_snow is a "water equivalent" volume flux
        # that was determined from a total volume flux
        # and a rain-snow temperature threshold.
        #------------------------------------------------        
        # Meteorology and Channel components may have
        # different time steps, but then self.P_snow
        # will be a time-interpolated value.
        #------------------------------------------------
        dh1_swe = (self.P_snow * self.dt)  # [m]
        self.h_swe += dh1_swe

        #------------------------------------------------
        # Decrease snow water equivalent due to melting
        #------------------------------------------------
        # Note that SM depends partly on h_snow due to
        # enforce_max_meltrate() in snow_base.py.
        #------------------------------------------------
        dh2_swe    = self.SM * self.dt
        self.h_swe -= dh2_swe

        #------------------------------------------        
        # This shouldn't be necessary if SM >= 0.
        #------------------------------------------
        np.maximum(self.h_swe, np.float64(0), self.h_swe)  # (in place)

        #-----------------------------------------------      
        # Set SWE to 0 on edges of grid ? (2023-09-11)
        #-----------------------------------------------
        # self.h_swe[ self.edge_IDs ] = 0.0
          
    #   update_swe()
    #-------------------------------------------------------------------
    def update_density_ratio(self):

        #-----------------------------------------------    
        # Return if density_ratio is constant in time.
        #-----------------------------------------------
        if (self.rho_snow_type.lower() in ['scalar', 'grid']):
            return
        density_ratio = self.rho_H2O / self.rho_snow

        #-------------------------------------             
        # Save updated density ratio in self
        #-------------------------------------
        if (np.ndim( self.density_ratio ) == 0):
            density_ratio = np.float64( density_ratio )  ### (from 0D array to scalar)
            self.density_ratio.fill( density_ratio )     ### (mutable scalar)
        else:
            self.density_ratio[:] = density_ratio

    #   update_density_ratio()
    #-------------------------------------------------------------------
    def update_depth(self):

        #--------------------------------------------------------
        # Note: The Meteorology component uses air temperature
        # to compute P_rain (precip that falls as liquid) and
        # P_snow (precip that falls as snow or ice) separately.
        # P_snow = (self.P * (self.T_air <= 0)) 
        #----------------------------------------------------------
        # Note: This method must be written to work regardless
        # of whether P_rain and T are scalars or grids. (3/14/07)
        #------------------------------------------------------------
        # If P or T_air is a grid, then h_swe and h_snow are grids.
        # This is set up in initialize_computed_vars().
        #------------------------------------------------------------
        # Note that for a region of area, A:
        #     rho_snow = (mass_snow / (h_snow * A))
        #     rho_H2O  = (mass_H20  / (h_swe * A))
        # Since mass_snow = mass_H20 (for SWE):
        #     rho_snow * h_snow = rho_H2O * h_swe
        #     (h_snow / h_swe)  = (rho_H2O / rho_snow) = density_ratio > 1
        #      h_snow = h_swe * density_ratio
        # Since liquid water is denser than snow:
        #      density_ratio > 1 and
        #      h_snow > h_swe
        #------------------------------------------------------------
        # See TopoFlow_Rainfall_Inputs.ipynb, GLDAS section for
        #   how to convert mass_flux to volume_flux.
        # Suppose we are given total precip as [kg m-2 s-1] from GLDAS.
        # For precip that falls as rain (liquid):
        #   volume_flux = 3600 * mass_flux  [mm h-1]
        # For precip that falls as snow:
        #   rho_H2O     = 1000 kg m-3
        #   rho_snow    = 200  kg m-3 (for example)
        #   volume_flux = 3600 * (rho_H2O / rho_snow) * mass_flux [mm h-1]
        #   volume_flux = 18000 * mass_flux  [mm h-1]
        #------------------------------------------------------------

        #------------------------------------------ 
        # Increase snow depth due to falling snow
        #-------------------------------------------
        # This assumes that update_swe() is called
        # before update_depth().
        #-------------------------------------------
        h_snow = self.h_swe * self.density_ratio
        
        #-------------------------------------
        # Decrease snow depth due to melting
        #-------------------------------------------
        # Don't need this; the loss due to melting
        # was already removed in update_swe().
        #-------------------------------------------   
#         dh     = self.SM * (self.density_ratio * self.dt)
#         np.maximum((h_snow - dh), np.float64(0), out=h_snow)

        #--------------
        # For testing
        #--------------
#         print 'type(density_ratio) =', type(self.density_ratio)
#         print 'type(self.h_swe) =', type(self.h_swe)
#         print 'type(h_snow) =', type(h_snow)
#         print 'type(self.SM) =', type(self.SM)
#         print 'rank(self.SM) =', np.ndim(self.SM)
        
        #----------------------------------             
        # Save updated snow depth in self
        #----------------------------------
        if (np.ndim( self.h_snow ) == 0):
            h_snow = np.float64( h_snow )  ### (from 0D array to scalar)
            self.h_snow.fill( h_snow )     ### (mutable scalar)
        else:
            self.h_snow[:] = h_snow
        
    #   update_depth()
    #-------------------------------------------------------------------  
    def update_total_snowpack_water_volume(self):

        #--------------------------------------------------------   
        # Note:  Compute the total volume of water stored
        #        in the snowpack for all grid cells in the DEM.
        #        Use this in the final mass balance reporting.
        #        (2023-08-31)
        #--------------------------------------------------------        
        # Note:  This is called from initialize() & finalize().
        #--------------------------------------------------------
  
        #----------------------------------------------------
        # Update total volume of liquid water stored in the
        # current snowpack, sum over all grid cells but no
        # integral over time.  (2023-08-31)
        #----------------------------------------------------   
        volume = np.float64(self.h_swe * self.da)  # [m^3]
        if (np.size(volume) == 1):
            vol_swe = (volume * self.rti.n_pixels)
        else:
            ## volume[ self.edge_IDs ] = 0.0  # (not needed)
            vol_swe = np.sum(volume)

        self.vol_swe.fill( vol_swe )
    
    #   update_total_snowpack_water_volume() 
    #-------------------------------------------------------------------  
    def open_input_files(self):

        #------------------------------------------------------
        # Each component that inherits from snow_base.py must
        # implement its own versions of these.
        #------------------------------------------------------
        print('ERROR: open_input_files() for Snow component')
        print('       has not been implemented.')

    #   open_input_files()
    #-------------------------------------------------------------------  
    def read_input_files(self):

        print('ERROR: read_input_files() for Snow component')
        print('       has not been implemented.')
        
    #   read_input_files()       
    #-------------------------------------------------------------------  
    def close_input_files(self):

        print('ERROR: close_input_files() for Snow component')
        print('       has not been implemented.')

    #   close_input_files()
    #-------------------------------------------------------------------  
    def update_outfile_names(self):

        #-------------------------------------------------
        # Notes:  Append out_directory to outfile names.
        #-------------------------------------------------
        self.mr_gs_file = (self.out_directory + self.mr_gs_file)
        self.hs_gs_file = (self.out_directory + self.hs_gs_file)
        self.sw_gs_file = (self.out_directory + self.sw_gs_file)
        self.cc_gs_file = (self.out_directory + self.cc_gs_file)
        #---------------------------------------------------------
        self.mr_ts_file = (self.out_directory + self.mr_ts_file)
        self.hs_ts_file = (self.out_directory + self.hs_ts_file)
        self.sw_ts_file = (self.out_directory + self.sw_ts_file)
        self.cc_ts_file = (self.out_directory + self.cc_ts_file)

    #   update_outfile_names()
    #-------------------------------------------------------------------  
    def disable_all_output(self):
    
        self.SAVE_MR_GRIDS  = False
        self.SAVE_HS_GRIDS  = False
        self.SAVE_SW_GRIDS  = False
        self.SAVE_CC_GRIDS  = False
        #-------------------------------
        self.SAVE_MR_PIXELS = False
        self.SAVE_HS_PIXELS  = False
        self.SAVE_SW_PIXELS  = False
        self.SAVE_CC_PIXELS  = False
        
    #   disable_all_output()  
    #-------------------------------------------------------------------  
    def open_output_files(self):

        model_output.check_netcdf( SILENT=self.SILENT )
        self.update_outfile_names()
        
        #----------------------------------
        # Open files to write grid stacks
        #----------------------------------
        if (self.SAVE_MR_GRIDS):
            model_output.open_new_gs_file( self, self.mr_gs_file, self.rti,
                                           ## var_name='MR',
                                           var_name='mr',
                                           ## var_name='SM', 
                                           long_name='snow_meltrate',
                                           units_name='m/s')
            
        if (self.SAVE_HS_GRIDS):
            model_output.open_new_gs_file( self, self.hs_gs_file, self.rti,
                                           ## var_name='h_snow',
                                           var_name='hs',
                                           long_name='snow_depth',
                                           units_name='m')
            
        if (self.SAVE_SW_GRIDS):
            model_output.open_new_gs_file( self, self.sw_gs_file, self.rti,
                                           ## var_name='SWE',
                                           var_name='sw',
                                           long_name='snow_water_equivalent_depth',
                                           units_name='m')
            
        if (self.SAVE_CC_GRIDS):
            model_output.open_new_gs_file( self, self.cc_gs_file, self.rti,
                                           ## var_name='SCC',
                                           var_name='cc',
                                           long_name='snow_cold_content',
                                           units_name='J/m^2')

        #---------------------------------------
        # Open text files to write time series
        #---------------------------------------
        IDs = self.outlet_IDs
        if (self.SAVE_MR_PIXELS):
            model_output.open_new_ts_file( self, self.mr_ts_file, IDs,
                                           ## var_name='MR',
                                           var_name='mr',
                                           long_name='snow_meltrate',
                                           units_name='m/s')

        if (self.SAVE_HS_PIXELS):
            model_output.open_new_ts_file( self, self.hs_ts_file, IDs,
                                           ## var_name='h_snow',
                                           var_name='hs',
                                           long_name='snow_depth',
                                           units_name='m')

        if (self.SAVE_SW_PIXELS):
            model_output.open_new_ts_file( self, self.sw_ts_file, IDs,
                                           ## var_name='SWE',
                                           var_name='sw',
                                           long_name='snow_water_equivalent',
                                           units_name='m')
            
        if (self.SAVE_CC_PIXELS):
            model_output.open_new_ts_file( self, self.cc_ts_file, IDs,
                                           ## var_name='SCC',
                                           var_name='cc',
                                           long_name='snow_cold_content',
                                           units_name='J/m^2')
            
    #   open_output_files()
    #-------------------------------------------------------------------
    def write_output_files(self, time_seconds=None):

        #-----------------------------------------
        # Allows time to be passed from a caller
        #-----------------------------------------
        if (time_seconds is None):
            time_seconds = self.time_sec
        model_time = int(time_seconds)
        
        #----------------------------------------
        # Save computed values at sampled times
        #----------------------------------------
        if (model_time % int(self.save_grid_dt) == 0):
            self.save_grids()
        if (model_time % int(self.save_pixels_dt) == 0):
            self.save_pixel_values()

        #----------------------------------------
        # Save computed values at sampled times
        #----------------------------------------
##        if ((self.time_index % self.grid_save_step) == 0):
##             self.save_grids()
##        if ((self.time_index % self.pixel_save_step) == 0):
##             self.save_pixel_values()
        
    #   write_output_files()
    #-------------------------------------------------------------------
    def close_output_files(self):
    
        if (self.SAVE_MR_GRIDS): model_output.close_gs_file( self, 'mr')   
        if (self.SAVE_HS_GRIDS): model_output.close_gs_file( self, 'hs')   
        if (self.SAVE_SW_GRIDS): model_output.close_gs_file( self, 'sw')   
        if (self.SAVE_CC_GRIDS): model_output.close_gs_file( self, 'cc')
        #-----------------------------------------------------------------        
        if (self.SAVE_MR_PIXELS): model_output.close_ts_file( self, 'mr')  
        if (self.SAVE_HS_PIXELS): model_output.close_ts_file( self, 'hs')   
        if (self.SAVE_SW_PIXELS): model_output.close_ts_file( self, 'sw')   
        if (self.SAVE_CC_PIXELS): model_output.close_ts_file( self, 'cc')
        
    #-------------------------------------------------------------------  
    def save_grids(self):
     
        if (self.SAVE_MR_GRIDS):
            model_output.add_grid( self, self.SM, 'mr', self.time_min )
            
        if (self.SAVE_HS_GRIDS):
            model_output.add_grid( self, self.h_snow, 'hs', self.time_min )
            
        if (self.SAVE_SW_GRIDS):
            model_output.add_grid( self, self.h_swe, 'sw', self.time_min )

        if (self.SAVE_CC_GRIDS):
            model_output.add_grid( self, self.Ecc, 'cc', self.time_min )

    #   save_grids()     
    #-------------------------------------------------------------------  
    def save_pixel_values(self):

        IDs  = self.outlet_IDs
        time = self.time_min   ###
        
        if (self.SAVE_MR_PIXELS):
            model_output.add_values_at_IDs( self, time, self.SM, 'mr', IDs )
            
        if (self.SAVE_HS_PIXELS):
            model_output.add_values_at_IDs( self, time, self.h_snow, 'hs', IDs )
            
        if (self.SAVE_SW_PIXELS):
            model_output.add_values_at_IDs( self, time, self.h_swe, 'sw', IDs )
            
        if (self.SAVE_CC_PIXELS):
            model_output.add_values_at_IDs( self, time, self.Ecc, 'cc', IDs )

    #   save_pixel_values()
    #------------------------------------------------------------------- 
