import argparse
import logging

from helpers import readConfig,getSamplesFeatures,readMinimalPheno

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


    #The following lines are for testing the code in ipython
    logging.shutdown()
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='test_run_log.txt',level=logging.INFO,filemode='w')
    logging.info("Configuration file path: "+"test_ses_config")

    params = {'MinimalPhenotypeFile':'/data/processed_data/minimal_phenotype/minimal_phenotype_2022-03-28.feather','SampleFile':'test_samplelist_100IDs.txt','FeatureFile':'selected_variables_v1.csv','CpiFile':'/data/original_data/etk_pension/consumer_price_index_1972_2021.csv','ByYear':'T','PensionFile':'/data/processed_data/etk_pension/elake_2022-05-10.feather'}
    #read in the samples and features to use in the output
    samples,features,data = getSamplesFeatures(params)
    requested_features = set(features['variable_name'])
    logging.info('Samples and features read in.')
    
    #read in the consumer price index table
    cpi = getCPI(params)

    #then reading in one data source at a time
    #First read in the pension register data
    #This step can be skipped if no variables from pension registry are requested
    pension_set = set(['received_disability_pension','received_pension','total_income'])
    if len(requested_features.intersection(pension_set))>0:
        data = readPension(data,params,cpi,requested_features)
        logging.info('Pension data read in.')
    else: logging.info('Pension data not read as no pension-related features were requested.')
    
    


MakeRegFile()
