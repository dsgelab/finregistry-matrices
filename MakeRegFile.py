import argparse
import logging

from time import time
from helpers import readConfig,getSamplesFeatures,readMinimalPheno,readSocialAssistance,readBenefits,readIncome,readPension,getCPI,readMaritalStatus,readPedigree,readLiving,readSES,readEdu,readBirth,readLongterm,readEmigration

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
        return False
    else: logging.info("Config file successfully read in.")


    start = time()
    #The following lines are for testing the code in ipython
    #logging.shutdown()
    #logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='test_run_log.txt',level=logging.INFO,filemode='w')
    #logging.info("Configuration file path: "+"test_ses_config")

    #params = {'MinimalPhenotypeFile':'/data/processed_data/minimal_phenotype/minimal_phenotype_main_dec2022.csv','SampleFile':'/data/projects/dimensions_of_health/tmp/parents_ses_header_first_50.csv','FeatureFile':'selected_variables_v2.csv','CpiFile':'/data/original_data/etk_pension/consumer_price_index_1972_2021.csv','ByYear':'F','PensionFile':'/data/processed_data/etk_pension/elake_2022-05-10.feather','OutputAge':'F','OutputFile':'out_test_','IncomeFile':'/data/processed_data/etk_pension/vuansiot_2022-05-12.feather','BenefitsFile':'/data/processed_data/etk_pension/palkaton_2022-05-10.feather','SocialAssistanceFile':'/data/processed_data/thl_social_assistance/3214_FinRegistry_toitu_MattssonHannele07122020.csv.finreg_IDsp','MarriageHistoryFile':'/data/processed_data/dvv/Tulokset_1900-2010_tutkhenk_aviohist.txt.finreg_IDsp','PedigreeFile':'/data/processed_data/dvv/dvv_pedigree_withfamid.20220501.tsv','LivingExtendedFile':'/data/processed_data/dvv/dvv_living_extended/dvv_ext_core.csv'}
    #params['SESFile'] = '/data/processed_data/sf_socioeconomic/sose_u1442_a.csv.finreg_IDsp'
    #params['BirthFile'] = '/data/processed_data/thl_birth/birth_2022-03-08.feather'
    #params['EducationFile'] = '/data/processed_data/sf_socioeconomic/tutkinto_u1442_a.csv.finreg_IDsp'
    #params['SocialHilmoFile'] =	'/data/processed_data/thl_soshilmo/thl2019_1776_soshilmo.csv.finreg_IDsp'
    #params['RelativesFile'] = '/data/processed_data/dvv/Tulokset_1900-2010_tutkhenk_ja_sukulaiset.txt.finreg_IDsp'
    #params['SampleFile'] = '/data/projects/dimensions_of_health/tmp/test_samplelist_N=1000.csv'
    #ipython test lines end here
    
    #read in the samples and features to use in the output
    features,data,ID_set,data_ind_dict = getSamplesFeatures(params)
    requested_features = set(features['variable_name'])
    logging.info('Samples and features read in.')
    
    #read in the consumer price index table
    cpi = getCPI(params)

    #then reading in one data source at a time

    #########
    #PENSION#
    #########
    
    #This step can be skipped if no variables from pension registry are requested
    pension_set = set(['received_disability_pension','received_pension','total_income','total_pension'])
    if len(requested_features.intersection(pension_set))>0:
        data = readPension(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Pension data read in.')
    else: logging.info('Pension data not read as no pension-related features were requested.')

    ########
    #INCOME#
    ########

    #Skipped if no variables needing income information are requested
    income_set = set(['total_income','received_labor_income','total_labor_income'])
    if len(requested_features.intersection(income_set))>0:
        data = readIncome(data,params,requested_features,ID_set,data_ind_dict)
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
        data = readBenefits(data,params,requested_features,ID_set,data_ind_dict)
        logging.info('Benefits data read in.')
    else: logging.info('Benefits data not read as no benefits-related features were requested.')

    ###################
    #SOCIAL ASSISTANCE#
    ###################

    #Skipped if no variables needing income information are requested
    sa_set = set(['total_income','received_any_income_support','total_benefits'])
    if len(requested_features.intersection(sa_set))>0:
        data = readSocialAssistance(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Social assistance data read in.')
    else: logging.info('Social assistance data not read as no social assistance-related features were requested.')

    ############
    #EMIGRATION#
    ############

    #Skipped if emigration variable is not requested
    emi_set = set(['emigrated'])
    if len(requested_features.intersection(emi_set))>0:
        data = readEmigration(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Emigration data read in.')
    else: logging.info('Emigration data not read as emigration variable was not requested.')

    ##################
    #MARRIAGE HISTORY#
    ##################

    #Skipped if no variables needing marital status information are requested
    ms_set = set(['divorced','married'])
    if len(requested_features.intersection(ms_set))>0:
        data = readMaritalStatus(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Marital status data read in.')
    else: logging.info('Marital status data not read as no marital status-related features were requested.')

    ##########
    #CHILDREN#
    ##########

    #Skipped if no variables needing information about children are requested
    ch_set = set(['children'])
    if len(requested_features.intersection(ch_set))>0:
        data = readPedigree(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Pedigree read in.')
    else: logging.info('Pedigree not read as no pedigree-related features were requested.')

    ####################
    #PLACE OF RESIDENCE#
    ####################

    #Skipped if no variables needing information about place of residence are requested
    ch_set = set(['zip_code','urbanization_class','urban_rural_class_code','sparse_small_house_area','apartment_building_area','small_house_area','demographic_dependency_ratio','economic_dependency_ratio','general_at_risk_of_poverty_rate_for_the_municipality','intermunicipal_net_migration_1000_inhabitants','sale_of_alcoholic_beverages_per_capita','self_rated_health_moderate_or_poor_scaled_health_and_welfare_indicator','average_income_of_inhabitants','median_income_of_inhabitants','permanent_residents_fraction'])
    if len(requested_features.intersection(ch_set))>0:
        data = readLiving(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Place of residence data read in.')
    else: logging.info('Place of residence data not read as no place of residence-related features were requested.')

    ######################
    #SOCIOECONOMIC STATUS#
    ######################

    #Skipped if no variables needing information about socioeconomic status are requested
    ses_set = set(['ses_self_employed','ses_upperlevel','ses_lowerlevel','ses_manual_workers','ses_students','ses_pensioners','ses_others','ses_unknown','ses_missing'])
    if len(requested_features.intersection(ses_set))>0:
        data = readSES(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Socioeconomic status data read in.')
    else: logging.info('Socioeconomic data not read as no socioeconomic features were requested.')


    ###########
    #EDUCATION#
    ###########

    #Skipped if no variables needing information about education are requested
    edu_set = set(['edu_years','edu_ongoing','edufield_generic','edufield_education','edufield_artshum','edufield_socialsciences','edufield_businessadminlaw','edufield_science_math_stat','edufield_ict','edufield_engineering','edufield_agriculture','edufield_health','edufield_services','edufield_NA'])
    if len(requested_features.intersection(edu_set))>0:
        data = readEdu(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Education data read in.')
    else: logging.info('Education data not read as no education-related features were requested.')

    #######
    #BIRTH#
    #######

    #Skipped if no variables needing information about birth and pregnancy are requested
    birth_set = set(['miscarriages','terminated_pregnancies','ectopic_pregnancies','stillborns','no_smoking_during_pregnancy','quit_smoking_during_1st_trimester','smoked_after_1st_trimester','smoking_during_pregnancy_NA','invitro_fertilization','thrombosis_prophylaxis','anemia','glucose_test_abnormal','no_analgesics','analgesics_info_missing','initiated_labor','promoted_labor','puncture','oxytocin','prostaglandin','extraction_of_placenta','uterine_scraping','suturing','prophylaxis','mother_antibiotics','blood_transfusion','circumcision','hysterectomy','embolisation','vaginal_delivery','vaginal_delivery_breech','forceps_delivery','vacuum_delivery','planned_c_section','urgent_c_section','emergency_c_section','not_planned_c_section','mode_of_delivery_NA','placenta_praevia','ablatio_placentae','eclampsia','shoulder_dystocia','asphyxia','live_born','stillborn_before_delivery','stillborn_during_delivery','stillborn_unknown','birth_status_NA'])
    if len(requested_features.intersection(birth_set))>0:
        data = readBirth(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Birth data read in.')
    else: logging.info('Birth data not read as no birth/pregnancy-related features were requested.')

    ################
    #LONG-TERM CARE#
    ################

    #Skipped if no variables needing information about long-term care are requested
    ltc_set = set(['care_in_elderly_home','assisted_living_elderly','institutional_care_demented','enhanced_care_demented','institutionalized_intellectual_disability','assisted_intellectual_disability','instructed_intellectual_disability','supported_intellectual_disability','services_fos_substance_abusers','rehabilitation','residential_care_housing','psychiatric_residential_care_housing','247_residential_care_housing_under_65yo','247_psychiatric_residential_care','unknown_long_term_care','mr_physical_reasons','mr_insufficient_self_care','mr_deficient_locomotion','mr_nervous_system','mr_forgetfullness','mr_mental_confusion','mr_deficiencies_in_communication','mr_dementia','mr_psychic_social_reasons','mr_depression','mr_other_psychatric','mr_loneliness_insecurity','mr_difficulties_with_housing','mr_lack_of_help_from_family','mr_caretaker_vacation','mr_lack_of_services','mr_lack_of_place_of_care','mr_rehabilitation','mr_med_rehabilitation','mr_accident','mr_somatic','mr_alcohol_use','mr_drug_use','mr_med_abuse','mr_polysubstance_abuse','mr_other_addiction','mr_substance_use_family','mr_NA','long_term_care_decision','long_term_care_duration'])
    if len(requested_features.intersection(ltc_set))>0:
        data = readLongterm(data,params,cpi,requested_features,ID_set,data_ind_dict)
        logging.info('Long-term care data read in.')
    else: logging.info('Long-term care data not read as no long-term care-related features were requested.')
    
    
    ########
    #OUTPUT#
    ########
    
    #save the output in the requested format
    #missing data ouput as '' (empty cells) to save space
    outname = params['OutputFile']+'-matrix.csv'
    data.to_csv(outname,sep=',',float_format='%.2f',index=False)
    logging.info('Final output matrix saved to: '+outname)
    end = time()
    print("Total running time = "+str(end-start)+" s")
    logging.info("Total running time = "+str(end-start)+" s")

    
    
MakeRegFile()
