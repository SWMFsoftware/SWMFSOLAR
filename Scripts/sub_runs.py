#!/usr/bin/env python3

import sys
import array
import change_param
import subprocess
import argparse

if __name__ == '__main__':

    PROG_DESCRIPTION = ('Script to submit jobs selected from a file.')
    ARG_PARSER = argparse.ArgumentParser(description=PROG_DESCRIPTION)
    ARG_PARSER.add_argument('-f', '--filename',
                            help='(default:event_list.txt)',
                            type=str, default='event_list.txt')
    ARG_PARSER.add_argument('-c', '--DoCompile',
                            help='(default: 1)'
                            + 'Use if you want to re-install and compile '
                            + 'the code.', 
                            type=int, default=1)
    ARGS = ARG_PARSER.parse_args()

    # the line number containing the selected run IDs, the index in
    # Python starts from 0...
    iSelectedID = 7-1

    # the line number where the ID and params start.
    iParamStart = 10-1

    # whether the code was compiled before
    IsAWSoMCompiled  = 0
    IsAWSoMRCompiled = 0

    with open(ARGS.filename, 'rt') as events:
        lines = list(events)

    # find the location of =
    iChar  = lines[iSelectedID].find('=')

    # any character after = is considered to be the string containing 
    # run IDs.
    StrRunIDs = lines[iSelectedID][iChar+1:]

    # split the string
    List_StrRunIDs = StrRunIDs.split(',')

    RunIDs = []

    # loop through List_StrRunIDs to get the list of run IDs in an integer list
    for StrRunID in List_StrRunIDs:
        try:
            # try to convert it to an integer
            RunID = int(StrRunID)
            RunIDs.append(RunID)
        except:
            # cannot convert to an integer as there is '-'
            ListTmp = StrRunID.split('-')
            try:
                RunIDs.extend([x for x in range(int(ListTmp[0]),
                                                int(ListTmp[1])+1)])
            except Exception as error:
                raise TypeError(error," wrong format: could only contain "
                                + "integer, ',' and '-'.")

    params_I =[]

    for iLine, line in enumerate(lines[iParamStart:]):
        if line.strip():
            param_now    = line.split()

            # the first element is always an inter representing the run ID.
            param_now[0] = int(param_now[0])
            params_I.append(param_now)

    for iID, params in enumerate(params_I):
        # if the run ID is found in the selected run ID.
        if params[0] in RunIDs:
            RunID = params[0]

            # reset all the default values
            MAP   = 'NoMap'
            PFSS  = 'HARMONICS'
            TIME  = 'MapTime'
            MODEL = 'AWSoM'

            NewParam = {}

            # the actual param starts from the 2nd element
            for param in params[1:]:
                paramTmp = param.split('=')
                if paramTmp[0].lower()   == 'map':
                    MAP  = paramTmp[1]
                    if 'adapt' in MAP.lower():
                        REALIZATIONS = [x for x in range(1,13)]
                        TypeMap      = 'ADAPT'
                    elif 'gong' in MAP.lower():
                        REALIZATIONS = [1]
                        TypeMap      = 'GONG'
                    else:
                        raise ValueError(MAP, ': unknown map type.')
                    ListStrRealizatinos = [str(iRealztion) 
                                           for iRealztion in REALIZATIONS]
                    StrRealizatinos = ",".join(ListStrRealizatinos)
                elif paramTmp[0].lower() == 'pfss':
                    PFSS = paramTmp[1]
                elif paramTmp[0].lower() == 'time':
                    TIME = paramTmp[1]
                elif paramTmp[0].lower() == 'model':
                    MODEL= paramTmp[1]
                else:
                    NewParam[paramTmp[0]] = paramTmp[1]

            strNewParam = ''
            for key in NewParam:
                strNewParam = strNewParam + '_' + key + '_' + NewParam[key]

            SIMDIR = ('run' + str(RunID).zfill(2) + '_' + MODEL + '_' + PFSS 
                      + '_' + MAP.replace('.fts','').replace('.fits','') 
                      + '_' + TIME + strNewParam)

            strMAP  ='MAP='+MAP
            strPFSS ='PFSS='+PFSS
            strTime ='TIME='+TIME
            strModel='MODEL='+MODEL

            strRealizations = 'REALIZATIONS='+StrRealizatinos

            strSIMDIR = 'SIMDIR='+SIMDIR

            # Compile the code if needed. AWSoM and AWSoM-R could not be 
            # selected at the same time
            if MODEL != 'AWSoM' and MODEL != 'AWSoMR':
                raise ValueError(MODEL, ': un-supported model.')

            if MODEL == 'AWSoM':
                if ARGS.DoCompile :
                    subprocess.call('make compile MODEL=AWSoM', shell=True)
                    ARGS.DoCompile = 0
                IsAWSoMCompiled = 1

            if MODEL == 'AWSoMR':
                if ARGS.DoCompile :
                    subprocess.call('make compile MODEL=AWSoMR', shell=True)
                    ARGS.DoCompile = 0
                IsAWSoMRCompiled = 1

            if IsAWSoMCompiled == 1 and IsAWSoMRCompiled == 1:
                raise ValueError(MODEL, ': AWSoM and AWSoMR cannot ' +
                                 'be selected at the same time.')

            # backup previous results if needed
            strbackup_run = 'make backup_run ' + strSIMDIR
            subprocess.call(strbackup_run, shell=True)

            # copy the PARAM.in, HARMONICS.in and FDIPS.in files
            strCopy_param = 'make copy_param ' + strModel
            subprocess.call(strCopy_param, shell=True)

            # change the PARAM.in file
            change_param.change_param_func(time=TIME, map=MAP, pfss=PFSS, 
                                           new_params=NewParam)
            
            # make run directories
            strRun_dir = ('make rundir_realizations ' + strSIMDIR + ' ' 
                          + strRealizations)
            subprocess.call(strRun_dir, shell=True)

            # clean the PARAM.in, HARMONICS.in, FDIPS.in and map_*.out files 
            # in the SWMFSOLAR folder
            subprocess.call('make clean_rundir_tmp', shell=True)

            # submit runs
            strRun = ('make run ' + strPFSS + ' ' + strSIMDIR + ' ' 
                      + strRealizations + ' JOBNAME=r'+str(RunID).zfill(2)+'_')
            subprocess.call(strRun, shell=True)