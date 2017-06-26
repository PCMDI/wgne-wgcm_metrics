"""
Calculate mode of varibility from archive of CMIP5 models

NAM: Northern Annular Mode
NAO: Northern Atlantic Oscillation
SAM: Southern Annular Mode
PNA: Pacific North American Pattern
PDO: Pacific Decadal Oscillation

Ji-Woo Lee
"""
from argparse import RawTextHelpFormatter
from shutil import copyfile 
import argparse
import cdms2 as cdms
import cdutil, cdtime
import genutil
import json
import pcmdi_metrics
import pdb
import string
import subprocess
import sys, os
import time
import MV2

# To avoid warning with NaN value for PDO case
#import warnings
#warnings.simplefilter(action = "ignore", category = RuntimeWarning)

libfiles = ['argparse_functions.py',
            'durolib.py',
            'get_pcmdi_data.py',
            'eof_analysis.py',
            'calc_stat.py',
            'landmask.py',
            'write_nc_output.py',
            'plot_map.py']

libfiles_share = ['default_regions.py']

for lib in libfiles:
  execfile(os.path.join('../lib/',lib))
  #execfile(os.path.join('../../lib/',lib))
  #execfile(os.path.join('./lib/',lib))

for lib in libfiles_share:
  #execfile(os.path.join('../../../../../share/',lib))
  execfile(os.path.join('../lib/',lib))
  #execfile(os.path.join('../../lib/',lib))
  #execfile(os.path.join('./lib/',lib))

##################################################
# Pre-defined options
#=================================================
mip = 'cmip5'
#exp = 'piControl'
exp = 'historical'
fq = 'mo'
realm = 'atm'

#=================================================
# Additional options
#=================================================
# Statistics against observation --
obs_compare = True
#obs_compare = False

# pseudo model PC time series analysis --
pseudo = True
#pseudo = False

# NetCDF output --
nc_out = True
#nc_out = False

# Plot figures --
plot = True
#plot = False

########################################################################
########################################################################
## Consistency test
########################################################################
########################################################################
#version = '0.0'
#version = '1.0'

#version = '2.0'
#version = '2.1'
#version = '2.2'

#version = '3.0'
version = '3.1'  ### Default 
#version = '3.2'
#version = '3.4'

DirCmp2NCAR = False
EofScaling = False
testCeline = False

#--------------------
if version == '0.0':

  DirCmp2NCAR = True

  OBS = 'HadSLP'
  OBS_SST = 'ERSSTv3b'

  osyear = 1920
  oeyear = 2015

  EofScaling = True

#--------------------
elif version == '1.0':

  DirCmp2NCAR = True

  OBS = 'HadSLP'
  OBS_SST = 'ERSSTv3b'

  osyear = 1920
  oeyear = 2015
  
#--------------------
elif version == '2.0':
  OBS = 'HadSLP'
  OBS_SST = 'ERSSTv3b'

elif version == '2.1':
  OBS = '20CR'
  OBS_SST = 'HadISST'

elif version == '2.2':
  OBS = 'ERAint'
  OBS_SST = 'HadISST'

  # For Non-PDOs...
  osyear = 1989
  oeyear = 2005

  # For PDO...
  osyear = 1979
  oeyear = 2012

#--------------------
elif version == '3.0':
  OBS = 'HadSLP'
  OBS_SST = 'ERSSTv3b'
  testCeline = True

  # For SAM...
  osyear = 1955
  oeyear = 2005

elif version == '3.1':
  OBS = '20CR'
  OBS_SST = 'HadISST'
  testCeline = True

  # For SAM...
  osyear = 1955
  oeyear = 2005

elif version == '3.2':
  OBS = 'ERAint'
  OBS_SST = 'HadISST'
  testCeline = True

  # For Non-PDOs...
  #osyear = 1989
  #oeyear = 2005

  # For PDO...
  osyear = 1979
  oeyear = 2012

elif version == '3.3':
  OBS = '20CR'
  OBS_SST = 'HadISST'
  testCeline = True

  osyear = 1979
  oeyear = 2005

elif version == '3.4':
  OBS = 'ERA20C'
  OBS_SST = 'ERA20C'
  testCeline = True

  # For SAM...
  osyear = 1955
  oeyear = 2005
#--------------------


########################################################################
########################################################################

#=================================================
# User defining options (argparse)
#=================================================
parser = argparse.ArgumentParser(description='Mode of variablility based on EOF analysis',
                                 formatter_class=RawTextHelpFormatter)
parser = AddParserArgument(parser)
args = parser.parse_args(sys.argv[1:])

# Check given model option ---
models = ModelCheck(args.model)
print 'models:', models

# Check given mode of variability option ---
mode = VariabilityModeCheck(args.variability_mode)
print 'mode:', mode

# Check dependency for given season option ---
seasons = SeasonCheck(args.season)
print 'seasons:', seasons

# Check dependency for given year ---
syear, eyear = YearCheck(args.year)
print 'syear, eyear: '+str(syear)+', '+str(eyear)

# Check dependency for realization ---
# (If multi_run == False then Considering only r1i1p1) ---
multi_run = RealizationCheck(args.realization)
print 'multi_run: ', multi_run

# EOF ordinal number ---
eofn_obs = args.eof_ordinal_number_for_observation
eofn_mod = args.eof_ordinal_number_for_model

# Basedir ---
basedir = args.basedir
print 'basedir: ', basedir
if mode == 'PDO':
  print 'PDO, user should give their land fraction information as well...'

# Output ---
out_dir = args.outdir
print 'outdir: ', out_dir

# Debug ---
debug = args.debug
print 'debug: ', debug
##if debug: pdb.set_trace()

##################################################

# Create output directory ---
out_dir = out_dir + '/' + mode
if not os.path.exists(out_dir): os.makedirs(out_dir)

# Multiple realization ---
if multi_run: 
  runs = '*'
else: 
  runs = 'r1i1p1'

if debug: print 'runs: ', runs

# Variables ---
if mode == 'NAM' or mode == 'NAO' or mode == 'SAM' or mode == 'PNA':
  var = 'psl'
elif mode == 'PDO':
  var = 'ts'

# Model list ---
if models == [ 'all' ]:
  models = get_all_mip_mods(mip,exp,fq,realm,var)

  if DirCmp2NCAR:
    flist = open('list_NCAR_models.txt','r')
    models = []
    for line in flist.readlines():
      models.append(line.strip())

  if debug: print models, len(models)

# lon1g and lon2g is for global map plotting ---
lon1g = -180
lon2g = 180

if mode == 'PDO':
  seasons = ['monthly']
  lon1g = 0
  lon2g = 360
  # Select models with land fraction available ---
  ###models_lf = get_all_mip_mods_lf(mip,'sftlf')
  ###models = list(set(models).intersection(models_lf)) # Select models when land fraction exists as well
  models = sorted(models, key=lambda s:s.lower()) # Sort list alphabetically, case-insensitive
  if debug: print 'Finally selected models: ', models

#=================================================
# Time period control
#-------------------------------------------------
start_time = cdtime.comptime(syear,1,1)
end_time = cdtime.comptime(eyear,12,31)

try:
  osyear
  oeyear
except NameError:
  # Variables were NOT defined
  start_time_obs = start_time
  end_time_obs = end_time
else:
  # Variables were defined."
  start_time_obs = cdtime.comptime(osyear,1,1)
  end_time_obs = cdtime.comptime(oeyear,12,31)
  
#=================================================
# Declare dictionary for .json record 
#-------------------------------------------------
var_mode_stat_dic={}

# Define output json file ---
json_filename = 'var_mode_'+mode+'_EOF'+str(eofn_mod)+'_stat_'+mip+'_'+exp+'_'+fq+'_'+realm+'_'+str(syear)+'-'+str(eyear)

json_file = out_dir + '/' + json_filename + '.json'
json_file_org = out_dir + '/' + json_filename + '_org_'+str(os.getpid())+'.json'

# Save pre-existing json file against overwriting ---
if os.path.isfile(json_file) and os.stat(json_file).st_size > 0 :
  copyfile(json_file, json_file_org)

  update_json = True

  if update_json == True:
    fj = open(json_file)
    var_mode_stat_dic = json.loads(fj.read())
    fj.close()

if 'REF' not in var_mode_stat_dic.keys():
  var_mode_stat_dic['REF']={}
if 'RESULTS' not in var_mode_stat_dic.keys():
  var_mode_stat_dic['RESULTS']={}

#=================================================
# Observation
#-------------------------------------------------
if obs_compare:

  # Load variable ---
  if var == 'psl':

    ## ERA interim
    if OBS == 'ERAint':
      obs_path = '/clim_obs/obs/atm/mo/psl/ERAINT/psl_ERAINT_198901-200911.nc'
      fo = cdms.open(obs_path)
      obs_timeseries = fo(var, time=(start_time_obs,end_time_obs), latitude=(-90,90))/100. # Pa to hPa
      obs_name = 'ERAint'

    ## HadSLP2r
    elif OBS == 'HadSLP':
      obs_path = '/work/lee1043/OBS/HadSLP2r/slp.mnmean.real.nc' 
      fo = cdms.open(obs_path)
      obs_timeseries = fo('slp', time=(start_time_obs,end_time_obs), latitude=(-90,90)) # mb = hPa
      obs_name = 'HadSLP2r'

    ## 20CR
    elif OBS == '20CR':
      obs_path = '/work/lee1043/DATA/reanalysis/20CR/slp_monthly_mean/monthly.prmsl.1871-2012.nc'
      fo = cdms.open(obs_path)
      obs_timeseries = fo('prmsl', time=(start_time_obs,end_time_obs), latitude=(-90,90))/100. # Pa to hPa
      obs_name = 'NOAA-CIRES_20CR'

    ## ERA 20C
    elif OBS == 'ERA20C':
      obs_path = '/work/lee1043/DATA/reanalysis/ERA20C/psl_ERA20C_190001-201012.nc'
      fo = cdms.open(obs_path)
      obs_timeseries = fo('msl', time=(start_time_obs,end_time_obs), latitude=(-90,90))/100. # Pa to hPa
      obs_name = 'ERA-20C'

  elif var == 'ts':

    ## HadISST
    if OBS_SST == 'HadISST':
      obs_path = '/clim_obs/obs/ocn/mo/tos/UKMETOFFICE-HadISST-v1-1/130122_HadISST_sst.nc'
      fo = cdms.open(obs_path)
      obs_timeseries = fo('sst', time=(start_time_obs,end_time_obs), latitude=(-90,90))
      obs_name = 'HadISSTv1.1'

    ## ERSST
    elif OBS_SST == 'ERSSTv3b':
      obs_path = '/work/lee1043/OBS/ERSSTv3b/sst.mnmean.v3.nc'
      fo = cdms.open(obs_path)
      obs_timeseries = fo('sst', time=(start_time_obs,end_time_obs), latitude=(-90,90))
      obs_name = 'ERSSTv3b'

    ## ERA 20C
    elif OBS == 'ERA20C':
      obs_path = '/work/lee1043/DATA/reanalysis/ERA20C/sst_ERA20C_190001-201012.nc'
      fo = cdms.open(obs_path)
      obs_timeseries = fo('sst', time=(start_time_obs,end_time_obs), latitude=(-90,90))-273.15 # K to C
      obs_name = 'ERA-20C'

    # Replace area where temperature below -1.8 C to -1.8 C ---
    obs_mask = obs_timeseries.mask
    obs_timeseries[obs_timeseries<-1.8] = -1.8
    obs_timeseries.mask = obs_mask

  cdutil.setTimeBoundsMonthly(obs_timeseries)

  # Check available time window and adjust if needed ---
  ostime = obs_timeseries.getTime().asComponentTime()[0]
  oetime = obs_timeseries.getTime().asComponentTime()[-1]

  osyear = ostime.year; osmonth = ostime.month
  oeyear = oetime.year; oemonth = oetime.month

  if osmonth > 1: osyear = osyear + 1
  if oemonth < 12: oeyear = oeyear - 1

  osyear = max(syear, osyear)
  oeyear = min(eyear, oeyear)

  if debug: print 'osyear:', osyear, 'oeyear:', oeyear

  # Save global grid information for regrid below ---
  ref_grid_global = obs_timeseries.getGrid()

  # Declare dictionary variables to keep information obtained from the observation ---
  eof_obs={}
  pc1_obs={}
  frac1_obs={}
  solver_obs={}
  reverse_sign_obs={}
  eof_lr_obs={}
  pc1_obs_stdv={}

  # Dictonary for json archive ---
  if 'obs' not in var_mode_stat_dic['REF'].keys(): 
    var_mode_stat_dic['REF']['obs']={}
  if 'defaultReference' not in var_mode_stat_dic['REF']['obs'].keys(): 
    var_mode_stat_dic['REF']['obs']['defaultReference']={}
  if 'source' not in var_mode_stat_dic['REF']['obs']['defaultReference'].keys():
    var_mode_stat_dic['REF']['obs']['defaultReference']['source'] = {}
  if mode not in var_mode_stat_dic['REF']['obs']['defaultReference'].keys():
    var_mode_stat_dic['REF']['obs']['defaultReference'][mode]={}

  var_mode_stat_dic['REF']['obs']['defaultReference']['source'] = obs_path
  var_mode_stat_dic['REF']['obs']['defaultReference']['reference_eof_mode'] = eofn_obs
  
  #-------------------------------------------------
  # Season loop
  #- - - - - - - - - - - - - - - - - - - - - - - - -
  obs_timeseries_season_subdomain = {}

  for season in seasons:

    if season not in var_mode_stat_dic['REF']['obs']['defaultReference'][mode].keys():
      var_mode_stat_dic['REF']['obs']['defaultReference'][mode][season]={}

    #- - - - - - - - - - - - - - - - - - - - - - - - -
    # Time series adjustment
    #. . . . . . . . . . . . . . . . . . . . . . . . .
    # Reomove annual cycle (for all modes) and get its seasonal mean time series (except PDO) ---
    obs_timeseries_ano = get_anomaly_timeseries(obs_timeseries, mode, season)

    # Calculate residual by subtracting domain average (or global mean) ---
    obs_timeseries_season = get_residual_timeseries(obs_timeseries_ano, mode)

    #- - - - - - - - - - - - - - - - - - - - - - - - -
    # Extract subdomain ---
    #. . . . . . . . . . . . . . . . . . . . . . . . .
    obs_timeseries_season_subdomain[season] = obs_timeseries_season(regions_specs[mode]['domain'])

    # EOF analysis ---
    eof_obs[season], pc1_obs[season], frac1_obs[season], solver_obs[season], reverse_sign_obs[season] = \
           eof_analysis_get_variance_mode(mode, obs_timeseries_season_subdomain[season], eofn_obs)

    # Calculate stdv of pc time series
    pc1_obs_stdv[season] = calcSTD(pc1_obs[season])

    # Linear regression to have extended global map; teleconnection purpose ---
    if testCeline:
      #slope_obs, intercept_obs = linear_regression(pc1_obs[season], obs_timeseries_ano)
      slope_obs, intercept_obs = linear_regression(pc1_obs[season], obs_timeseries_season)
      #eof_lr_obs[season] = linear_regression(pc1_obs[season], obs_timeseries_ano) * pc1_obs_stdv[season]
      eof_lr_obs[season] = ( slope_obs * pc1_obs_stdv[season] ) + intercept_obs
    else:
      slope_obs, intercept_obs = linear_regression(pc1_obs[season], obs_timeseries_season)
      if not EofScaling:
        #eof_lr_obs[season] = linear_regression(pc1_obs[season], obs_timeseries_season) * pc1_obs_stdv[season]
        eof_lr_obs[season] = ( slope_obs * pc1_obs_stdv[season] ) + intercept_obs
      else:
        #eof_lr_obs[season] = linear_regression(pc1_obs[season], obs_timeseries_season)
        eof_lr_obs[season] = slope_obs + intercept_obs

    #- - - - - - - - - - - - - - - - - - - - - - - - -
    # Record results 
    #. . . . . . . . . . . . . . . . . . . . . . . . .
    # Set output file name for NetCDF and plot ---
    output_filename_obs = out_dir + '/' + mode+'_'+var+'_EOF'+str(eofn_obs)+'_'+season+'_obs_'+str(osyear)+'-'+str(oeyear)

    # Save global map, pc timeseries, and fraction in NetCDF output ---
    if nc_out:
      write_nc_output(output_filename_obs, eof_lr_obs[season], pc1_obs[season], frac1_obs[season], slope_obs, intercept_obs)

    # Plotting ---
    if plot:
      #plot_map(mode, 'obs: '+obs_name, osyear, oeyear, season, eof_obs[season], frac1_obs[season], output_filename_obs+'_org')
      plot_map(mode, 'obs: '+obs_name, osyear, oeyear, season, 
               eof_lr_obs[season](regions_specs[mode]['domain']), frac1_obs[season], output_filename_obs)
      plot_map(mode+'_teleconnection', 'obs-lr: '+obs_name, osyear, oeyear, season, 
               eof_lr_obs[season](longitude=(lon1g,lon2g)), frac1_obs[season], output_filename_obs+'_teleconnection')

    # Save stdv of PC time series in dictionary ---
    var_mode_stat_dic['REF']['obs']['defaultReference'][mode][season]['pc1_stdv'] = float(pc1_obs_stdv[season])
    var_mode_stat_dic['REF']['obs']['defaultReference'][mode][season]['frac'] = float(frac1_obs[season])

    if debug: print 'obs plotting end'

    #execfile('../north_test.py')

#=================================================
# Model
#-------------------------------------------------
##if debug: pdb.set_trace()

for model in models:
  print ' ----- ', model,' ---------------------'

  if model not in var_mode_stat_dic['RESULTS'].keys():
    var_mode_stat_dic['RESULTS'][model]={}
  
  #model_path = get_latest_pcmdi_mip_data_path(mip,exp,model,fq,realm,var,run)
  #model_path = '/work/cmip5/historical/atm/mo/psl/cmip5.'+model+'.historical.r1i1p1.mo.atm.Amon.psl.ver-1.latestX.xml'
  model_path_list = get_latest_pcmdi_mip_data_path_as_list(mip,exp,model,fq,realm,var,runs)
  
  for model_path in model_path_list:

    try:
      run = string.split((string.split(model_path,'/')[-1]),'.')[3]
      print ' --- ', run,' ---'
  
      if run not in var_mode_stat_dic['RESULTS'][model].keys():
        var_mode_stat_dic['RESULTS'][model][run]={}
      if 'defaultReference' not in var_mode_stat_dic['RESULTS'][model][run].keys():
        var_mode_stat_dic['RESULTS'][model][run]['defaultReference']={}
      if mode not in var_mode_stat_dic['RESULTS'][model][run]['defaultReference'].keys():
        var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode]={}
  
      f = cdms.open(model_path)
    
      if var == 'psl':
        model_timeseries = f(var,time=(start_time,end_time),latitude=(-90,90))/100. # Pa to hPa
    
      elif var == 'ts':
        model_timeseries = f(var,time=(start_time,end_time),latitude=(-90,90))-273.15 # K to C degree
        model_timeseries.units = 'degC'
    
        # Replace area where temperature below -1.8 C to -1.8 C (sea ice) ---
        model_timeseries[model_timeseries<-1.8] = -1.8
  
      cdutil.setTimeBoundsMonthly(model_timeseries)

      # Check available time window and adjust if needed ---
      mstime = model_timeseries.getTime().asComponentTime()[0]
      metime = model_timeseries.getTime().asComponentTime()[-1]
    
      msyear = mstime.year; msmonth = mstime.month
      meyear = metime.year; memonth = metime.month
    
      ##if msmonth > 1: msyear = msyear + 1
      ##if memonth < 12: meyear = meyear - 1
      ####if memonth < 11: meyear = meyear - 1  ## HadGEM2-CC ends at Nov... 

      msyear = max(syear, msyear)
      meyear = min(eyear, meyear)

      if debug: print 'msyear:', msyear, 'meyear:', meyear
  
      #-------------------------------------------------
      # Season loop
      #- - - - - - - - - - - - - - - - - - - - - - - - -
      for season in seasons:

        if season not in var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode].keys():
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]={}
    
        #- - - - - - - - - - - - - - - - - - - - - - - - -
        # Time series adjustment
        #. . . . . . . . . . . . . . . . . . . . . . . . . 
        if mode == 'PDO':
          # Extract SST (land region mask out) ---
          model_timeseries = model_land_mask_out(mip,model,model_timeseries)

        # Reomove annual cycle (for all modes) and get its seasonal mean time series (except PDO) ---
        model_timeseries_ano = get_anomaly_timeseries(model_timeseries, mode, season)
  
        # Calculate residual by subtracting domain average (or global mean) ---
        model_timeseries_season = get_residual_timeseries(model_timeseries_ano, mode)
  
        #- - - - - - - - - - - - - - - - - - - - - - - - -
        # Extract subdomain ---
        #. . . . . . . . . . . . . . . . . . . . . . . . .
        model_timeseries_season_subdomain = model_timeseries_season(regions_specs[mode]['domain'])

        # Save subdomain's grid information for regrid (for pseudo2) below ---
        model_grid_subdomain = model_timeseries_season_subdomain.getGrid()

        #-------------------------------------------------
        # Usual EOF approach
        #- - - - - - - - - - - - - - - - - - - - - - - - -
        # EOF analysis ---
        eof, pc1, frac1, solver, reverse_sign = \
              eof_analysis_get_variance_mode(mode, model_timeseries_season_subdomain, eofn_mod)
        if debug: print 'eof analysis'
    
        # Calculate stdv of pc time series ---
        model_pcs_stdv = calcSTD(pc1)

        # Linear regression to have extended global map:
        # -- Reconstruct EOF fist mode including teleconnection purpose as well
        # -- Have confirmed that "eof_lr" is identical to "eof" over EOF domain (i.e., "subdomain")
        # -- Note that eof_lr has global field ---
        if testCeline:
          #slope, intercept = linear_regression(pc1, model_timeseries_ano)
          slope, intercept = linear_regression(pc1, model_timeseries_season)
          #eof_lr = linear_regression(pc1, model_timeseries_ano) * model_pcs_stdv
          eof_lr = ( slope * model_pcs_stdv ) + intercept
        else:
          slope, intercept = linear_regression(pc1, model_timeseries_season)
          if not EofScaling:
            #eof_lr = linear_regression(pc1, model_timeseries_season) * model_pcs_stdv
            eof_lr = ( slope * model_pcs_stdv ) + intercept
          else:
            #eof_lr = linear_regression(pc1, model_timeseries_season)
            eof_lr = slope + intercept
        if debug: print 'linear regression'

        # Add to dictionary for json output ---
        var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['frac'] = float(frac1)
        var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['std_model_pcs'] = float(model_pcs_stdv)
    
        #- - - - - - - - - - - - - - - - - - - - - - - - -
        # OBS statistics (only over EOF domain), save as dictionary ---
        #. . . . . . . . . . . . . . . . . . . . . . . . .
        if obs_compare:
    
          # Regrid (interpolation, model grid to ref grid) ---
          if debug: print 'regrid (global) start'
          eof_lr_regrid_global = eof_lr.regrid(ref_grid_global, regridTool='regrid2', mkCyclic=True)
          if debug: print 'regrid end'
    
          # Extract subdomain ---
          eof_regrid = eof_lr_regrid_global(regions_specs[mode]['domain'])

          # Spatial correlation weighted by area ('generate' option for weights) ---
          cor = calcSCOR(eof_regrid, eof_obs[season])
          cor_glo = calcSCOR(eof_lr_regrid_global, eof_lr_obs[season])
          if debug: print 'cor end'

          # Double check for arbitrary sign control --- 
          if cor < 0: 
            eof = eof * -1
            pc1 = pc1 * -1
            eof_lr = eof_lr * -1
            eof_lr_regrid_global = eof_lr_regrid_global * -1
            eof_regrid = eof_regrid * -1
            # Calc cor again ---
            cor = calcSCOR(eof_regrid, eof_obs[season])
            cor_glo = calcSCOR(eof_lr_regrid_global, eof_lr_obs[season])
    
          # RMS (uncentered) difference ---
          rms = calcRMS(eof_regrid, eof_obs[season])
          rms_glo = calcRMS(eof_lr_regrid_global, eof_lr_obs[season])
          if debug: print 'rms end'

          # RMS (centered) difference ---
          rmsc = calcRMSc(eof_regrid, eof_obs[season])
          rmsc_glo = calcRMSc(eof_lr_regrid_global, eof_lr_obs[season])
          if debug: print 'rmsc end'

          # Bias ---
          bias = calcBias(eof_regrid, eof_obs[season])
          bias_glo = calcBias(eof_lr_regrid_global, eof_lr_obs[season])
          if debug: print 'bias end'
    
          # Add to dictionary for json output ---
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rms'] = float(rms)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rms_glo'] = float(rms_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rmsc'] = float(rmsc)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rmsc_glo'] = float(rmsc_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['cor'] = float(cor)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['cor_glo'] = float(cor_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['bias'] = float(bias)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['bias_glo'] = float(bias_glo)
    
        #-------------------------------------------------
        # pseudo model PC timeseries and teleconnection 
        #- - - - - - - - - - - - - - - - - - - - - - - - -
        if debug: pdb.set_trace()

        if pseudo and obs_compare:
          # Regrid (interpolation, model grid to ref grid) ---
          #if testCeline:
          #  model_timeseries_ano_regrid = model_timeseries_ano.regrid(ref_grid_global, regridTool='regrid2', mkCyclic=True)
          model_timeseries_season_regrid = model_timeseries_season.regrid(ref_grid_global, regridTool='regrid2', mkCyclic=True)
          model_timeseries_season_regrid_subdomain = model_timeseries_season_regrid(regions_specs[mode]['domain'])
    
          # Matching model's missing value location to that of observation ---
          # 1) Replace model's masked grid to 0, so theoritically won't affect to result
          # 2) Give obs's mask to model field, so enable projecField functionality below 
          #missing_value = model_timeseries_season_regrid_subdomain.missing
          #model_timeseries_season_regrid_subdomain[ model_timeseries_season_regrid_subdomain == missing_value ] = 0
          #model_timeseries_season_regrid_subdomain.mask = model_timeseries_season_regrid_subdomain.mask + eof_obs[season].mask

          ##### Method 1... not working..  (above is working with only old UVCDAT version....)
          #missing_value = model_timeseries_season_regrid_subdomain.missing
          #model_timeseries_season_regrid_subdomain.mask = False
          #model_timeseries_season_regrid_subdomain.mask = model_timeseries_season_regrid_subdomain.mask + eof_obs[season].mask
          #model_timeseries_season_regrid_subdomain.mask = eof_obs[season].mask

          ##### Method 2... working!!..
          time = model_timeseries_season_regrid_subdomain.getTime()
          lat = model_timeseries_season_regrid_subdomain.getLatitude()
          lon = model_timeseries_season_regrid_subdomain.getLongitude()
          #
          model_timeseries_season_regrid_subdomain = MV2.array(model_timeseries_season_regrid_subdomain.filled(0.))
          model_timeseries_season_regrid_subdomain.mask = eof_obs[season].mask
          #
          model_timeseries_season_regrid_subdomain.setAxis(0,time)
          model_timeseries_season_regrid_subdomain.setAxis(1,lat)
          model_timeseries_season_regrid_subdomain.setAxis(2,lon)
    
          # Pseudo model PC time series ---
          pseudo_pcs = gain_pseudo_pcs(solver_obs[season], model_timeseries_season_regrid_subdomain, 1, reverse_sign_obs[season])
    
          # Calculate stdv of pc time series ---
          pseudo_pcs_stdv = calcSTD(pseudo_pcs)
    
          # Linear regression to have extended global map; teleconnection purpose ---
          if testCeline:
            #slope_pseudo, intercept_pseudo = linear_regression(pseudo_pcs, model_timeseries_ano_regrid)
            slope_pseudo, intercept_pseudo = linear_regression(pseudo_pcs, model_timeseries_season_regrid)
            #eof_lr_pseudo = linear_regression(pseudo_pcs, model_timeseries_ano_regrid) * pseudo_pcs_stdv
            eof_lr_pseudo = ( slope_pseudo * pseudo_pcs_stdv ) + intercept_pseudo
          else: 
            slope_pseudo, intercept_pseudo = linear_regression(pseudo_pcs, model_timeseries_season_regrid)
            if not EofScaling:
              #eof_lr_pseudo = linear_regression(pseudo_pcs, model_timeseries_season_regrid) * pseudo_pcs_stdv
              eof_lr_pseudo = ( slope_pseudo * pseudo_pcs_stdv ) + intercept_pseudo
            else:
              #eof_lr_pseudo = linear_regression(pseudo_pcs, model_timeseries_season_regrid)
              eof_lr_pseudo = slope_pseudo + intercept_pseudo

          # Extract subdomain for statistics ---
          eof_lr_pseudo_subdomain = eof_lr_pseudo(regions_specs[mode]['domain'])

          # Calculate variance franction of pseudo-pcs ---
          #pseudo_fraction = gain_pcs_fraction(model_timeseries_season_regrid_subdomain, eof_lr_pseudo_subdomain, pseudo_pcs)
          pseudo_fraction = gain_pcs_fraction(model_timeseries_season_regrid_subdomain, eof_lr_pseudo_subdomain, pseudo_pcs/pseudo_pcs_stdv)

          #- - - - - - - - - - - - - - - - - - - - - - - - -
          # OBS statistics (over global domain), save as dictionary, alternative approach -- pseudo PC analysis
          #. . . . . . . . . . . . . . . . . . . . . . . . .
          # Spatial correlation weighted by area ('generate' option for weights) ---
          cor_alt = calcSCOR(eof_lr_pseudo_subdomain, eof_obs[season])
          cor_alt_glo = calcSCOR(eof_lr_pseudo, eof_lr_obs[season])
          if debug: print 'pseudo cor end'

          # RMS (uncentered) difference ---
          rms_alt = calcRMS(eof_lr_pseudo_subdomain, eof_obs[season])
          rms_alt_glo = calcRMS(eof_lr_pseudo, eof_lr_obs[season])
          if debug: print 'pseudo rms end'
    
          # RMS (centered) difference ---
          rmsc_alt = calcRMSc(eof_lr_pseudo_subdomain, eof_obs[season])
          rmsc_alt_glo = calcRMSc(eof_lr_pseudo, eof_lr_obs[season])
          if debug: print 'pseudo rmsc end'

          # Temporal correlation between pseudo PC timeseries and usual model PC timeseries
          tc = calcTCOR(pseudo_pcs, pc1)
          if debug: print 'pseudo tc end'
    
          # Bias ---
          bias_alt = calcBias(eof_lr_pseudo_subdomain, eof_obs[season])
          bias_alt_glo = calcBias(eof_lr_pseudo, eof_lr_obs[season])
          if debug: print 'pseudo bias end'

          # Add to dictionary for json output ---
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rms_alt'] = float(rms_alt)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rms_alt_glo'] = float(rms_alt_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rmsc_alt'] = float(rmsc_alt)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['rmsc_alt_glo'] = float(rmsc_alt_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['cor_alt'] = float(cor_alt)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['cor_alt_glo'] = float(cor_alt_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['bias_alt'] = float(bias_alt)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['bias_alt_glo'] = float(bias_alt_glo)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['std_pseudo_pcs'] = float(pseudo_pcs_stdv)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['tcor_pseudo_vs_model_pcs'] = float(tc)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['frac_pseudo'] = float(pseudo_fraction)
    
          if debug: print 'pseudo pcs end'

          ######################################################
          # Pseudo2: 2016 Oct 10, following Ben's suggestion...
          ######################################################
          # Regrid (interpolation, obs to model grid) ---
          obs_timeseries_season_regrid_subdomain = obs_timeseries_season_subdomain[season].regrid(model_grid_subdomain, regridTool='regrid2')

          # Matching obs's missing value location to that of model ---
          # 1) Replace obs's masked grid to 0, so theoritically won't affect to result
          # 2) Give model's mask to obs field, so enable projecField functionality below 
          #missing_value = obs_timeseries_season_regrid_subdomain.missing
          #obs_timeseries_season_regrid_subdomain[ obs_timeseries_season_regrid_subdomain == missing_value ] = 0
          #obs_timeseries_season_regrid_subdomain.mask = obs_timeseries_season_regrid_subdomain.mask + eof.mask

          ##### Method 1... not working..  (above is working with only old UVCDAT version....)
          #missing_value = obs_timeseries_season_regrid_subdomain.missing
          #obs_timeseries_season_regrid_subdomain.mask = False
          #obs_timeseries_season_regrid_subdomain[ obs_timeseries_season_regrid_subdomain == missing_value ] = 0
          #obs_timeseries_season_regrid_subdomain.mask = eof.mask

          ##### Method 2... working!!..
          time = obs_timeseries_season_regrid_subdomain.getTime()
          lat = obs_timeseries_season_regrid_subdomain.getLatitude()
          lon = obs_timeseries_season_regrid_subdomain.getLongitude()
          #
          obs_timeseries_season_regrid_subdomain = MV2.array(obs_timeseries_season_regrid_subdomain.filled(0.))
          obs_timeseries_season_regrid_subdomain.mask = eof.mask
          #
          obs_timeseries_season_regrid_subdomain.setAxis(0,time)
          obs_timeseries_season_regrid_subdomain.setAxis(1,lat)
          obs_timeseries_season_regrid_subdomain.setAxis(2,lon)

          # Project model pattern onto observation space
          pseudo_pcs_on_obs_space = gain_pseudo_pcs(solver, obs_timeseries_season_regrid_subdomain, eofn_mod, reverse_sign)

          # Temporal correlation between pseudo PC timeseries and usual model PC timeseries
          tc2 = calcTCOR(pseudo_pcs_on_obs_space, pc1_obs[season])

          if tc2 < 0:
            pseudo_pcs_on_obs_space = pseudo_pcs_on_obs_space * -1.
            tc2 = calcTCOR(pseudo_pcs_on_obs_space, pc1_obs[season])

          # Calculate stdv of pc time series ---
          pseudo_pcs_on_obs_space_stdv = calcSTD(pseudo_pcs_on_obs_space)

          # Calculate variance franction of pseudo-pcs ---
          #pseudo2_fraction = gain_pcs_fraction(obs_timeseries_season_regrid_subdomain, eof_lr(regions_specs[mode]['domain']), pseudo_pcs_on_obs_space)
          pseudo2_fraction = gain_pcs_fraction(obs_timeseries_season_regrid_subdomain, eof_lr(regions_specs[mode]['domain']), pseudo_pcs_on_obs_space/pseudo_pcs_on_obs_space_stdv)

          if debug: print 'pseudo2 tc end'

          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['tcor_obs-pc1_vs_obs-pseudo_pcs'] = float(tc2)
          var_mode_stat_dic['RESULTS'][model][run]['defaultReference'][mode][season]['frac_pseudo2'] = float(pseudo2_fraction)
          ######################################################
    
        #-------------------------------------------------
        # Record results
        #- - - - - - - - - - - - - - - - - - - - - - - - -
        # Set output file name for NetCDF and plot ---
        output_filename = out_dir + '/' \
                         + mode+'_'+var+'_EOF'+str(eofn_mod)+'_'+season+'_' \
                         + mip+'_'+model+'_'+exp+'_'+run+'_'+fq+'_'+realm+'_'+str(msyear)+'-'+str(meyear)
    
        # Save global map, pc timeseries, and fraction in NetCDF output ---
        if nc_out:
          #write_nc_output(output_filename, eof_lr, pc1, frac1)
          write_nc_output(output_filename, eof_lr, pc1, frac1, slope, intercept)
          if pseudo and obs_compare: 
            #write_nc_output(output_filename+'_pseudo', eof_lr_pseudo, pseudo_pcs, pseudo_fraction)
            write_nc_output(output_filename+'_pseudo', eof_lr_pseudo, pseudo_pcs, pseudo_fraction, slope_pseudo, intercept_pseudo)
            #write_nc_output(output_filename+'_pseudo2', eof_lr_pseudo, pseudo_pcs_on_obs_space, pseudo2_fraction)
    
        # Plot map ---
        if plot:
          #plot_map(mode, model+'_'+run, msyear, meyear, season, eof, frac1, output_filename+'_org')
          plot_map(mode, model+' ('+run+')', msyear, meyear, season, 
                   eof_lr(regions_specs[mode]['domain']), frac1, output_filename)
          plot_map(mode+'_teleconnection', model+' ('+run+')', msyear, meyear, season, 
                   eof_lr(longitude=(lon1g,lon2g)), frac1, output_filename+'_teleconnection')
          if pseudo: 
            plot_map(mode, model+' ('+run+')'+' - pseudo', msyear, meyear, season, 
                     eof_lr_pseudo(regions_specs[mode]['domain']), pseudo_fraction, output_filename+'_pseudo')
            plot_map(mode+'_pseudo_teleconnection', model+' ('+run+')', msyear, meyear, season, 
                     eof_lr_pseudo(longitude=(lon1g,lon2g)), pseudo_fraction, output_filename+'_pseudo_teleconnection')
    
      #=================================================
      # Write dictionary to json file (let the json keep overwritten in model loop)
      #-------------------------------------------------
      if mode == 'PDO':
        new_json_structure = False
        #new_json_structure = True
      else:
        #new_json_structure = True
        new_json_structure = False

      if new_json_structure:
        JSON = pcmdi_metrics.io.base.Base(out_dir,json_filename)
        JSON.write(var_mode_stat_dic,json_structure=["model","realization","reference","mode","season","statistic"],
                   sort_keys=True, mode="w", indent=4, separators=(',', ': '))
      else:
        json.dump(var_mode_stat_dic, open(json_file,'w'), sort_keys=True, indent=4, separators=(',', ': '))

    except Exception, err:
      print 'faild for ', model, run, err
      pass


if not debug: sys.exit('done')
