""" FIDUCEO FCDR harmonisation 
    Author:         Arta Dilo / NPL MM
    Date created:   09-01-2017
    Last update:    20-03-2017
    Version:        10.0
Functions for propagating uncertainty to the calibrated radiance:
- function to calculate first derivatives to measurement eq. variables,
    - and first derivatives to calibration coefficients;
- function for uncertainty propagation using GUM.
 """

from numpy import zeros, dot, einsum, diag, sqrt
from readHD import satSens, sInCoeff

class avhrr(object):
    ''' The class contains a function for the measurement equation and functions 
    for calculating sensitivity coefficients to variables and parameters in the 
    measurement equation. '''
    
    # Initialise avhrr class instance
    def __init__(self, folder, nclist):
        self.slabel = 'avhrr' # series label
        
        # extract number of sensor pairs from the list
        self.nopairs = len(nclist) # number of sensor pairs in the series
        print self.nopairs, 'pairs in filelist', nclist
        
        # extract the list of satellite sensors from filelist
        slist = satSens(nclist) 
        self.sslab = slist # satellite sensors labels
        
        # number of sensors in the list
        self.nosensors = len(slist) # number of sensors in the series
        print '\n', self.nosensors, 'sensors in', self.slabel, 'class'
        
        # index matrix with sensor pairs and no of matchups
        self.im = None # to fill after reading netCDF files
        
        # fill the known calibration coefficients 
        self.preHcoef = sInCoeff(folder, nclist) # dictionary with input cal.coeffs 
        print '\n\nInput calibration coefficients for sensors', self.sslab
        print self.preHcoef
        
        # set manually number of meas. eq. parameters; will change if needed
        self.novars = 5 # number of meas. eq. variables
        self.nocoefs = 4 # number of calibration coefficients
        
    # set index matrix of sensor pairs' matchups 
    def setIm(self, Im): 
        self.im = Im 
        return self.im    
    
    # AVHRR measurement equation    
    def measEq(self, X, a):
        # add checks for number of calib. coefficients and variables
        
        a0 = a[0] # AVHRR model coefficients
        a1 = a[1]
        a2 = a[2]
        a3 = a[3]    
        CE = X[:,2] # Earth counts
        Cs = X[:,0] # space counts 
        Cict = X[:,1] # ICT counts 
        Lict = X[:,3] # ICT radiance
        To = X[:,4] # orbit temperature
        
        # Earth radiance from Earth counts and calibration data
        LE = a0 + (0.98514+a1)*Lict*(Cs-CE)/(Cs-Cict) + a2*(Cict-CE)*(Cs-CE) 
        LE += a3*To
        
        return LE # return Earth radiance
        
    ''' Partial derivatives to measurement equation variables and coefficients; 
    these form the Jacobian row(s) for the LS in a pair sensor-reference. '''
    def sensCoeff(self, X, a):
        p = self.nocoefs # number of calibration coefficients
        m = self.novars # number of harmonisation variables

        a1 = a[1] # AVHRR model coefficients
        a2 = a[2]
        a3 = a[3]    
        CE = X[:,2] # Earth counts
        Cs = X[:,0] # space counts 
        Cict = X[:,1] # ICT counts 
        Lict = X[:,3] # ICT radiance
        To = X[:,4] # orbit temperature
        
        # initialize array of sensitivity coefficients per data row
        sens = zeros((CE.shape[0], p+m)) # should check it is 9
        
        # partial derivatives to calibration coefficients 
        sens[:,0] = 1.                             # dLE / da0
        sens[:,1] = Lict * (Cs - CE) / (Cs - Cict) # dLE / da1
        sens[:,2] = (Cict - CE) * (Cs - CE)         # dLE / da2
        sens[:,3] = To                             # dLE / da3
        
        # partial derivatives to meas.eq. variables
        sens[:,4] = (0.98514+a1)*Lict*(CE-Cict)/(Cs-Cict)**2 + a2*(Cict-CE) # dLE/dCs
        sens[:,5] = (0.98514+a1)*Lict*(Cs-CE)/(Cs-Cict)**2 + a2*(Cs-CE) # dLE/dCict
        sens[:,6] = (0.98514+a1)*Lict/(Cict-Cs) + a2*(2*CE-Cs-Cict) # dLE/dCE
        sens[:,7] = (0.98514+a1) * (Cs-CE) / (Cs-Cict)             # dLE/dLict
        sens[:,8] = a3                                             # dLE/dTo
        
        return sens 
        
    ''' Evaluate Earth radiance uncertainty from coefficients uncertainty '''
    def va2ULE(self, X, a, Va):
        p = self.nocoefs # number of calibration coefficients
        sens = self.sensCoeff(X, a) # sensitivity coeffs for matchup obs.
        
        # compute uncertainty from calibration coefficients
        u2La = dot(sens[:, 0:p]**2, diag(Va)) # coeffs. variance component
        corU = zeros((X[:,0].shape[0]))
        for i in range(p-1):
            for j in range(i+1,p):
                corU[:] += 2 * sens[:,i] * sens[:,j] * Va[i,j]
        u2La += corU # add coeffs' correlation component
        
        return sqrt(u2La) # return radiance uncert. from coeffs uncertainty

    ''' Calculate Earth radiance uncertainty via GUM law of propagation '''
    def uncLE(self, X, a, uX, Va):
        # assumes no correlation between X variables 
        
        p = self.nocoefs # number of calibration coefficients
        m = self.novars # number of harmonisation variables
        sens = self.sensCoeff(X, a) # sensitivity coeffs for matchup obs.

        # compute uncertainty from calibration coefficients
        u2La = dot(sens[:, 0:p]**2, diag(Va)) # coeffs. variance component
        corU = zeros((X[:,0].shape[0]))
        for i in range(p-1):
            for j in range(i+1,p):
                corU[:] += 2 * sens[:,i] * sens[:,j] * Va[i,j]
        u2La += corU # add coeffs' correlation component

        # compute uncertainty from harmonisation data variables
        u2LX = einsum('ij,ij->i', sens[:, p:p+m]**2, uX**2) 

        u2L = u2La + u2LX # total squared uncertainty of radiance 
        print "Ratio of coeffs' uncertainty component to total radiance uncertainty:"
        print min(sqrt(u2La/u2L)), '-', max(sqrt(u2La/u2L))
        
        return sqrt(u2L) # return uncertainty of Earth radiance        
