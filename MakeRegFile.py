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

    params = {'MinimalPhenotypeFile':'/data/processed_data/minimal_phenotype/minimal_phenotype_2022-03-28.feather','SampleFile':'test_samplelist_100IDs.txt','FeatureFile':'selected_variables_v1.csv','CpiFile':'/data/original_data/etk_pension/consumer_price_index_1972_2021.csv','ByYear':'T','PensionFile':'/data/processed_data/etk_pension/elake_2022-05-10.feather','OutputAge':'T','OutputFile':'out_test_','IncomeFile':'/data/processed_data/etk_pension/vuansiot_2022-05-12.feather','BenefitsFile':'/data/processed_data/etk_pension/palkaton_2022-05-10.feather','SocialAssistanceFile':'/data/processed_data/thl_social_assistance/3214_FinRegistry_toitu_MattssonHannele07122020.csv.finreg_IDsp'}
    #ipython test lines end here
    
    #read in the samples and features to use in the output
    samples,features,data = getSamplesFeatures(params)
    requested_features = set(features['variable_name'])
    logging.info('Samples and features read in.')
    
    #read in the consumer price index table
    cpi = getCPI(params)

    #then reading in one data source at a time

    #########
    #PENSION#
    #########
    
    #This step can be skipped if no variables from pension registry are requested
    pension_set = set(['received_disability_pension','received_pension','total_income'])
    if len(requested_features.intersection(pension_set))>0:
        data = readPension(samples,data,params,cpi,requested_features)
        logging.info('Pension data read in.')
    else: logging.info('Pension data not read as no pension-related features were requested.')

    ########
    #INCOME#
    ########

    #Skipped if no variables needing income information are requested
    income_set = set(['total_income','received_labor_income'])
    if len(requested_features.intersection(income_set))>0:
        data = readIncome(samples,data,params,requested_features)
        logging.info('Income data read in.')
    else: logging.info('Income data not read as no income-related features were requested.')

    ##########
    #BENEFITS#
    ##########

    #Skipped if no variables needing income information are requested
    benefits_set = set(['received_unemployment_allowance','received_study_allowance',
                        'received_sickness_allowance','received_basic_unemployment_allowance',
                        'received_maternity_paternity_parental_allowance'])
    if len(requested_features.intersection(benefits_set))>0:
        data = readBenefits(samples,data,params,requested_features)
        logging.info('Benefits data read in.')
    else: logging.info('Benefits data not read as no benefits-related features were requested.')

    ###################
    #SOCIAL ASSISTANCE#
    ###################

    #Skipped if no variables needing income information are requested
    sa_set = set(['total_income','received_any_income_support'])
    if len(requested_features.intersection(sa_set))>0:
        data = readSocialAssistance(samples,data,params,cpi,requested_features)
        logging.info('Social assistance data read in.')
    else: logging.info('Social assistance data not read as no social assistance-related features were requested.')


    ########
    #OUTPUT#
    ########
    
    #save the output in the requested format
    #missing data ouput as '' (empty cells) to save space
    outname = params['OutputFile']+'-matrix.csv'
    data.to_csv(outname,sep=',',float_format='%.2f',index=False)
    logging.info('Final output matrix saved to: '+outname)

    
    
MakeRegFile()
