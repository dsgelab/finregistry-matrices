import csv

import numpy as np
import pandas as pd

from datetime import datetime
from time import time

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
    samples = pd.read_csv(params['SampleFile'])
    #convert the date columns to datetime
    samples['start_of_followup'] = pd.to_datetime(samples['start_of_followup'])
    samples['end_of_followup'] = pd.to_datetime(samples['end_of_followup'])
    samples['date_of_birth'] = pd.to_datetime(samples['date_of_birth'])
    #Read in sex from minimal phenotype file
    mpf = pd.read_feather(params['MinimalPhenotypeFile'],columns=['FINREGISTRYID','sex'])
    samples =  samples.merge(mpf,how='left',on='FINREGISTRYID')

    if params['ByYear']=='F': data = samples[['FINREGISTRYID']]
    elif params['ByYear']=='T':
        data = pd.DataFrame()
        IDs = []
        years = []
        sexs = []
        #create one entry row per each year of follow-up for each individual
        for index,row in samples.iterrows():
            start_year = row['start_of_followup'].year
            end_year = row['end_of_followup'].year
            for year in range(start_year,end_year+1):
                IDs.append(row['FINREGISTRYID'])
                #dobs.append(row['date_of_birth'])
                sexs.append(row['sex'])
                #starts.append(row['start_of_followup'])
                #ends.append(row['end_of_followup'])
                years.append(year)
        data['FINREGISTRYID'] = IDs
        data['year'] = years
        #data['date_of_birth'] = dobs
        data['sex'] = sexs
        #data['start_of_followup'] = starts
        #data['end_of_followup'] = ends
        
    features = pd.read_csv(params['FeatureFile'])
    return samples,features,data

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

def readPension(samples,data,params,cpi,requested_features):
    #Read in the variables from the pension registry
    #this function currently creates three variables, which are:
    #received_disability_pension = Received disability pension
    #received_pension = Received any pension
    #total_income = Sum of labor income, pension and social benefits, indexed
    start = time()
    keep_cols = ['id','apvm','ppvm','ptma','ltma','jkma','tksyy1']
    pension = pd.read_feather(params['PensionFile'],columns=keep_cols)
    #keep only rows corresponding to IDs in samples
    ID_set = set(samples['FINREGISTRYID'])
    pension = pension[pension['id'].isin(ID_set)]
    #convert date strings to datetime
    pension['apvm'] = pd.to_datetime(pension['apvm'])
    pension['ppvm'] = pd.to_datetime(pension['ppvm'])

    if params['ByYear']=='F':
        received_disability_pension = []
        received_pension = []
        total_income = []
        if params['OutputAge']=='T':
            received_disability_pension_OnsetAge = []
            received_pension_OnsetAge = []
            total_income_OnsetAge = []
        for index,row in samples.iterrows():
            ID = row['FINREGISTRYID']
            #get all pension info for this ID
            pension_id = pension.loc[pension['id']==ID]
            #go through each entry
            if len(pension_id)<1:
                received_disability_pension.append(0)
                received_pension.append(0)
                total_income.append(0)
                if params['OutputAge']=='T':
                    received_disability_pension_OnsetAge.append(np.nan)
                    received_pension_OnsetAge.append(np.nan)
                    total_income_OnsetAge.append(np.nan)
                continue
            else:
                #only consider entries within the inclusion period of the individual
                fu_start = row['start_of_followup']
                fu_end = row['end_of_followup']
                tot_pension = 0.0
                disability = False
                if params['OutputAge']=='T':
                    OnsetAge_pension = np.nan
                    OnsetAge_disability_pension = np.nan

                for p_index,p_row in pension_id.iterrows():
                    if not pd.isna(p_row['tksyy1']): disability = True #ID has received disability pension
                    p_start = p_row['apvm']
                    p_end = p_row['ppvm']
                    if pd.isna(p_end): p_end = fu_end
                    
                    if p_end<fu_start or p_start>fu_end: continue
                    if p_start<fu_start: p_start = fu_start
                    if p_end>fu_end: p_end = fu_end

                    if params['OutputAge']=='T':
                        #save the first pension occurrence for each individual
                        dob = row['date_of_birth']
                        age = getOnsetAge(dob,p_start)
                        if np.isnan(OnsetAge_pension): OnsetAge_pension = age
                        #and first disability pension occurrence
                        if not pd.isna(p_row['tksyy1']):
                            if np.isnan(OnsetAge_disability_pension): OnsetAge_disability_pension = age
                            elif age<OnsetAge_disability_pension: OnsetAge_disability_pension = age
                    #add up the pension from range p_start -> p_end
                    #corrected with the consumer price index
                    for year in range(p_start.year,p_end.year+1):
                        if not pd.isna(p_row['ptma']): tot_pension += cpi[year]*12*p_row['ptma']
                        if not pd.isna(p_row['ltma']): tot_pension += cpi[year]*12*p_row['ltma']
                        if not pd.isna(p_row['jkma']):tot_pension += cpi[year]*12*p_row['jkma']
                    #correct the amount paid for first and last year
                    if not pd.isna(p_row['ptma']): tot_pension -= cpi[p_start.year]*(p_start.month-1)*p_row['ptma']
                    if not pd.isna(p_row['ltma']): tot_pension -= cpi[p_start.year]*(p_start.month-1)*p_row['ltma']
                    if not pd.isna(p_row['jkma']): tot_pension -= cpi[p_start.year]*(p_start.month-1)*p_row['jkma']

                    if not pd.isna(p_row['ptma']): tot_pension -= cpi[p_end.year]*(12-p_end.month)*p_row['ptma']
                    if not pd.isna(p_row['ltma']): tot_pension -= cpi[p_end.year]*(12-p_end.month)*p_row['ltma']
                    if not pd.isna(p_row['jkma']): tot_pension -= cpi[p_end.year]*(12-p_end.month)*p_row['jkma']
                #save values of the final variables for the current ID
                total_income.append(tot_pension)
                if tot_pension>0: received_pension.append(1)
                else: received_pension.append(0)
                if disability: received_disability_pension.append(1)
                else: received_disability_pension.append(0)

                if params['OutputAge']=='T':
                    total_income_OnsetAge.append(OnsetAge_pension)
                    received_pension_OnsetAge.append(OnsetAge_pension)
                    received_disability_pension_OnsetAge.append(OnsetAge_disability_pension)
                    
    elif params['ByYear']=='T':
        #one entry per each year in output
        received_disability_pension = [0 for i in range(len(data))]
        received_pension = [0 for i in range(len(data))]
        total_income = [0 for i in range(len(data))]
        if params['OutputAge']=='T':
            received_disability_pension_OnsetAge = [np.nan for i in range(len(data))]
            received_pension_OnsetAge = [np.nan for i in range(len(data))]
            total_income_OnsetAge = [np.nan for i in range(len(data))]
        for p_index,p_row in pension.iterrows():
            ID = p_row['id']
            fu_end = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['end_of_followup']
            fu_start = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['start_of_followup']
            p_start = p_row['apvm']#.astype(datetime)
            p_end = p_row['ppvm']#.astype(datetime)
            if pd.isna(p_end): p_end = fu_end
            #print("fu_start:")
            #print(fu_start)
            #print("fu_end:")
            #print(fu_end)
            #print("p_start:")
            #print(p_start)
            #print("p_end:")
            #print(p_end)
            if params['OutputAge']=='T':
                #output also ages of onset
                dob = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
            #iterate over each year covered by this entry
            for year in range(p_start.year,p_end.year+1):
                if year<(fu_start.year) or year>(fu_end.year): continue
                #add up the  pension from year
                #corrected with the consumer price index
                disability = False
                tot_pension = 0.0
                
                if params['OutputAge']=='T':
                    if year==p_start.year: onset_date = p_start
                    else: onset_date = datetime(year,1,1)
                    OnsetAge = getOnsetAge(dob,onset_date)
                if not pd.isna(p_row['tksyy1']): disability = True #ID has received disability pension
                n_month = 12
                if year==p_start.year: n_month = n_month-(p_start.month-1)
                if year==p_end.year: n_month = n_month-(12-p_end.month)
                if not pd.isna(p_row['ptma']): tot_pension += cpi[year]*12*p_row['ptma']
                if not pd.isna(p_row['ltma']): tot_pension += cpi[year]*12*p_row['ltma']
                if not pd.isna(p_row['jkma']): tot_pension += cpi[year]*12*p_row['jkma']
                #get the correct row index in the dataframe data
                ind = data.index[(data['FINREGISTRYID']==ID) & (data['year']==year)][0]
                total_income[ind] += tot_pension
                if tot_pension>0: received_pension[ind] = 1
                
                if tot_pension>0 and params['OutputAge']=='T':
                    if np.isnan(total_income_OnsetAge[ind]):
                        total_income_OnsetAge[ind] = OnsetAge
                        received_pension_OnsetAge[ind] = OnsetAge
                    elif total_income_OnsetAge[ind]>OnsetAge:
                        total_income_OnsetAge[ind] = OnsetAge
                        received_pension_OnsetAge[ind] = OnsetAge
                    
                if disability: received_disability_pension[ind] = 1
                if disability and params['OutputAge']=='T':
                    if np.isnan(received_disability_pension_OnsetAge[ind]): received_disability_pension_OnsetAge[ind] = OnsetAge
                    elif received_disability_pension_OnsetAge[ind]>OnsetAge: received_disability_pension_OnsetAge[ind] = OnsetAge
                    
    #add the created variables as columns to the df data
    if 'total_income' in requested_features:
        data['total_income'] = total_income
        if params['OutputAge']=='T': data['total_income_OnsetAge'] = total_income_OnsetAge
    if 'received_pension' in requested_features:
        data['received_pension'] = received_pension
        if params['OutputAge']=='T': data['received_pension_OnsetAge'] = received_pension_OnsetAge
    if 'received_disability_pension' in requested_features:
        data['received_disability_pension'] = received_disability_pension
        if params['OutputAge']=='T': data['received_disability_pension_OnsetAge'] = received_disability_pension_OnsetAge
    end = time()
    print("Pension data preprocessed in "+str(end-start)+" s")
    return data

def readIncome(samples,data,params,requested_features):
    #Read in the variables from the pension registry
    #this function currently creates two variables, which are:
    #received_labor_income = Received labor income
    #total_income = Sum of labor income, pension and social benefits, indexed
    start = time()
    keep_cols = ['id','vuosi','vuosiansio_indexed']
    income = pd.read_feather(params['IncomeFile'],columns=keep_cols)
    #keep only rows corresponding to IDs in samples
    ID_set = set(samples['FINREGISTRYID'])
    income = income[income['id'].isin(ID_set)]

    #Note that the dataframe 'data' has already been initialized, so depending on the
    #value of params['ByYear'], it either contains one entry per ID, or one entry per ID
    #per year.
    #Also the variable 'total_income' is already in data
    received_labor_income = [0 for i in range(len(data))]
    if params['OutputAge']=='T': received_labor_income_OnsetAge = [np.nan for i in range(len(data))]

    for index,row in income.iterrows():
        ID = row['id']
        year = row['vuosi']
        fu_end = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['end_of_followup']
        fu_start = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['start_of_followup']
        #if year is outside the follow-up for this ID, skip
        if year<fu_start.year or year>fu_end.year: continue
        income_value = row['vuosiansio_indexed']
        if params['ByYear']=='T': ind = data.index[(data['FINREGISTRYID']==ID) & (data['year']==year)][0]
        else: ind = data.index[data['FINREGISTRYID']==ID][0]
        #update the values
        data.loc[ind,'total_income'] += income_value
        if income_value>0: received_labor_income[ind] = 1
        #and the onset ages if requested
        if params['OutputAge']=='T':
            dob = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
            OnsetAge = getOnsetAge(dob,datetime(year,1,1))
            if np.isnan(received_labor_income_OnsetAge[ind]): received_labor_income_OnsetAge[ind] = OnsetAge
            elif received_labor_income_OnsetAge[ind]>OnsetAge: received_labor_income_OnsetAge[ind] = OnsetAge
    #Add the new columns to data
    data['received_labor_income'] = received_labor_income
    if params['OutputAge']=='T': data['received_labor_income_OnsetAge'] = received_labor_income_OnsetAge

    end = time()
    print('Income data read in in '+str(end-start)+" s")
    return data

def readBenefits(samples,data,params,requested_features):
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
    ID_set = set(samples['FINREGISTRYID'])
    benefits = benefits[benefits['id'].isin(ID_set)]
    #convert the dates to datetime
    benefits['alkamispvm'] = pd.to_datetime(benefits['alkamispvm'])
    benefits['paattymispvm'] = pd.to_datetime(benefits['paattymispvm'])
    #Note that the dataframe 'data' has already been initialized, so depending on the
    #value of params['ByYear'], it either contains one entry per ID, or one entry per ID
    #per year.
    data['received_unemployment_allowance'] = [0 for i in range(len(data))]
    data['received_study_allowance'] = [0 for i in range(len(data))]
    data['received_sickness_allowance'] = [0 for i in range(len(data))]
    data['received_basic_unemployment_allowance'] = [0 for i in range(len(data))]
    data['received_maternity_paternity_parental_allowance'] = [0 for i in range(len(data))]
    data['received_other_allowance'] = [0 for i in range(len(data))]

    if params['OutputAge']=='T':
        data['received_unemployment_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        data['received_study_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        data['received_sickness_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        data['received_basic_unemployment_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        data['received_maternity_paternity_parental_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        data['received_other_allowance_OnsetAge'] = [np.nan for i in range(len(data))]
        
        
    for index,row in benefits.iterrows():
        ID = row['id']
        b_start = row['alkamispvm'] #start date of allowance
        b_end = row['paattymispvm'] #end date of allowance
        fu_end = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['end_of_followup']
        fu_start = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['start_of_followup']
        #if the benefit period is outside the follow-up for this ID, skip
        if b_end<fu_start or b_start>fu_end: continue
        #get the type of social benefit
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

        if b_start<fu_start: b_start = fu_start
        if b_end>fu_end: b_end = fu_end
        
        if params['ByYear']=='F':
            ind = data.index[data['FINREGISTRYID']==ID][0]
            #update the values
            data.loc[ind,benefit_var] = 1
            #and the onset ages if requested
            if params['OutputAge']=='T':
                dob = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
                OnsetAge = getOnsetAge(dob,b_start)
                if np.isnan(data.iloc[ind][benefit_var+'_OnsetAge']): data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
                elif data.iloc[ind][benefit_var+'_OnsetAge']>OnsetAge: data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
            
        elif params['ByYear']=='T':
            for year in range(b_start.year,b_end.year+1):
                ind = data.index[(data['FINREGISTRYID']==ID) & (data['year']==year)][0]
                #update the values
                data.loc[ind,benefit_var] = 1
                #and the onset ages if requested
                if params['OutputAge']=='T':
                    dob = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
                    if year==b_start.year: onset_date = b_start
                    else: onset_date = datetime(year,1,1)
                    OnsetAge = getOnsetAge(dob,onset_date)
                    if np.isnan(data.iloc[ind][benefit_var+'_OnsetAge']): data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
                    elif data.iloc[ind][benefit_var+'_OnsetAge']>OnsetAge: data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
    end = time()
    print('Benefits data read in in '+str(end-start)+" s")
    return data
