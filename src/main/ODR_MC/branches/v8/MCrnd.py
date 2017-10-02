#!/usr/bin/env python

""" FIDUCEO FCDR harmonisation 
    Author:         Arta Dilo / NPL MM
    Date created:   24-01-2017
    Last update:    13-03-2017
    Version:        8.1
Evaluate ODR fit coefficients uncertainty via Monte Carlo (MC) trials. 
Work with a reference-sensor pair, use the same error structure with the weights 
in ODR, the combined random and systematic. Systematic effect is constant, 
set to average of all matchups, to be comparable with Peter & Sam's results. """

from numpy import empty, sqrt, savetxt, random
from datetime import datetime as dt
from os.path import join as pjoin
import readHD as rhd
import harFun as har
import unpFun as upf
import plotMCres as mcr


notime = True # work with (not-) time dependant simulation data
datadir = "D:\Projects\FIDUCEO\Data\Simulated" # root data folder
mcrdir = pjoin(datadir, 'Results') # folder for MC trials results
#pltdir = pjoin(datadir, 'Graphs') # folder for png images of graphs

filelist = ["m02_n19.nc","m02_n18.nc","m02_n17.nc","m02_n16.nc","m02_n15.nc"]
ncfile = filelist[4] # netCDF file to work with 

nop = len(filelist) # number of sensor pairs
slist = rhd.sensors(filelist) # list of sensors in filelist
nos = len(slist) # number of sensors
s2 = ncfile[4:7]
beta = [-10., -4.e-3, 1.e-5, 0.0] #  a3 value to fix to input
inCoef = rhd.sInCoeff(datadir, filelist) # dictionary with input cal. coeffs 
beta[3] = inCoef[s2][3] # set a3 to the input value
print '\nCalibrating sensor', s2, 'against the reference'
print '\nInput coefficients for', s2, ':', inCoef[s2]

if notime: # work with newSim_notime data
    
    # read data from the netCDF file
    newdir = pjoin(datadir, 'newSim_notime') # data folder
    rsp,Im,Hd,Hr,Hs,corIdx,corLen,csUr,cictUr = rhd.rHDpair(newdir, ncfile)
    
    podr = har.odrP(Hd, Hr, beta) # perform odr fit, weights from random uncert.
    
    fn = s2 + '_notd_mcrnd_beta.txt' # filename where MC coeffs will be stored

else: # work with data in the main data folder
    
    rsp,Im,Hd,Hr,Hs,corIdx,corLen,csUr,cictUr = rhd.rHDpair(datadir, ncfile)
    # set systematic uncertainties equivalent to Peter&Sam GN optimisation
    Hs = har.resetHs(Hs, rsp) 
    
    # perform odr fit 
    fixb = [1,1,1,0] # fix a3 coefficient
    podr = har.odrP(Hd, Hr, beta, fixb) # weights from random uncertainties
    
    fn = s2 + '_mcrnd_beta.txt' # filename for MC trials's coefficients 

print Im[0,2], 'matchup data from', ncfile, 'passed to harmonisation matrices'
print '\nODR results on Jon data, weights from random uncertainty'
podr.pprint()
bodr = podr.beta # odr fit coefficients
covodr = podr.cov_beta # odr evaluated covariance matrix

# ODR output for MC trials: best estimates of X and Y variables
Y = podr.y # best est.of adjusted reference radiance: Lref + K
X = podr.xplus # best est. of explanatory variables: Cs,Cict,CE,Lict,To
p = len(beta) # number of calib. coefficients

st = dt.now() # start of MC run

# MC runs ODR on new data: best estimate + full correlation error draw
sigma = sqrt(Hr**2)# + Hs**2) # standard uncertainty of X and Y vars
print '\nGenerate MC data with error distribution from input random uncertainty.'
notr = 1000 # number of MC trials
mcb = empty([notr, p+1]) # array to store beta vals and ODR info of MC trials

for i in range(notr):
    ''' Run notr MC trials '''
    
    # generate errors for MC trial and add to odr best estimates
    errStr = random.normal(loc=0.0, scale=sigma) # errors in MC trial i
    Xdt = X.T + errStr[:,1:6] # X variables for odr in the MC trial
    Ydt = Y + errStr[:,0] + errStr[:,6] # Y variable for odr 
    
    # run ODR on new X & Y vals with Hr (and Hs) weights 
    #mcodr = har.odr4MC(Xdt, Ydt, Hr, bodr, fixb, Hs)
    mcodr = har.odr4MC(Xdt, Ydt, Hr, bodr, fixb) # weights from random uncert.

    # store ODR fit coefficients and reason for halting
    mcb[i, 0:p] = mcodr.beta
    mcb[i,p] = mcodr.info

print '\nODR results from the last MC trial'
mcodr.pprint()

fn = pjoin(mcrdir, fn)
savetxt(fn, mcb, delimiter=',')

et = dt.now() # end of MC run
exect = (et-st).total_seconds()
print '\n--- Time taken for', notr, 'MC trials', (exect/60.), 'minutes ---'


""" == LOAD text file with calib. coeffs in MC trials and plot == """

avhrrNx = upf.avhrr(nop, nos) # instance of class avhrr series 
noMU = Im[0,2] # number of matchups

# graphs of ODR results on simulated data
nobj = 5000 # number of mathcup records to plot
mcr.plotSDfit(avhrrNx, noMU, nobj, s2, corIdx, Hr, podr, weight=1)


# heat maps for correlation of harmonisation coeffs from ODR and MC 
mcCov = mcr.mcCorr(fn, s2, bodr, covodr, 'MC with random error')

# graphs of radiance bias with 2sigma error bars
nobj = 200 # number of mathcups to plot
mcr.plotMCres(avhrrNx,noMU,nobj,inCoef[s2],s2,Hr,Hs,podr,mcCov,4)