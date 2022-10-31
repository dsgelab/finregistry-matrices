import argparse
import logging

from helpers import readConfig,getSamplesFeatures

def MakeRegFile():

    ########################
    #command line arguments#
    ########################

    parser = argparse.ArgumentParser()

    #PARAMETERS
    parser.add_argument("--configfile",help="Full path to the configuration file.",type=str,default=None)
    parser.add_argument("--logfile",help="Full path to the log file.",type=str,default='./log.txt')
   
    args = parser.parse_args()

    #initialize logging file
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename=args.logfile,level=logging.INFO,filemode='w')
    logging.info("Configuration file path: "+args.configfile)
    
    #read in the config file and test that all provided files open
    isOk,params,msg = readConfig(args.configfile)

    if not isOk:
        logging.error(msg)
        print("Terminating, see the log file (path defined by args.logfile flag) for details.")
        exit
    else: logging.info("Config file successfully read in.")

    #read in the samples and features to use in the output
    samples,features = getSamplesFeatures(params)


    
    


MakeRegFile()
