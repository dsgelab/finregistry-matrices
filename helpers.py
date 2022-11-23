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
    start = time()
    samples = pd.read_csv(params['SampleFile'])
    ID_set = set(list(samples['FINREGISTRYID']))
    #convert the date columns to datetime
    samples['start_of_followup'] = pd.to_datetime(samples['start_of_followup'])
    samples['end_of_followup'] = pd.to_datetime(samples['end_of_followup'])
    samples['date_of_birth'] = pd.to_datetime(samples['date_of_birth'])
    #Read in sex from minimal phenotype file
    mpf = pd.read_feather(params['MinimalPhenotypeFile'],columns=['FINREGISTRYID','sex'])
    mpf = mpf[mpf['FINREGISTRYID'].isin(ID_set)]
    #mpf['sex'] = mpf['sex'].astype('int') #This does not work for missing values...
    samples =  samples.merge(mpf,how='left',on='FINREGISTRYID')

    if params['ByYear']=='F': data = samples[['FINREGISTRYID','sex']]
    elif params['ByYear']=='T':
        data_ind_dict = {}
        data = pd.DataFrame()
        IDs = []
        years = []
        sexs = []
        #create one entry row per each year of follow-up for each individual
        ind = 0
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
                data_ind_dict[(row['FINREGISTRYID'],year)] = ind
                ind += 1
        data['FINREGISTRYID'] = IDs
        data['year'] = years
        #data['date_of_birth'] = dobs
        data['sex'] = sexs
        #data['start_of_followup'] = starts
        #data['end_of_followup'] = ends

    #create a dictionary mapping the ID+year pairs to indices of dataframe data
    features = pd.read_csv(params['FeatureFile'])
    if params['ByYear']=='F':
        data_ind_dict = dict(zip(list(data['FINREGISTRYID']),list(data.index)))
        end = time()
        print("Data structures initialized in "+str(end-start)+" s")
        return samples,features,data,ID_set,data_ind_dict,data_ind_dict
    elif params['ByYear']=='T':
        samples_ind_dict = dict(zip(list(samples['FINREGISTRYID']),list(samples.index)))
        end = time()
        print("Data structures initialized in "+str(end-start)+" s")
        return samples,features,data,ID_set,data_ind_dict,samples_ind_dict
    
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

def readPension(samples,data,params,cpi,requested_features,ID_set,data_ind_dict,samples_ind_dict):
    #Read in the variables from the pension registry
    #this function currently creates three variables, which are:
    #received_disability_pension = Received disability pension
    #received_pension = Received any pension
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
    total_income = [0.0 for i in range(len(data))]

    if params['OutputAge']=='T':
        received_disability_pension_OnsetAge = [np.nan for i in range(len(data))]
        received_pension_OnsetAge = [np.nan for i in range(len(data))]
        total_income_OnsetAge = [np.nan for i in range(len(data))]

    for p_indx,p_row in pension.iterrows():
        ID = p_row['id']
        fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']
        fu_start = samples.iloc[samples_ind_dict[ID]]['start_of_followup']
        dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']

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
            if params['ByYear']=='T': ind = data_ind_dict[(ID,year)]
            elif params['ByYear']=='F': ind = data_ind_dict[ID]

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
    if 'received_pension' in requested_features:
        data['received_pension'] = received_pension
        if params['OutputAge']=='T': data['received_pension_OnsetAge'] = received_pension_OnsetAge
    if 'received_disability_pension' in requested_features:
        data['received_disability_pension'] = received_disability_pension
        if params['OutputAge']=='T': data['received_disability_pension_OnsetAge'] = received_disability_pension_OnsetAge
    end = time()
    print("Pension data preprocessed in "+str(end-start)+" s")
    return data
                
def readPension_old(samples,data,params,cpi,requested_features,ID_set,data_ind_dict,samples_ind_dict):
    #Read in the variables from the pension registry
    #this function currently creates three variables, which are:
    #received_disability_pension = Received disability pension
    #received_pension = Received any pension
    #total_income = Sum of labor income, pension and social benefits, indexed
    start = time()
    keep_cols = ['id','apvm','ppvm','ptma','ltma','jkma','tksyy1']
    pension = pd.read_feather(params['PensionFile'],columns=keep_cols)
    #keep only rows corresponding to IDs in samples
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
                        if year not in cpi: C = cpi[1972]
                        else: C = cpi[year]
                        if not pd.isna(p_row['ptma']): tot_pension += C*12*p_row['ptma']
                        if not pd.isna(p_row['ltma']): tot_pension += C*12*p_row['ltma']
                        if not pd.isna(p_row['jkma']):tot_pension += C*12*p_row['jkma']
                    #correct the amount paid for first and last year
                    if p_start.year not in cpi: C = cpi[1972]
                    else: C = cpi[p_start.year]
                    if not pd.isna(p_row['ptma']): tot_pension -= C*(p_start.month-1)*p_row['ptma']
                    if not pd.isna(p_row['ltma']): tot_pension -= C*(p_start.month-1)*p_row['ltma']
                    if not pd.isna(p_row['jkma']): tot_pension -= C*(p_start.month-1)*p_row['jkma']

                    if p_end.year not in cpi: C = cpi[1972]
                    else: C = cpi[p_end.year]
                    
                    if not pd.isna(p_row['ptma']): tot_pension -= C*(12-p_end.month)*p_row['ptma']
                    if not pd.isna(p_row['ltma']): tot_pension -= C*(12-p_end.month)*p_row['ltma']
                    if not pd.isna(p_row['jkma']): tot_pension -= C*(12-p_end.month)*p_row['jkma']
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
            fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['end_of_followup']
            fu_start = samples.iloc[samples_ind_dict[ID]]['end_of_followup']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['start_of_followup']
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
                dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
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

                if year not in cpi: C = cpi[1972]
                else: C = cpi[year]
                
                if not pd.isna(p_row['ptma']): tot_pension += C*12*p_row['ptma']
                if not pd.isna(p_row['ltma']): tot_pension += C*12*p_row['ltma']
                if not pd.isna(p_row['jkma']): tot_pension += C*12*p_row['jkma']
                #get the correct row index in the dataframe data
                ind = data.iloc[data_ind_dict[(ID,year)]]#data.index[(data['FINREGISTRYID']==ID) & (data['year']==year)][0]
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

def readIncome(samples,data,params,requested_features,ID_set,data_ind_dict,samples_ind_dict):
    #Read in the variables from the pension registry
    #this function currently creates two variables, which are:
    #received_labor_income = Received labor income
    #total_income = Sum of labor income, pension and social benefits, indexed
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
        
        fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['end_of_followup']
        fu_start = samples.iloc[samples_ind_dict[ID]]['start_of_followup']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['start_of_followup']
        #if year is outside the follow-up for this ID, skip
        if year<fu_start.year or year>fu_end.year: continue
        income_value = row['vuosiansio_indexed']
        
        #update the values
        if params['ByYear']=='T': ind = data_ind_dict[(ID,year)]
        else: ind = data_ind_dict[ID]
        labor_income[ind] += income_value
        if income_value>0: received_labor_income[ind] = 1
        #and the onset ages if requested
        if params['OutputAge']=='T':
            dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']
            OnsetAge = getOnsetAge(dob,datetime(year,1,1))
            if np.isnan(received_labor_income_OnsetAge[ind]): received_labor_income_OnsetAge[ind] = OnsetAge
            elif received_labor_income_OnsetAge[ind]>OnsetAge: received_labor_income_OnsetAge[ind] = OnsetAge
    #Add the new columns to data
    data['total_income'] = data['total_income'].add(labor_income,axis='index')
    data['received_labor_income'] = received_labor_income
    if params['OutputAge']=='T': data['received_labor_income_OnsetAge'] = received_labor_income_OnsetAge

    end = time()
    print('Income data read in in '+str(end-start)+" s")
    return data

def readBenefits(samples,data,params,requested_features,ID_set,data_ind_dict,samples_ind_dict):
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

        fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']
        fu_start = samples.iloc[samples_ind_dict[ID]]['start_of_followup']
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
            ind = data_ind_dict[ID]
            #update the values
            new_cols[benefit_var][ind] = 1
            #and the onset ages if requested
            if params['OutputAge']=='T':
                dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']
                OnsetAge = getOnsetAge(dob,b_start)
                if np.isnan(new_cols[benefit_var+'_OnsetAge'][ind]): new_cols[benefit_var+'_OnsetAge'][ind] = OnsetAge
                elif new_cols[benefit_var+'_OnsetAge'][ind]>OnsetAge: new_cols[benefit_var+'_OnsetAge'][ind] = OnsetAge
            
        elif params['ByYear']=='T':
            for year in range(b_start.year,b_end.year+1):
                ind = data_ind_dict[(ID,year)]
                #update the values
                new_cols[benefit_var][ind] = 1
                #and the onset ages if requested
                if params['OutputAge']=='T':
                    dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']
                    if year==b_start.year: onset_date = b_start
                    else: onset_date = datetime(year,1,1)
                    OnsetAge = getOnsetAge(dob,onset_date)
                    if np.isnan(data.iloc[ind][benefit_var+'_OnsetAge']): data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
                    elif data.iloc[ind][benefit_var+'_OnsetAge']>OnsetAge: data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge

    #add the new columns
    for key in new_cols:
        if key in requested_features:
            data[key] = new_cols[key]
            if params['OutputAge']=='T': data[key+'_OnsetAge'] = new_cols[key+'_OnsetAge']
    end = time()
    print('Benefits data read in in '+str(end-start)+" s")
    return data


def readBenefits_old(samples,data,params,requested_features,ID_set,data_ind_dict,samples_ind_dict):
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

        fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['end_of_followup']
        fu_start = samples.iloc[samples_ind_dict[ID]]['start_of_followup']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['start_of_followup']
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
            ind = data_ind_dict[ID]#data.index[data['FINREGISTRYID']==ID][0]
            #update the values
            data.loc[ind,benefit_var] = 1
            #and the onset ages if requested
            if params['OutputAge']=='T':
                dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
                OnsetAge = getOnsetAge(dob,b_start)
                if np.isnan(data.iloc[ind][benefit_var+'_OnsetAge']): data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
                elif data.iloc[ind][benefit_var+'_OnsetAge']>OnsetAge: data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
            
        elif params['ByYear']=='T':
            for year in range(b_start.year,b_end.year+1):
                ind = data_ind_dict[(ID,year)]#data.index[(data['FINREGISTRYID']==ID) & (data['year']==year)][0]
                #update the values
                data.loc[ind,benefit_var] = 1
                #and the onset ages if requested
                if params['OutputAge']=='T':
                    dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']#samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
                    if year==b_start.year: onset_date = b_start
                    else: onset_date = datetime(year,1,1)
                    OnsetAge = getOnsetAge(dob,onset_date)
                    if np.isnan(data.iloc[ind][benefit_var+'_OnsetAge']): data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
                    elif data.iloc[ind][benefit_var+'_OnsetAge']>OnsetAge: data.loc[ind,benefit_var+'_OnsetAge'] = OnsetAge
    end = time()
    print('Benefits data read in in '+str(end-start)+" s")
    return data

def readSocialAssistance(samples,data,params,cpi,requested_features,ID_set,data_ind_dict,samples_ind_dict):
    #Read in the variables from the social assistance registry
    #this function currently creates two variables, which are:
    #received_any_income_support = Received basic, actual, preventive or complementary income support
    #total_income = Sum of labor income, pension and social benefits, indexed
    
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
        fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']
        fu_start = samples.iloc[samples_ind_dict[ID]]['start_of_followup']
        #if year is outside the follow-up for this ID, skip
        if year<fu_start.year or year>fu_end.year: continue

        if year not in cpi: C = cpi[1972]
        else: C = cpi[year]
        
        income_value = row['tot_income_support']*C #multiply with the consumer price index
        if params['ByYear']=='T': ind = data_ind_dict[(ID,year)]
        else: ind = data_ind_dict[ID]
        #update the values
        support_income[ind] += income_value
        if income_value>0: received_any_income_support[ind] = 1
        #and the onset ages if requested
        if params['OutputAge']=='T':
            dob = samples.loc[samples['FINREGISTRYID']==ID].iloc[0]['date_of_birth']
            OnsetAge = getOnsetAge(dob,datetime(year,1,1))
            if np.isnan(received_any_income_support_OnsetAge[ind]): received_any_income_support_OnsetAge[ind] = OnsetAge
            elif received_any_income_support_OnsetAge[ind]>OnsetAge: received_any_income_support_OnsetAge[ind] = OnsetAge

    #add the newly preprocessed values to data
    data['total_income'] = data['total_income'].add(support_income,axis='index')
    data['received_any_income_support'] = received_any_income_support
    if params['OutputAge']=='T': data['received_any_income_support_OnsetAge'] = received_any_income_support_OnsetAge
    
    end = time()
    print('Social assistance data read in in '+str(end-start)+" s")
    return data

def readMaritalStatus(samples,data,params,cpi,requested_features,ID_set,data_ind_dict,samples_ind_dict):
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

        fu_end = samples.iloc[samples_ind_dict[ID]]['end_of_followup']
        fu_start = samples.iloc[samples_ind_dict[ID]]['start_of_followup']
        #if the marriage period is completely outside the follow-up for this ID, skip
        if m_end<fu_start or m_start>fu_end: continue
        #get the current marital status
        m_status = int(row['Current_marital_status'])
        marriage_date = m_start
        if m_status==4 or m_status==7: divorce_date = m_end
        else: divorce_date = None

        if m_start<fu_start: m_start = fu_start
        if m_end>fu_end: m_end = fu_end
        
        if params['ByYear']=='F':
            ind = data_ind_dict[ID]
            #update the values
            #note that if a person has divorced, they must have been married or in a
            #registered partnership
            married[ind] = 1
            if divorce_date is not None:
                #only count the divorce if it happens inside the follow-up period
                if divorce_date<=m_end: divorced[ind] = 1
            #and the onset ages if requested
            if params['OutputAge']=='T':
                dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']
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

            if m_start==marriage_date:
                m_ind = data_ind_dict[(ID,marriage_date.year)]
                #update the values
                #note that if a person has divorced, they must have been married or in a
                #registered partnership
                married[m_ind] = 1
                #if divorce_date is not None:
                if divorce_date==m_end:
                    d_ind = data_ind_dict[(ID,divorce_date.year)]
                    divorced[d_ind] = 1
                #and the onset ages if requested
                if params['OutputAge']=='T':
                    dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']
                    OnsetAge = getOnsetAge(dob,marriage_date)
                    if np.isnan(married_OnsetAge[m_ind]): married_OnsetAge[m_ind] = OnsetAge
                    elif married_OnsetAge[m_ind]>OnsetAge: married_OnsetAge[m_ind] = OnsetAge
                    if divorce_date is not None:
                        #only count the divorce if it happens this year
                        if divorce_date==m_end:
                            OnsetAge = getOnsetAge(dob,divorce_date)
                            if np.isnan(divorced_OnsetAge[d_ind]): divorced_OnsetAge[d_ind] = OnsetAge
                            elif divorced_OnsetAge[d_ind]>OnsetAge: divorced_OnsetAge[d_ind] = OnsetAge
                

            
            #for year in [m_start.year,m_end.year]:
            #    if np.isnan(year): continue
            #    ind = data_ind_dict[(ID,year)]
            #    #update the values
            #    #note that if a person has divorced, they must have been married or in a
            #    #registered partnership
            #    if year==marriage_date.year: married[ind] = 1
            #    if divorce_date is not None:
            #        if divorce_date.year==year: divorced[ind] = 1
            #    #and the onset ages if requested
            #    if params['OutputAge']=='T':
            #        dob = samples.iloc[samples_ind_dict[ID]]['date_of_birth']
            #        if year==marriage_date.year:
            #            OnsetAge = getOnsetAge(dob,marriage_date)
            #            if np.isnan(married_OnsetAge[ind]): married_OnsetAge[ind] = OnsetAge
            #            elif married_OnsetAge[ind]>OnsetAge: married_OnsetAge = OnsetAge
            #        if divorce_date is not None:
            #            #only count the divorce if it happens this year
            #            if divorce_date.year==year:
            #                OnsetAge = getOnsetAge(dob,divorce_date)
            #                if np.isnan(divorced_OnsetAge[ind]): divorced_OnsetAge[ind] = OnsetAge
            #                elif divorced_OnsetAge[ind]>OnsetAge: divorced_OnsetAge[ind] = OnsetAge
                        
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
    
