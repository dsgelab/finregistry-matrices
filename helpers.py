import csv

import numpy as np
import pandas as pd

from datetime import datetime
from datetime import date
from time import time
from collections import Counter

def readConfig(filepath):
    #Reads in the configuration file.
    #Checks that files provided can be opened.
    #If some files cannot be opened, returns isOk = False
    #which halts excecution of MakeRegFile.

    #test opening the configfile
    error,msg = testFileOpens(filepath)
    if error: return False,{},msg
    
    #read in the parameters and test that each provided file opens
    with open(filepath,'rt') as infile:
        r = csv.reader(infile,delimiter='\t')
        params = {}
        for row in r:
            key = row[0]
            value = row[1]
            if key.count('File')>0:
                #test that file opens
                mode = 'r'
                if key.count('OutputFile')>0: mode = 'w'
                error,msg = testFileOpens(value,mode)
                if error: return False,{},msg
                
            params[key] = value
    
    return True,params,""

def getSamplesFeatures(params):
    #Read in the IDs of samples and variables to use in the output
    #return initialized output dataframe
    start = time()
    samples = pd.read_csv(params['SampleFile'])
    ID_set = set(list(samples['FINREGISTRYID']))
    #convert the date columns to datetime
    samples['start_of_followup'] = pd.to_datetime(samples['start_of_followup'])
    samples['end_of_followup'] = pd.to_datetime(samples['end_of_followup'])
    samples['date_of_birth'] = pd.to_datetime(samples['date_of_birth'])
    #Read in sex from minimal phenotype file
    mpfpath = params['MinimalPhenotypeFile']
    usecols = ['FINREGISTRYID','sex','mother_tongue']
    if mpfpath.count('.feather')>0: mpf = pd.read_feather(mpfpath,columns=usecols)
    else: mpf = pd.read_csv(mpfpath,usecols=usecols)
    mpf = mpf[mpf['FINREGISTRYID'].isin(ID_set)]
    #one-hot encode mother tongues
    mpf = pd.get_dummies(mpf,columns=['mother_tongue'])

    #rename mother tongue columns
    mpf.rename(columns={'mother_tongue_fi':'mothertongue_fi','mother_tongue_sv':'mothertongue_swe','mother_tongue_ru':'mothertongue_rus','mother_tongue_other':'mothertongue_other'},inplace=True)
    #mpf['sex'] = mpf['sex'].astype('int') #This does not work for missing values...
    #samples =  samples.merge(mpf[['FINREGISTRYID','sex']],how='left',on='FINREGISTRYID')

    if params['ByYear']=='F':
        data =  samples.merge(mpf,how='left',on='FINREGISTRYID')
        samples =  samples.merge(mpf[['FINREGISTRYID','sex']],how='left',on='FINREGISTRYID')
        data_ind_dict = {} #key = ID, value = [list of indices for this ID]
        for index,row in data.iterrows():
            ID = row['FINREGISTRYID']
            if ID not in data_ind_dict: data_ind_dict[ID] = [index]
            else: data_ind_dict[ID].append(index)
            
    elif params['ByYear']=='T':
        samples =  samples.merge(mpf[['FINREGISTRYID','sex']],how='left',on='FINREGISTRYID')
        #mother tongues are not repeated for every year
        data_ind_dict = {} #key = (FINREGISTRYID,year), value = [list of indices for this ID]
        samples_ind_dict = {} #key = (FINREGISTRYID,start_of_followup,end_of_followup)
        data = pd.DataFrame()
        IDs = []
        years = []
        sexs = []
        dobs = []
        starts = []
        ends = []
        #create one entry row per each year of follow-up for each individual
        ind = 0
        for index,row in samples.iterrows():
            start_year = row['start_of_followup'].year
            end_year = row['end_of_followup'].year
            samples_ind_dict[(row['FINREGISTRYID'],row['start_of_followup'],row['end_of_followup'])] = index
            for year in range(start_year,end_year+1):
                IDs.append(row['FINREGISTRYID'])
                dobs.append(row['date_of_birth'])
                sexs.append(row['sex'])
                starts.append(row['start_of_followup'])
                ends.append(row['end_of_followup'])
                years.append(year)
                key = (row['FINREGISTRYID'],year)
                if key not in data_ind_dict: data_ind_dict[key] = [ind]
                else: data_ind_dict[key].append(ind)
                ind += 1
        data['FINREGISTRYID'] = IDs
        data['year'] = years
        data['date_of_birth'] = dobs
        data['sex'] = sexs
        data['start_of_followup'] = starts
        data['end_of_followup'] = ends

    #create a dictionary mapping the ID+year pairs to indices of dataframe data
    features = pd.read_csv(params['FeatureFile'])
    if params['ByYear']=='F':
        #keys = [(row['FINREGISTRYID'],row['start_of_followup'],row['end_of_followup']) for index,row in data.iterrows()]
        #data_ind_dict = dict(zip(keys,list(data.index)))
        #samples_ind_dict = dict(zip(list(samples['FINREGISTRYID']),list(samples.index)))
        #key = (FINREGISTRYID,start_of_followup,end_of_followup)
        #value = corresponding index in dataframe data
        end = time()
        print("Data structures initialized in "+str(end-start)+" s")
        return features,data,ID_set,data_ind_dict
    elif params['ByYear']=='T':
        #samples_ind_dict = dict(zip(list(samples['FINREGISTRYID']),list(samples.index)))
        end = time()
        print("Data structures initialized in "+str(end-start)+" s")
        return features,data,ID_set,data_ind_dict
    
def getCPI(params):
    #Read in the consumer price index correction table
    with open(params['CpiFile'],'rt') as infile:
        r = csv.reader(infile,delimiter=',')
        cpi = {}
        for row in r:
            if row[0].count('year')>0: continue
            cpi[int(row[0])] = float(row[1])
    return cpi
    
def testFileOpens(filepath,mode='r'):

    error = False
    msg = ""
    try:
        f = open(filepath,mode)
        f.close()
    except OSError as e:
        error = True
        msg = e
    return error,msg

def getOnsetAge(dob,doo):
    #returns age of onset in decimal years
    #dob = date of birth (datetime)
    #doo = date of onset (datetime)
    diff = doo-dob
    return diff.days/365.0

def readMinimalPheno(params,data):
    #Read in sex from minimal phenotype file
    mpf = pd.read_feather(params['MinimalPhenotypeFile'],columns=['FINREGISTRYID','sex'])
    if params['ByYear']=='F': return data.merge(mpf,how='left',on='FINREGISTRYID')
    elif params['ByYear']=='T':
        sexs = []
        for index,row in data.iterrows():
            ID = row['FINREGISTRYID']
            sexs.append(mpf.loc[mpf['FINREGISTRYID']==ID]['sex'])
        data['sex'] = sexs
        return data

def readPension(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the pension registry
    #this function currently creates four variables, which are:
    #received_disability_pension = Received disability pension
    #received_pension = Received any pension
    #total_pension = Sum of pensions, indexed
    #total_income = Sum of labor income, pension and social benefits, indexed
    start = time()
    keep_cols = ['id','apvm','ppvm','ptma','ltma','jkma','tksyy1']
    pension = pd.read_feather(params['PensionFile'],columns=keep_cols)
    #keep only rows corresponding to IDs in samples
    pension = pension[pension['id'].isin(ID_set)]
    print("Pension, number or data rows: "+str(len(pension)))
    #convert date strings to datetime
    pension['apvm'] = pd.to_datetime(pension['apvm'])
    pension['ppvm'] = pd.to_datetime(pension['ppvm'])

    received_disability_pension = [0 for i in range(len(data))]
    received_pension = [0 for i in range(len(data))]
    #Note that since pension is read in first, total_income and total_pension
    #are identical at this point, so the same array can be just copied as the
    #total_pension column at the end
    total_income = [0.0 for i in range(len(data))]

    if params['OutputAge']=='T':
        received_disability_pension_OnsetAge = [np.nan for i in range(len(data))]
        received_pension_OnsetAge = [np.nan for i in range(len(data))]
        total_income_OnsetAge = [np.nan for i in range(len(data))]

    for p_indx,p_row in pension.iterrows():
        #First read in data for all years covered by the entry
        #then determine which rows of the dataframe data need to be updated
        #This means different approaches for byYear=T/F
        ID = p_row['id']
        if params['ByYear']=='T':
            p_start = p_row['apvm']
            p_end = p_row['ppvm']
            #if p_end is NaT, it means the pension is ongoing
            if pd.isnull(p_end): p_end = date.today()
            #get the list of years covered by this entry
            #print(p_row)
            years = [a for a in range(int(p_start.year),int(p_end.year)+1)]
            for year in years:
                key = (ID,year)
                #check if this ID+year combo is requested
                if key not in data_ind_dict: continue
                for ind in data_ind_dict[key]:
                    #correct for start and end years not necessarily being full years
                    nmonths = 12
                    if year==p_start.year: nmonths = 13-p_start.month
                    if year==p_end.year: nmonths = p_end.month

                    received_pension[ind] = 1#ID has received any pension
                    if not pd.isna(p_row['tksyy1']): received_disability_pension[ind] = 1 #ID has received disability pension

                    #if year is earlier than the earliest entry in the cpi table, use then index for year 1972
                    if year not in cpi: C = cpi[1972]
                    else: C = cpi[year]
            
                    if not pd.isna(p_row['ptma']): total_income[ind] += C*nmonths*p_row['ptma']
                    if not pd.isna(p_row['ltma']): total_income[ind] += C*nmonths*p_row['ltma']
                    if not pd.isna(p_row['jkma']): total_income[ind] += C*nmonths*p_row['jkma']

                    if params['OutputAge']=='T':
                        dob = data.iloc[ind]['date_of_birth']
                        if year==p_start.year: onset_date = p_start
                        else: onset_date = datetime(year,1,1)
                        OnsetAge = getOnsetAge(dob,onset_date)
                        #pension onset age/income onset age/disability pension onset age,
                        #these are the same as this is the first data source to read in
                        if np.isnan(received_pension_OnsetAge[ind]):
                            received_pension_OnsetAge[ind] = OnsetAge
                            total_income_OnsetAge[ind] = OnsetAge
                            if received_disability_pension[ind]: received_disability_pension_OnsetAge[ind] = OnsetAge
                            elif received_pension_OnsetAge[ind]>OnsetAge:
                                received_pension_OnsetAge[ind] = OnsetAge
                                total_income_OnsetAge[ind] = OnsetAge
                                if received_disability_pension[ind]: received_disability_pension_OnsetAge[ind] = OnsetAge
            
        elif params['ByYear']=='F':
            key = ID
            for ind in data_ind_dict[key]:
                fu_end = data.iloc[ind]['end_of_followup']
                fu_start = data.iloc[ind]['start_of_followup']
                dob = data.iloc[ind]['date_of_birth']

                p_start = p_row['apvm']
                p_end = p_row['ppvm']
                if pd.isna(p_end): p_end = fu_end
                    
                if p_end<fu_start or p_start>fu_end: continue
                if p_start<fu_start: p_start = fu_start
                if p_end>fu_end: p_end = fu_end
        
                #add up the pension from range p_start -> p_end
                #corrected with the consumer price index
                for year in range(p_start.year,p_end.year+1):
                    #correct for start and end years not necessarily being full years
                    nmonths = 12
                    if year==p_start.year: nmonths = 13-p_start.month
                    if year==p_end.year: nmonths = p_end.month

                    #get corresponding index in the dataframe data
                    #if params['ByYear']=='T': ind = data_ind_dict[(ID,fu_start,fu_end,year)]
                    #elif params['ByYear']=='F': ind = data_ind_dict[(ID,fu_start,fu_end)]

                    received_pension[ind] = 1#ID has received any pension
                    if not pd.isna(p_row['tksyy1']): received_disability_pension[ind] = 1 #ID has received disability pension

                    #if year is earlier than the earliest entry in the cpi table, use then index for year 1972
                    if year not in cpi: C = cpi[1972]
                    else: C = cpi[year]
            
                    if not pd.isna(p_row['ptma']): total_income[ind] += C*nmonths*p_row['ptma']
                    if not pd.isna(p_row['ltma']): total_income[ind] += C*nmonths*p_row['ltma']
                    if not pd.isna(p_row['jkma']): total_income[ind] += C*nmonths*p_row['jkma']

                    if params['OutputAge']=='T':
                        if year==p_start.year: onset_date = p_start
                        else: onset_date = datetime(year,1,1)
                        OnsetAge = getOnsetAge(dob,onset_date)
                        #pension onset age/income onset age/disability pension onset age,
                        #these are the same as this is the first data source to read in
                        if np.isnan(received_pension_OnsetAge[ind]):
                            received_pension_OnsetAge[ind] = OnsetAge
                            total_income_OnsetAge[ind] = OnsetAge
                            if received_disability_pension[ind]: received_disability_pension_OnsetAge[ind] = OnsetAge
                            elif received_pension_OnsetAge[ind]>OnsetAge:
                                received_pension_OnsetAge[ind] = OnsetAge
                                total_income_OnsetAge[ind] = OnsetAge
                                if received_disability_pension[ind]: received_disability_pension_OnsetAge[ind] = OnsetAge
    #add the new columns to dataframe data
    if 'total_income' in requested_features:
        data['total_income'] = total_income
        if params['OutputAge']=='T': data['total_income_OnsetAge'] = total_income_OnsetAge
    if 'total_pension' in requested_features:
        data['total_pension'] = data.loc[:,'total_income']
        if params['OutputAge']=='T': data['total_pension_OnsetAge'] = data.loc[:,'total_income_OnsetAge']
    if 'received_pension' in requested_features:
        data['received_pension'] = received_pension
        if params['OutputAge']=='T': data['received_pension_OnsetAge'] = received_pension_OnsetAge
    if 'received_disability_pension' in requested_features:
        data['received_disability_pension'] = received_disability_pension
        if params['OutputAge']=='T': data['received_disability_pension_OnsetAge'] = received_disability_pension_OnsetAge
    end = time()
    print("Pension data preprocessed in "+str(end-start)+" s")
    return data
                
def readIncome(data,params,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the pension registry
    #this function currently creates three variables, which are:
    #received_labor_income = Received labor income
    #total_income = Sum of labor income, pension and social benefits, indexed
    #total_labor_income = Sum of labor income, indexed
    start = time()
    keep_cols = ['id','vuosi','vuosiansio_indexed']
    income = pd.read_feather(params['IncomeFile'],columns=keep_cols)
    #keep only rows corresponding to IDs in samples
    income = income[income['id'].isin(ID_set)]
    print("Income, number or data rows: "+str(len(income)))
    
    #Note that the dataframe 'data' has already been initialized, so depending on the
    #value of params['ByYear'], it either contains one entry per ID, or one entry per ID
    #per year.
    #Also the variable 'total_income' is already in data
    labor_income = [0 for i in range(len(data))]
    received_labor_income = [0 for i in range(len(data))]
    if params['OutputAge']=='T': received_labor_income_OnsetAge = [np.nan for i in range(len(data))]

    for index,row in income.iterrows():
        ID = row['id']
        year = row['vuosi']

        if params['ByYear']=='T':
            key = (ID,year)
            if key not in data_ind_dict: continue
        elif params['ByYear']=='F': key = ID

        for ind in data_ind_dict[key]:
            fu_end = data.iloc[ind]['end_of_followup']
            fu_start = data.iloc[ind]['start_of_followup']
            #if year is outside the follow-up for this ID, skip
            if year<fu_start.year or year>fu_end.year: continue
            income_value = row['vuosiansio_indexed']
        
            #update the values
            #if params['ByYear']=='T': ind = data_ind_dict[(ID,fu_start,fu_end,year)]
            #else: ind = data_ind_dict[(ID,fu_start,fu_end)]
            labor_income[ind] += income_value
            if income_value>0: received_labor_income[ind] = 1
            #and the onset ages if requested
            if params['OutputAge']=='T':
                dob = data.iloc[ind]['date_of_birth']
                OnsetAge = getOnsetAge(dob,datetime(year,1,1))
                if np.isnan(received_labor_income_OnsetAge[ind]): received_labor_income_OnsetAge[ind] = OnsetAge
                elif received_labor_income_OnsetAge[ind]>OnsetAge: received_labor_income_OnsetAge[ind] = OnsetAge
    #Add the new columns to data
    if 'total_income' in requested_features:
        data['total_income'] = data['total_income'].add(labor_income,axis='index')
    if 'total_labor_income' in requested_features:
        data['total_labor_income'] = labor_income
    if 'received_labor_income' in requested_features:
        data['received_labor_income'] = received_labor_income
        if params['OutputAge']=='T': data['received_labor_income_OnsetAge'] = received_labor_income_OnsetAge

    end = time()
    print('Income data read in in '+str(end-start)+" s")
    return data

def readBenefits(data,params,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the pension registry
    #this function currently creates six variables, which are:
    #received_unemployment_allowance = Received earnings-related unemployment allowance
    #received_study_allowance = Received study allowance (only including finished degrees)
    #received_sickness_allowance = Received sickness daily allowance
    #received_basic_unemployment_allowance = Received basic daily unemployment allowance
    #received_maternity_paternity_parental_allowance = Received materntity, paternity or parental allowance
    #received_other_allowance = REceived any other type of allowance (source: ETK Pension)
    
    start = time()
    keep_cols = ['id','etuuslaji','alkamispvm','paattymispvm']
    benefits = pd.read_feather(params['BenefitsFile'],columns=keep_cols)
    #keep only rows corresponding to IDs in samples
    benefits = benefits[benefits['id'].isin(ID_set)]
    print("Benefits, number or data rows: "+str(len(benefits)))
    #convert the dates to datetime
    benefits['alkamispvm'] = pd.to_datetime(benefits['alkamispvm'])
    benefits['paattymispvm'] = pd.to_datetime(benefits['paattymispvm'])
    #Note that the dataframe 'data' has already been initialized, so depending on the
    #value of params['ByYear'], it either contains one entry per ID, or one entry per ID
    #per year.
    new_cols = {}
    new_cols['received_unemployment_allowance'] = [0 for i in range(len(data))]
    new_cols['received_study_allowance'] = [0 for i in range(len(data))]
    new_cols['received_sickness_allowance'] = [0 for i in range(len(data))]
    new_cols['received_basic_unemployment_allowance'] = [0 for i in range(len(data))]
    new_cols['received_maternity_paternity_parental_allowance'] = [0 for i in range(len(data))]
    new_cols['received_other_allowance'] = [0 for i in range(len(data))]

    if params['OutputAge']=='T':
        new_cols['received_unemployment_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        new_cols['received_study_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        new_cols['received_sickness_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        new_cols['received_basic_unemployment_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        new_cols['received_maternity_paternity_parental_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        new_cols['received_other_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        
        
    for index,row in benefits.iterrows():
        ID = row['id']
        b_start = row['alkamispvm'] #start date of allowance
        b_end = row['paattymispvm'] #end date of allowance

        #get the type of the social benefit
        benefit_type = int(row['etuuslaji'])
        if benefit_type==100 or benefit_type==101 or benefit_type==102 or benefit_type==103:
            #maternity, paternity or parental benefit
            benefit_var = 'received_maternity_paternity_parental_allowance'
        elif benefit_type==120 or benefit_type==121:
            #sickness allowance or partial sickness allowance
            benefit_var = 'received_sickness_allowance'
        elif benefit_type==150:
            #basic unemployment allowance
            benefit_var = 'received_basic_unemployment_allowance'
        elif benefit_type==210:
            #Earnings-related unemployment allowance
            benefit_var = 'received_unemployment_allowance'
        else: benefit_var = 'received_other_allowance'

        if params['ByYear']=='F':
            key = ID
            for ind in data_ind_dict[key]:
                fu_end = data.iloc[ind]['end_of_followup']
                fu_start = data.iloc[ind]['start_of_followup']
                #if the benefit period is outside the follow-up for this ID, skip
                if b_end<fu_start or b_start>fu_end: continue

                if b_start<fu_start: b_start = fu_start
                if b_end>fu_end: b_end = fu_end
        
                #update the values
                new_cols[benefit_var][ind] = 1
                #and the onset ages if requested
                if params['OutputAge']=='T':
                    dob = data.iloc[ind]['date_of_birth']
                    OnsetAge = getOnsetAge(dob,b_start)
                    if np.isnan(new_cols[benefit_var+'_OnsetAge'][ind]): new_cols[benefit_var+'_OnsetAge'][ind] = OnsetAge
                    elif new_cols[benefit_var+'_OnsetAge'][ind]>OnsetAge: new_cols[benefit_var+'_OnsetAge'][ind] = OnsetAge
            
        elif params['ByYear']=='T':
            #In some cases the starting date of the benefit is missing, this means
            #the entry is skipped
            if np.isnan(b_start.year): continue
            if np.isnan(b_start.year) or np.isnan(b_end.year): continue
            years = [a for a in range(b_start.year,b_end.year+1)]
            for year in years:
                key = (ID,year)
                #if year is outside of follow-up, skip this year
                if key not in data_ind_dict: continue
                for ind in data_ind_dict[key]:
                    #update the values
                    new_cols[benefit_var][ind] = 1
                    #and the onset ages if requested
                    if params['OutputAge']=='T':
                        dob = data.iloc[ind]['date_of_birth']
                        if year==b_start.year: onset_date = b_start
                        else: onset_date = datetime(year,1,1)
                        OnsetAge = getOnsetAge(dob,onset_date)
                        if np.isnan(new_cols[benefit_var+'_OnsetAge'][ind]): new_cols[benefit_var+'_OnsetAge'][ind] = OnsetAge
                        elif new_cols[benefit_var+'_OnsetAge'][ind]>OnsetAge: new_cols[benefit_var+'_OnsetAge'][ind] = OnsetAge

    #add the new columns
    for key in new_cols:
        if key in requested_features:
            data[key] = new_cols[key]
            if params['OutputAge']=='T': data[key+'_OnsetAge'] = new_cols[key+'_OnsetAge']
    end = time()
    print('Benefits data read in in '+str(end-start)+" s")
    return data

def readSocialAssistance(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the social assistance registry
    #this function currently creates three variables, which are:
    #received_any_income_support = Received basic, actual, preventive or complementary income support
    #total_income = Sum of labor income, pension and social benefits, indexed
    #total_benefits = sum of social benefits, indexed
    
    start = time()
    keep_cols = ['TNRO','TILASTOVUOSI','EHKAISEVA_TOIMEENTULOTUKI_EUR','PERUS_TOIMEENTULOTUKI_EUR','TAYD_TOIMEENTULOTUKI_EUR','KUNT_TOIMINTARAHA_EUR','KUNT_MATKAKORVAUS_EUR']
    #Note that column VARS_TOIMEENTULOTUKI_EUR seems to be sum of all other forms of income support except EHKAISEVA_TOIMEENTULOTUKI_EUR, that is why it is not used to avoid counting some of the income support twice
    assistance = pd.read_csv(params['SocialAssistanceFile'],usecols=keep_cols,sep=';')
    #keep only rows corresponding to IDs in samples
    assistance = assistance[assistance['TNRO'].isin(ID_set)]
    print("Social assistance, number or data rows: "+str(len(assistance)))
    sum_cols = list(assistance)
    sum_cols.remove('TNRO')
    sum_cols.remove('TILASTOVUOSI') #all columns used to compute sum of all income support
    assistance['tot_income_support'] = assistance[sum_cols].sum(axis=1)
    assistance = assistance[['TNRO','TILASTOVUOSI','tot_income_support']]

    #Note that the dataframe 'data' has already been initialized, so depending on the
    #value of params['ByYear'], it either contains one entry per ID, or one entry per ID
    #per year.
    #Also the variable 'total_income' is already in data
    received_any_income_support = [0 for i in range(len(data))]
    support_income = [0 for i in range(len(data))]
    if params['OutputAge']=='T': received_any_income_support_OnsetAge = [np.nan for i in range(len(data))]

    for index,row in assistance.iterrows():
        ID = row['TNRO']
        year = row['TILASTOVUOSI']
        if params['ByYear']=='F': key = ID
        elif params['ByYear']=='T':
            key = (ID,year)
            #if the year is not within follow-up, skip this entry
            if key not in data_ind_dict: continue
        for ind in data_ind_dict[key]:
            fu_end = data.iloc[ind]['end_of_followup']
            fu_start = data.iloc[ind]['start_of_followup']
            #if year is outside the follow-up for this ID, skip
            if year<fu_start.year or year>fu_end.year: continue

            if year not in cpi: C = cpi[1972]
            else: C = cpi[year]
        
            income_value = row['tot_income_support']*C #multiply with the consumer price index
            #if params['ByYear']=='T': ind = data_ind_dict[(ID,fu_start,fu_end,year)]
            #else: ind = data_ind_dict[(ID,fu_start,fu_end)]
            #update the values
            support_income[ind] += income_value
            if income_value>0: received_any_income_support[ind] = 1
            #and the onset ages if requested
            if params['OutputAge']=='T':
                dob = data.iloc[ind]['date_of_birth']
                OnsetAge = getOnsetAge(dob,datetime(year,1,1))
                if np.isnan(received_any_income_support_OnsetAge[ind]): received_any_income_support_OnsetAge[ind] = OnsetAge
                elif received_any_income_support_OnsetAge[ind]>OnsetAge: received_any_income_support_OnsetAge[ind] = OnsetAge

    #add the newly preprocessed values to data
    if 'total_income' in requested_features:
        data['total_income'] = data['total_income'].add(support_income,axis='index')
    if 'total_benefits' in requested_features:
        data['total_benefits'] = support_income
    if 'received_any_income_support' in requested_features:
        data['received_any_income_support'] = received_any_income_support
        if params['OutputAge']=='T': data['received_any_income_support_OnsetAge'] = received_any_income_support_OnsetAge
    
    end = time()
    print('Social assistance data read in in '+str(end-start)+" s")
    return data

def readMaritalStatus(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the DVV marriage history
    #this function currently creates two variables, which are:
    #divorced = Whether the individual has divorced; 0=no, 1=yes
    #married = Whether the individual has married; 0=no, 1=yes
    
    start = time()
    keep_cols = ['FINREGISTRYID','Current_marital_status','Starting_date','Ending_day']
    marriage = pd.read_csv(params['MarriageHistoryFile'],usecols=keep_cols,sep=',')
    #keep only rows corresponding to IDs in samples
    marriage = marriage[marriage['FINREGISTRYID'].isin(ID_set)]
    #keep only rows corresponding to current marital status being either married or divorced,
    #also include registered partnerships
    marriage = marriage.loc[(marriage['Current_marital_status']==2) | (marriage['Current_marital_status']==4) | (marriage['Current_marital_status']==6) | (marriage['Current_marital_status']==7)]
    #convert date columns to datetime
    marriage['Starting_date'] = pd.to_datetime(marriage['Starting_date'])
    marriage['Ending_day'] = pd.to_datetime(marriage['Ending_day'])
    
    print("Marriage history, number or data rows: "+str(len(marriage)))

    #initialize the new variables
    divorced = [0 for i in range(len(data))]
    married = [0 for i in range(len(data))]
    if params['OutputAge']=='T':
        divorced_OnsetAge = [np.nan for i in range(len(data))]
        married_OnsetAge = [np.nan for i in range(len(data))]

    for index,row in marriage.iterrows():
        ID = row['FINREGISTRYID']
        m_start = row['Starting_date'] #start date of marriage/reg. partnership
        m_end = row['Ending_day'] #end date of marriage/reg. partnership

        #get the current marital status
        m_status = int(row['Current_marital_status'])
        marriage_date = m_start
        if m_status==4 or m_status==7: divorce_date = m_end
        else: divorce_date = None

        if params['ByYear']=='F':
            key = ID
            for ind in data_ind_dict[key]:
                fu_end = data.iloc[ind]['end_of_followup']
                fu_start = data.iloc[ind]['start_of_followup']
                #if the marriage period is completely outside the follow-up for this ID, skip
                if m_end<fu_start or m_start>fu_end: continue
        
                if m_start<fu_start: m_start = fu_start
                if m_end>fu_end: m_end = fu_end
        
                #update the values
                #note that if a person has divorced, they must have been married or in a
                #registered partnership
                married[ind] = 1
                if divorce_date is not None:
                    #only count the divorce if it happens inside the follow-up period
                    if divorce_date<=m_end: divorced[ind] = 1
                #and the onset ages if requested
                if params['OutputAge']=='T':
                    dob = data.iloc[ind]['date_of_birth']
                    OnsetAge = getOnsetAge(dob,m_start)
                    if np.isnan(married_OnsetAge[ind]): married_OnsetAge[ind] = OnsetAge
                    elif married_OnsetAge[ind]>OnsetAge: married_OnsetAge[ind] = OnsetAge
                    if divorce_date is not None:
                        #only count the divorce if it happens inside the follow-up period
                        if divorce_date<=m_end:
                            OnsetAge = getOnsetAge(dob,divorce_date)
                            if np.isnan(divorced_OnsetAge[ind]): divorced_OnsetAge[ind] = OnsetAge
                            elif divorced_OnsetAge[ind]>OnsetAge: divorced_OnsetAge[ind] = OnsetAge
            
        elif params['ByYear']=='T':
            #If this option is selected, only those years when marriage/divorce actually happens
            #are marked with 1. Do for example if a person gets married before the start of the
            #follow-up period, they will only have married=0 entries for each year
            #If there is no starting date for marriage, the entry is skipped
            if pd.isnull(m_start): continue
            #if there is no end date for marriage, it is still continuing
            if pd.isnull(m_end): m_end = date.today()
            #print(row)
            for year in range(m_start.year,m_end.year+1):
                key = (ID,year)
                if key not in data_ind_dict: continue

                for m_ind in data_ind_dict[key]:
                    if m_start==marriage_date:
                        #m_ind = data_ind_dict[(ID,fu_start,fu_end,marriage_date.year)]
                        #update the values
                        #note that if a person has divorced, they must have been married or in a
                        #registered partnership
                        married[m_ind] = 1
                        #if divorce_date is not None:
                        if divorce_date==m_end:
                            d_key = (ID,divorce_date.year)
                            #d_ind = data_ind_dict[(ID,fu_start,fu_end,divorce_date.year)]
                            if d_key in data_ind_dict:
                                for d_ind in data_ind_dict[d_key]: divorced[d_ind] = 1
                                #and the onset ages if requested
                                if params['OutputAge']=='T':
                                    dob = data.iloc[m_ind]['date_of_birth']
                                    OnsetAge = getOnsetAge(dob,marriage_date)
                                    if np.isnan(married_OnsetAge[m_ind]): married_OnsetAge[m_ind] = OnsetAge
                                    elif married_OnsetAge[m_ind]>OnsetAge: married_OnsetAge[m_ind] = OnsetAge
                                    if divorce_date is not None:
                                        #only count the divorce if it happens this year
                                        if divorce_date==m_end:
                                            OnsetAge = getOnsetAge(dob,divorce_date)
                                            d_key = (ID,divorce_date.year)
                                            if d_key in data_ind_dict:
                                                for d_ind in data_ind_dict[d_key]:
                                                    if np.isnan(divorced_OnsetAge[d_ind]): divorced_OnsetAge[d_ind] = OnsetAge
                                                    elif divorced_OnsetAge[d_ind]>OnsetAge: divorced_OnsetAge[d_ind] = OnsetAge
                        
    #Add the new variables
    if 'divorced' in requested_features:
        data['divorced'] = divorced
        if params['OutputAge']=='T': data['divorced_OnsetAge'] = divorced_OnsetAge
    if 'married' in requested_features:
        data['married'] = married
        if params['OutputAge']=='T': data['married_OnsetAge'] = married_OnsetAge
            
    end = time()
    print('Marital status data read in in '+str(end-start)+" s")
    return data

def readPedigree(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the FinRegistry pedigree
    #this function currently creates one variables, which is:
    #children = Whether the individual has children.
    
    start = time()
    keep_cols = ['ID','MOTHER_ID','FATHER_ID','Birth_Date']
    pedigree = pd.read_csv(params['PedigreeFile'],usecols=keep_cols,sep='\t')
    #keep only rows corresponding to IDs in samples
    pedigree = pedigree[(pedigree['MOTHER_ID'].isin(ID_set)) | (pedigree['FATHER_ID'].isin(ID_set))]
    #convert date columns to datetime
    pedigree['Birth_Date'] = pd.to_datetime(pedigree['Birth_Date'])
    #convert nans to empty strings
    pedigree.fillna('',inplace=True)
    
    print("Pedigree, number or data rows: "+str(len(pedigree)))

    #initialize the new column
    children = [0 for i in range(len(data))]
    if params['OutputAge']=='T': children_OnsetAge = [np.nan for i in range(len(data))]

    father_ids = set(pedigree['FATHER_ID']).intersection(ID_set)
    mother_ids = set(pedigree['MOTHER_ID']).intersection(ID_set)

    #iterate over each child and count it for mothers and fathers who are in the study population
    for index,row in pedigree.iterrows():
        father_ID = row['FATHER_ID']
        mother_ID = row['MOTHER_ID']

        parent_IDs = []
        if father_ID in ID_set: parent_IDs.append(father_ID)
        if mother_ID in ID_set: parent_IDs.append(mother_ID)
        child_dob = row['Birth_Date']
        
        for ID in parent_IDs:
            if params['ByYear']=='F': key = ID
            elif params['ByYear']=='T':
                key = (ID,child_dob.year)
                #if child is born outside of follow-up for this parent, skip the child
                if key not in data_ind_dict: continue

            for ind in data_ind_dict[key]:
                fu_end = data.iloc[ind]['end_of_followup']
                fu_start = data.iloc[ind]['start_of_followup']
                if params['OutputAge']=='T': dob = data.iloc[ind]['date_of_birth']

                #only count children that are born within the specified follow-up period of the
                #parent
                if child_dob<fu_start or child_dob>fu_end: continue
            
                #if params['ByYear']=='F':
                #    ind = data_ind_dict[(ID,fu_start,fu_end)]
                #elif params['ByYear']=='T':
                #    year = child_dob.year
                #    ind = data_ind_dict[(ID,fu_start,fu_end,year)]
                children[ind] += 1
                if params['OutputAge']=='T':
                    #save the age at birth of first children during the follow-up
                    if not pd.isnull(children_OnsetAge[ind]):
                        OnsetAge = getOnsetAge(dob,child_dob)
                        children_OnsetAge[ind] = OnsetAge

    #save the required variables as new columns
    data['children'] = children
    if params['OutputAge']=='T': data['children_OnsetAge'] = children_OnsetAge
    end = time()
    print('Pedigree read in in '+str(end-start)+" s")

    return data

def readLiving(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the variables from the DVV living extended
    #this function currently creates 13 variables, which are:
    #zip_code = Zip code of place of residence
    #urbanization_class = Urbanisation Class (1 or 2)
    #urban_rural_class_code = Urban/Rural Class Code
    #sparse_small_house_area = Sparse Small House Area (binary indicator)
    #apartment_building_area = Apartment building Area (binary indicator)
    #small_house_area = Small house Area (binary indicator)
    #demographic_dependency_ratio = Demographic (or population) dependency ratio is the number of people aged under 15 and over 64 per hundred working-age people aged 15-64. The greater the number of children and/or retirement-age people, the higher the dependency ratio is. The source is Population Statistics, where the population consists of all people residing permanently within a geographical area (such as the whole country, region or sub-region). Those who according to the Population Information System are domiciled in Finland at the end of the year belong to the permanent resident population whatever their nationality, as do Finnish nationals temporarily residing abroad. Foreign nationals are domiciled in Finland if their stay is intended to last or has lasted at least twelve months. An asylum-seeker will not be granted a legal domicile until his/her application has been approved. Persons attached to foreign embassies, trade missions and consulates, as well as their family members and personal staff, are not counted among the resident population unless they are Finnish nationals. On the contrary, the Finnish staff of Finland's embassies and trade missions abroad and persons serving in the UN peacekeeping forces are counted among the resident population.
    #economic_dependency_ratio = Economic dependency ratio gives the number of people who are outside the labour force or unemployed per hundred employed people. People who are unemployed or outside the labour force (retired people, children and those engaged in family duties) constitute the economically inactive population. The population is classified based on their principal activity into economically active and economically inactive population (the labour force comprises the employed and the unemployed). The classification is based on information about the individual's activity during the last week of the year. In register-based data collection, the individual's subjective view of their own activity does not receive the same weight as in survey-based data collection. An individual who works while studying may be classified as a student in a questionnaire survey, while in register-based data collection the individual will be classified as employed if the employment is reported to the register. Undeclared work is outside the register. However, it can be assumed that work that is not declared to the tax authorities is not reported in a questionnaire survey either.
    #general_at_risk_of_poverty_rate_for_the_municipality = The indicator gives the percentage of persons living in households with low incomes in the total population of the geographical area. The risk-at-poverty threshold is set at 60% of each year's median equivalent disposable income of Finnish households (according to the adjusted OECD scale). Disposable income is calculated by adding together earned, entrepreneurial and property incomes and the income transfers received and by subtracting the income transfers paid. Equivalent income refers to all household members' combined disposable income divided by the total number of consumption units in the household. The statistics use the OECD's adjusted consumption unit scale, where the first adult of the household receives the weight 1, other over 13-year-olds receive the weight 0.5 and 0 to 13-year-olds receive the weight 0.3. Regional classification according to the latest statistical year.
    #intermunicipal_net_migration_1000_inhabitants = The indicator gives intermunicipal net migration per thousand inhabitants. Population figures refer to mean population. Net migration is obtained by subtracting those leaving the region (out-migrants) from those moving to the region (in-migrants). Accordingly, net migration is positive if more people have moved to the region than left it. Migration between municipalities has been adjusted throughout the time series so that it correspond with the most recent regional divisions, i.e., migration between municipalities that have since merged has been eliminated from the figures. Population proportions are calculated at THL based on the Population Statistics of Statistics Finland.
    #sale_of_alcoholic_beverages_per_capita = The indicator describes the amount of alcoholic beverages sold at Alko stores and delivered to grocery stores, kiosks, service stations and licensed restaurants within the area of the municipality, as litres of pure alcohol per local inhabitant during year. It describes the documented consumption of alcohol per capita. Population proportions are calculated at THL based on the Population Statistics of Statistics Finland.
    #self_rated_health_moderate_or_poor_scaled_health_and_welfare_indicator =
    #average_income_of_inhabitants = Average income of inhabitants (€) is the average annual income of inhabitants. (FROM: Statistics Finland 1km² dataset)
    #median_income_of_inhabitants = Median income of inhabitants (€) is obtained by listing inhabitants by the amount of disposable monetary income. Median income is the income of the middle inhabitant. An equal number of inhabitants remain on both sides of the middle inhabitant. (FROM: Statistics Finland 1km² dataset)
    
    start = time()
    #first read in the dvv_ext_core for individuals' information
    keep_cols = ['FINREGISTRYID','Start_of_residence','End_of_residence','posti_alue','TaajamaLuo','Luokka','sparse_small_house_area','apartment_building_area','small_house_area','demographic_dependency_ratio','economic_dependency_ratio','general_at_risk_of_poverty_rate_for_the_municipality','intermunicipal_net_migration_1000_inhabitants','sale_of_alcoholic_beverages_per_capita_as_litres_of_pure_alcohol','self_rated_health_moderate_or_poor_scaled_health_and_welfare_indicator','hr_ktu','hr_mtu','pt_vakiy']
    living = pd.read_csv(params['LivingExtendedFile'],usecols=keep_cols,sep=',',dtype={'posti_alue':str})
    #remove entries for IDs that are not in the study population
    living = living[living['FINREGISTRYID'].isin(ID_set)]
    #convert date columns to datetime
    living['Start_of_residence'] = pd.to_datetime(living['Start_of_residence'])
    living['End_of_residence'] = pd.to_datetime(living['End_of_residence'])
    #fill missing end dates of residence with today, assuming missing end date means
    #that the residence still continues in this address
    living['End_of_residence'] = living['End_of_residence'].fillna(datetime.now())
    #rename columns to output variables
    rename_dict = {'posti_alue':'zip_code','TaajamaLuo':'urbanization_class','Luokka':'urban_rural_class_code','sale_of_alcoholic_beverages_per_capita_as_litres_of_pure_alcohol':'sale_of_alcoholic_beverages_per_capita','hr_ktu':'average_income_of_inhabitants','hr_mtu':'median_income_of_inhabitants','pt_vakiy':'permanent_residents_fraction'}
    #These are the column names to merge to dataframe data
    out_cols = ['FINREGISTRYID','zip_code','urbanization_class','urban_rural_class_code','sparse_small_house_area','apartment_building_area','small_house_area','demographic_dependency_ratio','economic_dependency_ratio','general_at_risk_of_poverty_rate_for_the_municipality','intermunicipal_net_migration_1000_inhabitants','sale_of_alcoholic_beverages_per_capita','self_rated_health_moderate_or_poor_scaled_health_and_welfare_indicator','average_income_of_inhabitants','median_income_of_inhabitants','permanent_residents_fraction']
    living.rename(columns=rename_dict,inplace=True)
    #NOTE! Some information attached to a geographic location was not provided in the source
    #register due to there being too few inhabintants in the area, these values are marked
    #with -1 and here we just consider them missing values
    living.replace(to_replace=-1,value=np.nan,inplace=True)
    #sort the dataframe living by date in ascending order so that we can be sure the latest
    #place of residence is the last one encountered for each ID
    living.sort_values(inplace=True,by='Start_of_residence',ascending=True)
    end = time()
    print('Mangling the data frame took '+str(end-start)+" s")
    print("Living history, number or data rows: "+str(len(living)))

    
    #Note that if selecting binary output, we will only report the latest entry for each ID
    #create the new columns
    new_cols = {}
    for i in range(1,len(out_cols)): new_cols[out_cols[i]] = [np.nan for j in range(len(data))]

    if params['OutputAge']=='T':
        #Add only one column, as all of the place of residence related variables
        #have the same age of onset which corresponds to the date the person started
        #living in their final address
        zip_code_OnsetAge = [np.nan for i in range(len(data))]

    for index,row in living.iterrows():
        ID = row['FINREGISTRYID']
        living_start = row['Start_of_residence']
        living_end = row['End_of_residence']

        if params['ByYear']=='F':
            key = ID
            for ind in data_ind_dict[key]:
                fu_end = data.iloc[ind]['end_of_followup']
                fu_start = data.iloc[ind]['start_of_followup']
                if params['OutputAge']=='T': dob = data.iloc[ind]['date_of_birth']
                #check if the person has lived in this address during the requested follow-up period
                if living_start>fu_end: continue
                elif living_end<fu_start: continue

                #get the earliest age at which the person has lived in current address during their
                #follow-up period
                if fu_start>living_start: living_start = fu_start
        
                #add values from this row
                for i in range(1,len(out_cols)): new_cols[out_cols[i]][ind] = row[out_cols[i]]
                if params['OutputAge']=='T':
                    OnsetAge = getOnsetAge(dob,living_start)
                    zip_code_OnsetAge[ind] = OnsetAge
        
        elif params['ByYear']=='T':
            #if living_start is null, only mark residence for the living_end year
            if pd.isnull(living_start): living_start = living_end
            for year in range(living_start.year,living_end.year+1):
                key = (ID,year)
                if key not in data_ind_dict: continue

                for ind in data_ind_dict[key]:
                    fu_end = data.iloc[ind]['end_of_followup']
                    fu_start = data.iloc[ind]['start_of_followup']
                    if params['OutputAge']=='T': dob = data.iloc[ind]['date_of_birth']
                    #check if the person has lived in this address during the requested follow-up period
                    if living_start>fu_end: continue
                    elif living_end<fu_start: continue

                    
                    if living_end>fu_end: living_end = fu_end
                    
                    for year in range(living_start.year,living_end.year+1):
                        #data_ind = data_ind_dict[(ID,fu_start,fu_end,year)]
                        #add values from this row
                        for i in range(1,len(out_cols)): new_cols[out_cols[i]][ind] = row[out_cols[i]]
                        if params['OutputAge']=='T':
                            if year==living_start.year: start_date = living_start
                            else: start_date = datetime(year,1,1)
                            OnsetAge = getOnsetAge(dob,start_date)
                            zip_code_OnsetAge[ind] = OnsetAge
    #add the new columns to dataframe data
    for i in range(1,len(out_cols)):
        if out_cols[i] in requested_features: data[out_cols[i]] = new_cols[out_cols[i]]
    if params['OutputAge']=='T': data['zip_code_OnsetAge'] = zip_code_OnsetAge

    end = time()
    print('DVV living extended variables preprocessed in '+str(end-start)+" s")
    
    return data

def readSES(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the socioeconomic status variables from the SF Socioeconomic dataset
    #this function currently creates one variable, which is:
    #ses_self_employed = Socioeconomic status: self-employed
    #ses_upperlevel = Socioeconomic status: Upper-level employees with administrative, managerial, professional and related occupations
    #ses_lowerlevel = Socioeconomic status: Lower-level employees with administrative and clerical occupations
    #ses_manual_workers = Socioeconomic status: manual workers
    #ses_students = Socioeconomic status: students
    #ses_pensioners = Socioeconomic status: pensioners
    #ses_others	= Socioeconomic status: others
    #ses_unknown = Socioeconomic status unknown
    #ses_missing = Socioeconomic status missing
    
    start = time()
    ses = pd.read_csv(params['SESFile'])
    #keep only rows corresponding to IDs in samples
    ses = ses[ses['FINREGISTRYID'].isin(ID_set)]
    #skip rows with missing year
    print(ses.loc[ses['vuosi'].isnull()])
    ses = ses.loc[~ses['vuosi'].isnull()]
    #convert column data types
    ses['vuosi'] = ses['vuosi'].astype(int)
    ses['psose'] = ses['psose'].astype(str)
    ses['sose'] = ses['sose'].astype(str)
    ses.rename(columns={'vuosi':'year'},inplace=True)
    #sort the values by year to be certain the newest entry for each ID is read in last
    ses.sort_values(by='year',inplace=True)
    
    print("Socioeconomic status, number or data rows: "+str(len(ses)))

    ses_names = {'1':'ses_self_employed','3':'ses_upperlevel','4':'ses_lowerlevel','5':'ses_manual_workers','6':'ses_students','7':'ses_pensioners','8':'ses_others','9':'ses_unknown','NaN':'ses_missing'}
    #map both socioeconomic columns into the proposed format
    psose_map = {'11':'1','12':'1','21':'1','2':'1','22':'1','3':'3','31':'3','32':'3','33':'3','34':'3','4':'4','41':'4','42':'4','43':'4','44':'4','5':'5','51':'5','52':'5','53':'5','54':'5','7':'6','70':'6','6':'7','9':'8','91':'8','92':'8','93':'8','94':'8','99':'9'}
    #sose maps
    sose_1990_map = {'1':'1','10':'1','11':'1','12':'1','20':'1','2':'1','21':'1','22':'1','23':'1','24':'1','29':'1','3':'3','30':'3','31':'3','32':'3','33':'3','34':'3','39':'3','4':'4','40':'4','41':'4','42':'4','43':'4','44':'4','49':'4','5':'5','50':'5','51':'5','52':'5','53':'5','54':'5','59':'5','6':'7','60':'7','61':'7','7':'7','70':'6','71':'7','72':'7','73':'7','74':'7','79':'7','8':'8','81':'8','82':'8','83':'8','84':'8','85':'8','91':'8','92':'8','93':'8','94':'8','X':'9','9':'9','98':'9','99':'9','na':'NaN'}
    sose_map = {'1':'1','10':'1','11':'1','12':'1','20':'1','2':'1','21':'1','22':'1','23':'1','24':'1','29':'1','3':'3','30':'3','31':'3','32':'3','33':'3','34':'3','39':'3','4':'4','40':'4','41':'4','42':'4','43':'4','44':'4','49':'4','5':'5','50':'5','51':'5','52':'5','53':'5','54':'5','59':'5','6':'7','60':'6','61':'7','7':'7','70':'7','71':'7','72':'7','73':'7','74':'7','79':'7','8':'8','81':'8','82':'8','83':'8','84':'8','85':'8','91':'8','92':'8','93':'8','94':'8','X':'9','9':'9','98':'9','99':'9','na':'NaN'}
    
    #create new columns
    #latest socioeconomic status (within the specified follow-up) for each row in SamplesList
    ses_status = ['ses_missing' for i in range(len(data))]
    #only one variable to capture the onset age
    ses_OnsetAge = [np.nan for i in range(len(data))]
    for index,row in ses.iterrows():
        ID = row['FINREGISTRYID']
        year = row['year']
        if params['ByYear']=='T':
            key = (ID,year)
            if key not in data_ind_dict: continue
        elif params['ByYear']=='F': key = ID
        
        for ind in data_ind_dict[key]:
            fu_end = data.iloc[ind]['end_of_followup']
            fu_start = data.iloc[ind]['start_of_followup']
            #skip if year is outside of follow-up for this entry in SamplesList
            if year<fu_start.year or year>fu_end.year: continue
            
            if params['OutputAge']=='T': dob = data.iloc[ind]['date_of_birth']
            old_code = ses_status[ind]
            
            if year<1990:
                #code is psose
                code = row['psose'].split('.')[0]
                if len(code)>2: code = code[:2]
                #do not replace a real code with missing value
                if code=='na' and ses_status[ind]!='NaN': continue
                ses_status[ind] = ses_names[psose_map[code]]
            elif year<1995:
                #code is sose_1990
                code = row['sose'].split('.')[0]
                if len(code)>2: code = code[:2]
                #do not replace a real code with missing value
                if code=='na' and ses_status[ind]!='NaN': continue
                ses_status[ind] = ses_names[sose_1990_map[code]]
            else:
                #code is sose
                code = row['sose'].split('.')[0]
                if len(code)>2: code = code[:2]
                #do not replace a real code with missing value
                if code=='na' and ses_status[ind]!='NaN': continue
                ses_status[ind] = ses_names[sose_map[code]]

                #print(row)
                #print(code)
                #print(ses_status[ind])
                #while True:
                #    z = input('any')
                #    break
            #if onset age is requested
            if params['OutputAge']=='T':
                #if the socioeconomic status did not change from the last record,
                #then we keep the first occurrence of the same socioeconomic status
                #as the onset age
                if old_code!=code:
                    OnsetAge = getOnsetAge(dob,datetime(year,1,1))
                    ses_OnsetAge[ind] = OnsetAge
    #then add the new columns to dataframe data
    #but first read SES also from Social assistance register and birth register
    #to fill in possibly missing values
    #print(ses_status)
    data['ses'] = ses_status
    #print(data['ses'].value_counts())
    #add the onset column if requested
    if params['OutputAge']=='T':
        #print('Adding ses_OnsetAge column')
        data['ses_OnsetAge'] = ses_OnsetAge
        #print(data.columns)

    nan_IDs = set(data.loc[data['ses']=='ses_missing']['FINREGISTRYID'])
    print('Number of missing SESs:')
    print(len(data.loc[data['ses']=='ses_missing']['FINREGISTRYID']))
    if len(nan_IDs)>0:
        #first social assistance register
        keep_cols = ['TNRO','TILASTOVUOSI','SOSIOEKOASEMA']
        assistance = pd.read_csv(params['SocialAssistanceFile'],usecols=keep_cols,sep=';',dtype={'SOSIOEKOASEMA':str})
        #keep only rows corresponding to IDs with missing SES
        assistance = assistance[assistance['TNRO'].isin(nan_IDs)]
        #keep only rows with non-missing SOSIOEKOASEMA
        assistance = assistance.loc[~pd.isnull(assistance['SOSIOEKOASEMA'])]
        #print('SOSIOEKOASEMA from social assistance read in')
        for index,row in assistance.iterrows():
            ID = row['TNRO']
            year = row['TILASTOVUOSI']
            if params['ByYear']=='F': key = ID
            elif params['ByYear']=='T':
                key = (ID,year)
                if key not in data_ind_dict: continue
            #print(row)
            for ind in data_ind_dict[key]:
                #go through with each entry with NaN socioeconomic status and replace if a
                #value is found from the social assistance register
                old_code = data.iloc[ind]['ses']
                dob = data.iloc[ind]['date_of_birth']
                #print('dob:')
                #print(dob)
                #print('year:')
                #print(year)
                if year<1990:
                    #code is psose
                    code = row['SOSIOEKOASEMA'].split('.')[0]
                    if len(code)>2: code = code[:2]
                    #do not replace a real code with missing value
                    if code=='na' and ses_status[ind]!='NaN': continue
                    data.at[ind,'ses'] = ses_names[psose_map[code]]
                elif year<1995:
                    #code is sose_1990
                    code = row['SOSIOEKOASEMA'].split('.')[0]
                    if len(code)>2: code = code[:2]
                    #do not replace a real code with missing value
                    if code=='na' and ses_status[ind]!='NaN': continue
                    ses_status[ind] = ses_names[sose_1990_map[code]]
                else:
                    #code is sose
                    #print(row)
                    #print('dob:')
                    #print(dob)
                    #print('year:')
                    #print(year)
                    code = row['SOSIOEKOASEMA'].split('.')[0]
                    if len(code)>2: code = code[:2]
                    #do not replace a real code with missing value
                    if code=='na' and ses_status[ind]!='NaN': continue
                    data.at[ind,'ses'] = ses_names[sose_map[code]]
                if params['OutputAge']=='T':
                    #if the socioeconomic status did not change from the last record,
                    #then we keep the first occurrence of the same socioeconomic status
                    #as the onset age
                    if old_code!=code:
                        OnsetAge = getOnsetAge(dob,datetime(year,1,1))
                        data.at[ind,'ses_OnsetAge'] = OnsetAge

    #If we still have missing values, try to fill them from the birth registry
    nan_IDs = set(data.loc[data['ses']=='ses_missing']['FINREGISTRYID'])
    print('Number of missing SESs:')
    print(len(data.loc[data['ses']=='ses_missing']['FINREGISTRYID']))
    if len(nan_IDs)>0:
        #read birth register
        keep_cols = ['AITI_TNRO','TILASTOVUOSI','SOSEKO']
        birth = pd.read_feather(params['BirthFile'],columns=keep_cols)
        #keep only rows corresponding to IDs with missing SES
        birth = birth[birth['AITI_TNRO'].isin(nan_IDs)]
        #keep only rows with non-missing SOSEKO
        birth = birth.loc[~pd.isnull(birth['SOSEKO'])]
        birth['SOSEKO'] = birth['SOSEKO'].astype(str)
        #print('SOSEKO from birth registry read in')
        for index,row in birth.iterrows():
            ID = row['AITI_TNRO']
            year = row['TILASTOVUOSI']
            if params['ByYear']=='F': key = ID
            elif params['ByYear']=='T':
                key = (ID,year)
                if key not in data_ind_dict: continue
            for ind in data_ind_dict[key]:
                #go through with each entry with NaN socioeconomic status and replace if a
                #value is found from the birth register
                old_code = data.iloc[ind]['ses']
                if year<1990:
                    #code is psose
                    code = row['SOSEKO'].split('.')[0]
                    if len(code)>2: code = code[:2]
                    #do not replace a real code with missing value
                    if code=='na' and ses_status[ind]!='NaN': continue
                    data.at[ind,'ses'] = ses_names[psose_map[code]]
                elif year<1995:
                    #code is sose_1990
                    code = row['SOSEKO'].split('.')[0]
                    if len(code)>2: code = code[:2]
                    #do not replace a real code with missing value
                    if code=='na' and ses_status[ind]!='NaN': continue
                    ses_status[ind] = ses_names[sose_1990_map[code]]    
                else:
                    #code is sose
                    code = row['SOSEKO'].split('.')[0]
                    if len(code)>2: code = code[:2]
                    #do not replace a real code with missing value
                    if code=='na' and ses_status[ind]!='NaN': continue
                    #print('code='+str(code))
                    data.at[ind,'ses'] = ses_names[sose_map[code]]
                if params['OutputAge']=='T':
                    #if the socioeconomic status did not change from the last record,
                    #then we keep the first occurrence of the same socioeconomic status
                    #as the onset age
                    if old_code!=code:
                        OnsetAge = getOnsetAge(dob,datetime(year,1,1))
                        data.at[ind,'ses_OnsetAge'] = OnsetAge

    #print('Number of missing SESs:')
    #print(len(nan_IDs))
    print('Number of missing SESs:')
    print(len(data.loc[data['ses']=='ses_missing']['FINREGISTRYID']))
    #one-hot encode the socioeconomic status variable
    print(data['ses'].value_counts())
    data = pd.get_dummies(data,columns=['ses'],prefix=None)
    cols = list(data.columns)
    print('One-hot encoding done')
    #print(cols)
    #for c in cols:
    #    print(c)
    #    #print(data[c])
    #    if c.count('ses')>0: print(data[c].value_counts())
    #if there are no values for some of the ses levels, these indicator variables need to be
    #separately added
    ses_set = set(['ses_self_employed','ses_upperlevel','ses_lowerlevel','ses_manual_workers','ses_students','ses_pensioners','ses_others','ses_unknown','ses_missing'])
    #rename the ses columns
    for c in cols:
        if c.count('ses_')>0 and c!='ses_OnsetAge': data.rename(columns={c:c[4:]},inplace=True)
    #print(data.columns)
    data_cols_set = set(data.columns)
    #print(ses_set.difference(data_cols_set))
    for name in ses_set.difference(data_cols_set): data[name] = [0 for i in range(len(data))]

    end = time()
    print("Socioeconomic status preprocessed in "+str(end-start)+" s")
    return data

def readEdu(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the education variables from the SF Socioeconomic dataset
    #this function currently creates the following variables:
    #edu_years = Highest completed education in education years
    #edu_ongoing = Education possibly ongoing (age<35)
    #edufield_generic = Field of education: generic programmes and qualifications
    #edufield_education = Field of education: education
    #edufield_artshum = Field of education: Arts and humanities
    #edufield_socialsciences = Field of education: Social sciences, journalism and information
    #edufield_businessadminlaw = Field of education: Business, administration and law
    #edufield_science_math_stat = Field of education: Natural sciences, mathematics and statistics
    #edufield_ict = Field of education: Information and communication technologies
    #edufield_engineering = Field of education: Engineering, manufacturing and construction
    #edufield_agriculture = Field of education: Agriculture, forestry, fisheries and veterinary
    #edufield_health = Field of education: Health and wellfare
    #edufield_services = Field of education: Services
    #edufield_NA = Field of education not found or unknown
    
    start = time()
    edu = pd.read_csv(params['EducationFile'],usecols=["FINREGISTRYID","vuosi","iscfi2013","kaste_t2"],dtype={'iscfi2013':str,'kaste_t2':str},encoding = 'ISO-8859-1')
    #keep only rows corresponding to IDs in samples
    edu = edu[edu['FINREGISTRYID'].isin(ID_set)]
    #for both edulevel and edufield, keep only the first/2 first character of the code
    edu['kaste_t2'] = edu['kaste_t2'].str[0]
    edu['iscfi2013'] = edu['iscfi2013'].str[:2]
    #map missing values to lower secondary
    edu['kaste_t2'] = edu['kaste_t2'].fillna('2')
    #change the vuosi column to datetime
    edu['vuosi'] = pd.to_datetime(edu['vuosi'],format='%Y')
    print("Education, number or data rows: "+str(len(edu)))

    #mapping of education levels to education years, using the median ages for each
    #education level
    edu_year_map = {'2':16.5,'3':18.7,'4':38.5,'5':24.2,'6':25.1,'7':27.4,'8':34.8}
    #notice that the education years are computed based on the highest completed degree, so durations of multiple degrees are not summed up
    #mapping of fields of education
    edu_field_map = {'00':'edufield_generic','01':'edufield_education','02':'edufield_artshum','03':'edufield_socialsciences','04':'edufield_businessadminlaw','05':'edufield_science_math_stat','06':'edufield_ict','07':'edufield_engineering','08':'edufield_agriculture','09':'edufield_health','10':'edufield_services','99':'edufield_NA'}

    #map all education levels according to edu_year_map
    edu['kaste_t2'] = edu['kaste_t2'].map(edu_year_map)
    #map all education field values according to edu_field_map
    edu['iscfi2013'] = edu['iscfi2013'].map(edu_field_map)
    #print(edu['iscfi2013'].value_counts())
    #create the new variables
    edu_years = [0.0 for i in range(len(data))]
    edufield = ['edufield_NA' for i in range(len(data))]
    #possible ages of onset
    if params['OutputAge']=='T': edufield_OnsetAge = [np.nan for i in range(len(data))]

    for index,row in edu.iterrows():
        ID = row['FINREGISTRYID']
        year = row['vuosi'].year
        #print(year)
        if params['ByYear']=='T':
            key = (ID,year)
            if key not in data_ind_dict: continue
        elif params['ByYear']=='F': key = ID
        
        for ind in data_ind_dict[key]:
            fu_end = data.iloc[ind]['end_of_followup']
            fu_start = data.iloc[ind]['start_of_followup']
            #skip if year is outside of follow-up for this entry
            if year<fu_start.year or year>fu_end.year: continue
            
            if params['OutputAge']=='T': dob = data.iloc[ind]['date_of_birth']
            old_edulevel = edu_years[ind]
            edulevel = row['kaste_t2']
            if edulevel>old_edulevel:
                #only update edulevel if it is higher than what is recorded previously
                edu_years[ind] = edulevel
                edufield[ind] = row['iscfi2013']
                #if onset age is requested
                if params['OutputAge']=='T':
                    #For lower-secondary education we do not have the year available
                    #so it is set to the population median
                    if edulevel<18: OnsetAge = getOnsetAge(dob,datetime(dob.year+16,1,1))
                    else: OnsetAge = getOnsetAge(dob,datetime(year,1,1))
                    edufield_OnsetAge[ind] = OnsetAge
    #add the new columns to data
    if 'edu_years' in requested_features: data['edu_years'] = edu_years
    if 'edu_ongoing' in requested_features:
        data['edu_ongoing'] = np.where(((data['end_of_followup']-data['date_of_birth']).dt.days/365.0)<35,1,0)
    if 'edufield_generic' in requested_features:
        #one-hot encode the field of education variable
        data['edufield'] = edufield
        #print(data['edufield'].value_counts())
        #print(data)
        data = pd.get_dummies(data,columns=['edufield'],prefix=None)
        #print(data)
        cols = list(data.columns)
        #print('One-hot encoding done')
        #if there are no values for some of the education fields,
        #these indicator variables need to be
        #separately added
        edu_set = set(['edufield_generic','edufield_education','edufield_artshum','edufield_socialsciences','edufield_businessadminlaw','edufield_science_math_stat','edufield_ict','edufield_engineering','edufield_agriculture','edufield_health','edufield_services','edufield_NA'])
        #rename the education field columns
        for c in cols:
            if c.count('edufield_')>0: data.rename(columns={c:c[9:]},inplace=True)
        #print(data.columns)
        data_cols_set = set(data.columns)
        for name in edu_set.difference(data_cols_set): data[name] = [0 for i in range(len(data))]
        
        if params['OutputAge']=='T': data['edufield_OnsetAge'] = edufield_OnsetAge
        #while True:
        #    z = input('any')
        #    break
    return data

def readBirth(data,params,cpi,requested_features,ID_set,data_ind_dict):
    #Read in the education variables from the Birth registry
    #this function currently creates the following variables:
    #miscarriages = Number of miscarriages (KESKENMENOJA)
    #terminated_pregnancies = Number of terminated pregnancies (KESKEYTYKSIA)
    #ectopic_pregnancies = Number of ectopic pregnancies (ULKOPUOLISIA)
    #stillborns	= Number of births with at least one stillborn infant (KUOLLEENASYNT)
    #no_smoking_during_pregnancy = No smoking during pregnancy (TUPAKOINTITUNNUS)
    #quit_smoking_during_1st_trimester = Quit smoking during 1. trimester (TUPAKOINTITUNNUS)
    #smoked_after_1st_trimester = Smoked after 1. trimester (TUPAKOINTITUNNUS)
    #smoking_during_pregnancy_NA = Smoking information during pregnancy not available (TUPAKOINTITUNNUS)
    #invitro_fertilization = In-vitro fertilization (IVF)
    #thrombosis_prophylaxis = Thrombosis prophylaxis (TROMBOOSIPROF)
    #anemia = Anemia during pregnancy (ANEMIA)
    #glucose_test_abnormal = Glucose test abnormal during pregnancy (SOKERI_PATOL)
    #no_analgesics = No analgesics during labor (EI_LIEVITYSTA)
    #analgesics_info_missing = Information about analgesics during labor missing (EI_LIEVITYS_TIETOA)
    #initiated_labor = Artificially initiated labor (KAYNNISTYS)
    #promoted_labor = Promoted labor (EDISTAMINEN)
    #puncture = Amniotic membrane puncture during labor (PUHKAISU)
    #oxytocin = Oxytocin during labor (OKSITOSIINI)
    #prostaglandin = Prostaglandin during labor (PROSTAGLANDIINI)
    #extraction_of_placenta = Manual extraction of placenta (ISTUKANIRROITUS)
    #uterine_scraping = Uterine scraping (KAAVINTA)
    #suturing = Suturing during labor (OMPELU)
    #prophylaxis = Intrapartum antiobiotic Group B Streptococcal prophylaxis (GBS_PROFYLAKSIA)
    #mother_antibiotics	= Antiobiotic treatment of the mother during labor (AIDIN_ANTIBIOOTTIHOITO)
    #blood_transfusion = Blood transfusion during labor (VERENSIIRTO)
    #circumcision = Opening of circumcision during labor (YMPARILEIKKAUKSEN_AVAUS)
    #hysterectomy = Hysterectomy (KOHDUNPOISTO)
    #embolisation = Embolisation (EMBOLISAATIO)
    #vaginal_delivery = Vaginal delivery (SYNNYTYSTAPATUNNUS)
    #vaginal_delivery_breech = Vaginal delivery, breech (SYNNYTYSTAPATUNNUS)
    #forceps_delivery = Forceps-assisted delivery (SYNNYTYSTAPATUNNUS)
    #vacuum_delivery = Vacuum-assisted delivery (SYNNYTYSTAPATUNNUS)
    #planned_c_section = Delivery by planned C-section (SYNNYTYSTAPATUNNUS)
    #urgent_c_section = Delivery by urgent C-section (SYNNYTYSTAPATUNNUS)
    #emergency_c_section = Delivery by emergency C-section (SYNNYTYSTAPATUNNUS)
    #not_planned_c_section = Delivery by C-section, not planned (before 2004) (SYNNYTYSTAPATUNNUS)
    #mode_of_delivery_NA = Mode of delivery missing or unknown (SYNNYTYSTAPATUNNUS)
    #placenta_praevia = Placenta praevia (ETINEN)
    #ablatio_placentae = Ablatio placentae (ISTIRTO)
    #eclampsia = Eclampsia (RKOURIS)
    #shoulder_dystocia = Shoulder dystocia (HARTIADYSTOKIA)
    #asphyxia = Asphyxia (ASFYKSIA)
    #live_born = Child born live (SYNTYMATILATUNNUS)
    #stillborn_before_delivery = Child stillborn, died before delivery (SYNTYMATILATUNNUS)
    #stillborn_during_delivery = Child stillborn, died during delivery (SYNTYMATILATUNNUS)
    #stillborn_unknown = Child stillborn, unknown if died before or during delivery (SYNTYMATILATUNNUS)
    #birth_status_NA = Information missing about birth status of the child (SYNTYMATILATUNNUS)

    start = time()
    usecols = ['AITI_TNRO','TILASTOVUOSI','AITI_IKA','KESKENMENOJA','KESKEYTYKSIA','ULKOPUOLISIA','KUOLLEENASYNT','TUPAKOINTITUNNUS','IVF','TROMBOOSIPROF','ANEMIA','SOKERI_PATOL','EI_LIEVITYSTA','EI_LIEVITYS_TIETOA','KAYNNISTYS','EDISTAMINEN','PUHKAISU','OKSITOSIINI','PROSTAGLANDIINI','ISTUKANIRROITUS','KAAVINTA','OMPELU','GBS_PROFYLAKSIA','AIDIN_ANTIBIOOTTIHOITO','VERENSIIRTO','YMPARILEIKKAUKSEN_AVAUS','KOHDUNPOISTO','EMBOLISAATIO','SYNNYTYSTAPATUNNUS','ETINEN','ISTIRTO','RKOURIS','HARTIADYSTOKIA','ASFYKSIA','SYNTYMATILATUNNUS']
    birth = pd.read_feather(params['BirthFile'],columns=usecols)
    #keep only rows corresponding to IDs in samples
    birth = birth[birth['FINREGISTRYID'].isin(ID_set)]

    #rename columns to match the output variable names
    rename_col_dict = {'KESKENMENOJA':'miscarriages','KESKEYTYKSIA':'terminated_pregnancies','ULKOPUOLISIA':'ectopic_pregnancies','KUOLLEENASYNT':'stillborns','IVF':'invitro_fertilization','TROMBOOSIPROF':'thrombosis_prophylaxis','ANEMIA':'anemia','SOKERI_PATOL':'glucose_test_abnormal','EI_LIEVITYSTA':'no_analgesics','EI_LIEVITYS_TIETOA':'analgesics_info_missing','KAYNNISTYS':'initiated_labor','EDISTAMINEN':'promoted_labor','PUHKAISU':'puncture','OKSITOSIINI':'oxytocin','PROSTAGLANDIINI':'prostaglandin','ISTUKANIRROITUS':'extraction_of_placenta','KAAVINTA':'uterine_scraping','OMPELU':'suturing','GBS_PROFYLAKSIA':'prophylaxis','AIDIN_ANTIBIOOTTIHOITO':'mother_antibiotics','VERENSIIRTO':'blood_transfusion','YMPARILEIKKAUKSEN_AVAUS':'circumcision','KOHDUNPOISTO':'hysterectomy','EMBOLISAATIO':'embolisation','ETINEN':'placenta_praevia','ISTIRTO':'ablatio_placentae','RKOURIS':'eclampsia','HARTIADYSTOKIA':'shoulder_dystocia','ASFYKSIA':'asphyxia'}

    birth = birth.rename(columns=rename_col_dict)
    #rename levels of TUPAKOINTITUNNUS, SYNNYTYSTAPATUNNUS and SYNTYMATILATUNNUS
    TUPAKOINTITUNNUS_dict = {1:'no_smoking_during_pregnancy',2:'quit_smoking_during_1st_trimester',3:'smoked_after_1st_trimester',4:'smoked_after_1st_trimester',9:'smoking_during_pregnancy_NA'}
    SYNNYTYSTAPATUNNUS_dict = {1.0:'vaginal_delivery',2.0:'vaginal_delivery_breech',3.0:'forceps_delivery',4.0:'vacuum_delivery',5.0:'planned_c_section',6.0:'urgent_c_section',7.0:'emergency_c_section',8.0:'not_planned_c_section',9.0:'mode_of_delivery_NA',np.nan:'mode_of_delivery_NA'}
    SYNTYMATILATUNNUS_dict = {1:'live_born',2:'stillborn_before_delivery',3:'stillborn_during_delivery',4:'stillborn_unknown'}

    birth['TUPAKOINTITUNNUS'] = birth['TUPAKOINTITUNNUS'].map(TUPAKOINTITUNNUS_dict)
    birth['SYNNYTYSTAPATUNNUS'] = birth['SYNNYTYSTAPATUNNUS'].map(SYNNYTYSTAPATUNNUS_dict)
    birth['SYNTYMATILATUNNUS'] = birth['SYNTYMATILATUNNUS'].map(SYNTYMATILATUNNUS_dict)

    #initialize the new columns
    new_cols = {}
    for cname in birth.columns:
        if cname not in ['AITI_TNRO','TILASTOVUOSI','AITI_IKA']: new_cols[cname] = [0 for i in range(len(data))]
    if params['OutputAge']=='T': birth_onsetAge = [np.nan for i in range(len(data))]

    for index,row in birth.iterrows():
        ID = row['AITI_TNRO']
        year = row['TILASTOVUOSI']
        if params['ByYear']=='T':
            key = (ID,year)
            if key not in data_ind_dict: continue
        elif params['ByYear']=='F': key = ID
        
        for ind in data_ind_dict[key]:
            fu_end = data.iloc[ind]['end_of_followup']
            fu_start = data.iloc[ind]['start_of_followup']
            #skip if year is outside of follow-up for this entry
            if year<fu_start.year or year>fu_end.year: continue

            for cname in new_cols:
                #do not overwrite 1s with never 0s
                if new_cols[cname][ind]<1: new_cols[cname][ind] = row[cname]
            #check if age at birth is requested
            if params['OutputAge']=='T': birth_onsetAge[ind] = row['AITI_IKA']
    #add the new columns to data
    for cname in new_cols:
        if cname in requested_features: data[cname] = new_cols[cname]
    if 'no_smoking_during_pregnancy' in requested_features:
        data['TUPAKOINTITUNNUS'] = new_cols['TUPAKOINTITUNNUS']
        #one-hot encode
        data = pd.get_dummies(data,columns=['TUPAKOINTITUNNUS'],prefix=None)
        cols = list(data.columns)
        for c in cols:
            if c.count('TUPAKOINTITUNNUS_')>0: data.rename(columns={c:c[17:]},inplace=True)
        smoking_set = set(['no_smoking_during_pregnancy','quit_smoking_during_1st_trimester','smoked_after_1st_trimester','smoked_after_1st_trimester','smoking_during_pregnancy_NA'])
        #if some of the smoking levels are missing from the data, add empty columns
        data_cols_set = set(data.columns)
        for name in smoking_set.difference(data_cols_set): data[name] = [0 for i in range(len(data))]
            
    if 'vaginal_delivery' in requested_features:
        data['SYNNYTYSTAPATUNNUS'] = new_cols['SYNNYTYSTAPATUNNUS']
        #one-hot encode
        data = pd.get_dummies(data,columns=['SYNNYTYSTAPATUNNUS'],prefix=None)
        cols = list(data.columns)
        for c in cols:
            if c.count('SYNNYTYSTAPATUNNUS_')>0: data.rename(columns={c:c[19:]},inplace=True)
        delivery_set = set(['vaginal_delivery','vaginal_delivery_breech','forceps_delivery','vacuum_delivery','planned_c_section','urgent_c_section','emergency_c_section','not_planned_c_section','mode_of_delivery_NA'])
        #if some of the smoking levels are missing from the data, add empty columns
        data_cols_set = set(data.columns)
        for name in delivery_set.difference(data_cols_set): data[name] = [0 for i in range(len(data))]
        
    if 'live_born' in requested_features:
        data['SYNTYMATILATUNNUS'] = new_cols['SYNTYMATILATUNNUS']
        #one-hot encode
        data = pd.get_dummies(data,columns=['SYNTYMATILATUNNUS'],prefix=None)
        cols = list(data.columns)
        for c in cols:
            if c.count('SYNTYMATILATUNNUS_')>0: data.rename(columns={c:c[18:]},inplace=True)
        birth_set = set(['live_born','stillborn_before_delivery','stillborn_during_delivery','stillborn_unknown'])
        #if some of the smoking levels are missing from the data, add empty columns
        data_cols_set = set(data.columns)
        for name in birth_set.difference(data_cols_set): data[name] = [0 for i in range(len(data))]
    if params['OutputAge']=='T': data['birth_OnsetAge'] = birth_onsetAge

    return data
