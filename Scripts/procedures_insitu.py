from ai import cdas
import pandas as pd
import datetime
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.dates as dates
from datetime import datetime
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']


class preprocess:
    def get_insitu_data(self,spacecraft,start_time,end_time,cache_dir):
        cdas.set_cache(True, cache_dir)
        if(spacecraft == 'earth'): 
            instr    = 'OMNI_COHO1HR_MERGED_MAG_PLASMA'
            var_list = ['ABS_B' , 'V', 'N','T']
            #download data from cdaw
            try:
                data=cdas.get_data('istp_public',instr,start_time,end_time,
                            var_list)
                #unify the keys to ['B','V','N','T']
                data['Epoch'] = data.pop('EPOCH_TIME')
                data['B'] = data.pop('FIELD_MAGNITUDE_AVG.')
                data['V'] = data.pop('BULK_FLOW_SPEED')
                data['N'] = data.pop('ION_DENSITY')
                data['T'] = data.pop('TEMPERATURE')
            except cdas.NoDataError:
                print('No Observation Data for '+spacecraft+'!!')
                data={}
                data['Epoch'] = np.array([np.nan])
                data['B'] = np.array([np.nan])
                data['V'] = np.array([np.nan])
                data['N'] = np.array([np.nan])
                data['T'] = np.array([np.nan])
                return data
        elif('st' in spacecraft):
            if(spacecraft == 'sta'): 
                instr    = 'STA_COHO1HR_MERGED_MAG_PLASMA'
            elif(spacecraft == 'stb'):
                instr    = 'STB_COHO1HR_MERGED_MAG_PLASMA'
            var_list = ['B','plasmaSpeed','plasmaDensity','plasmaTemp']
            #download data from cdaw
            try:
                data=cdas.get_data('istp_public',instr,start_time,end_time,
                            var_list)
                #unify the keys to ['B','V','N','T']
                data['Epoch'] = data.pop('EPOCH')
                data['V'] = data.pop('PLASMA_SPEED')
                data['N'] = data.pop('SW_PLASMA_DENS')
                data['T'] = data.pop('SW_PLASMA_TEMP')
            except cdas.NoDataError:
                print('No Observation Data for '+spacecraft+'!!')
                data={}
                data['Epoch'] = np.array([np.nan])
                data['B'] = np.array([np.nan])
                data['V'] = np.array([np.nan])
                data['N'] = np.array([np.nan])
                data['T'] = np.array([np.nan])
                return data
        else: 
            print('Invalid spacecraft!!')
            return -1
        #clean data
        for key in ['B','V','N','T']:
            data[key][data[key]<0.0]=np.nan

        return data
    def read_simu_data(self,filename):
        self.ProtonMass = 1.67e-24
        self.k          = 1.3807e-23
        #read in simulation file and calculate required quantities
        #read in csv file
        data=pd.read_csv(filename,skiprows=1,sep='\s+',
                         parse_dates={ 'date': ['year', 'mo', 'dy','hr','mn','sc','msc']})
        #parse date time
        data['date'] = pd.to_datetime(data['date'],format='%Y %m %d %H %M %S %f')
        #calculate ur, number density, ion/electron temperature,b magnitude
        #change to lower case
        data.columns= data.columns.str.lower()
        data['ur'] = (data['ux']*data['x']+data['uy']*data['y']+data['uz']*data['z']) \
                    /(data['x']**2.+data['y']**2.+data['z']**2.)**0.5
        data['ndens'] = data['rho']/self.ProtonMass
        data['ti']    = data['p']*self.ProtonMass/data['rho']/self.k*1E-7
        data['te']    = data['pe']*self.ProtonMass/data['rho']/self.k*1E-7
        data['bmag']  = (data['bx']**2.+data['by']**2.+data['bz']**2.\
			+4.0*np.pi*(data['i01']+data['i02']) )**0.5
        return data
    def get_icme_list(self,filename,start_time,end_time,spacecraft): 
        #read in ICME list
        data_icme=pd.read_csv(filename,parse_dates=[0,1])
        #decide sta or stb
        if(spacecraft == 'sta'): 
            data_icme = data_icme[data_icme['STEREO']==1]
        elif(spacecraft == 'stb'): 
            data_icme = data_icme[data_icme['STEREO']==-1]
        #select ICMEs that fall into the simulation time range
        icme_selected = (data_icme['start_time']>start_time) & \
                    (data_icme['end_time']<end_time)
        icme_start = data_icme['start_time'][icme_selected]
        icme_end   = data_icme['end_time'][icme_selected]
        
        return icme_start,icme_end
    def plot_data(self,dir_plot,data,omni_data,icme_start,icme_end,spacecraft,model): 
        mpl.rcParams['axes.linewidth'] = 0.5 #set the value globally

        simu_label = model
        obs_label  = spacecraft
        ylabels    = ['$\mathdefault{U_r}$ [km/s]','$\mathdefault{N_p}$ [cm$^{-3}$]',
                        'Temperature [k]','B [nT]']

        fig = plt.figure(figsize=(5,5))
        ux  = fig.add_subplot(4,1,1)
        dx  = fig.add_subplot(4,1,2,sharex=ux)
        tx  = fig.add_subplot(4,1,3,sharex=ux)
        bx  = fig.add_subplot(4,1,4,sharex=ux)

        #plot observations
        ux.plot(omni_data['Epoch'],omni_data['V'],color='k',label=obs_label)
        dx.plot(omni_data['Epoch'],omni_data['N'],color='k')
        tx.plot(omni_data['Epoch'],omni_data['T'],color='k')
        bx.plot(omni_data['Epoch'],omni_data['B'],color='k')


        #plot simulations
        ux.plot(data['date'],data['ur'],color='r',label=simu_label)
        dx.plot(data['date'],data['ndens'],color='r')
        tx.plot(data['date'],data['ti'],color='r')
        bx.plot(data['date'],data['bmag']*1E5,color='r')

        #plot ICMEs
        for i in range(icme_start.size): 
            for px in [ux,dx,tx,bx]: 
                px.axvspan(icme_start.iloc[i], icme_end.iloc[i],color='lightblue')

        #specify tick format
        fmt = lambda x, pos: '{:.1f}e5'.format(x*1e-5, pos)
        tx.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(fmt))

        #beautify the plots
        for px in [ux,dx,tx]: 
            px.tick_params(labelbottom=False)
        for pxi, px in enumerate([ux,dx,tx,bx]): 
            px.set_ylabel(ylabels[pxi],fontweight='bold',fontsize=14)
            px.set_xlim(data['date'].iloc[0],data['date'].iloc[-1])
            px.yaxis.set_ticks_position('both')

        bx.set_xlabel('Start Time ('+data['date'][0].strftime("%d-%b-%y %H:%M:%S")+')',fontsize=14,
			fontweight='bold')
        bx.xaxis.set_major_formatter(dates.DateFormatter('%d-%b'))
        bx.xaxis.set_major_locator(plt.MaxNLocator(8))

        #add legend to the first plot
        legend_prop={'weight':'bold'}
        ux.legend(frameon=False,loc=2,fontsize=14,prop=legend_prop)

        #save figure to png
        plt.subplots_adjust(left=0.15, bottom=0.09, right=0.98, top=0.98, wspace=None, hspace=0.1)
        plt.savefig(dir_plot+spacecraft+'_'+data['date'][0].strftime("%d-%b-%y")+'.png',dpi=300)
        plt.close()
