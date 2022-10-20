#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define nSampleBin 720
#define MaxSamplePerBin 10000
#define MaxFeature 5000
#define MaxEventTimeLength 20000
#define FeatureLen 100
#define IDandTimeLen 15

char buffer[100000];
char InLongFile[10000];
char OutFile[10000];
char SampleListFile[10000];
char FeatureListFile[10000];
const char *NoVal = "NA";
int CutOffMode; // 0 -- age cutoff, 1 -- year cutoff, default age
int ByYear; // 0 -- no, 1 -- yes, default no
int EventMode; // 0 -- binary, 1 -- number of events, 2 -- list of event date, 3 -- list of event age, default binary
int WithAge; // 0 -- no, 1 -- yes, default no
int SampleIncFlag, RecordIncFlag; // Inclusion flags

int iFeature;
int iSample[2];
int * SampleFeature;
double * SampleOnsetAge;
char * SampleEventTime[MaxFeature];

struct SampleInfo {
   char FINREGISTRYID[IDandTimeLen];
   time_t DateOfBirth;
   double lower;
   double upper; // upper and lower bound for age/year cutoff
};  
typedef struct SampleInfo Sample;
Sample SampleList[nSampleBin][MaxSamplePerBin];
char *FeatureList[MaxFeature];
int nFeature;
long int nSample;

static int StrComp(const void* Item1, const void* Item2) {
    return strcmp(*(char **)Item1, *(char **)Item2);
}


// lol annoying C time stuff
time_t MakeTime(char Date[IDandTimeLen]) {
	int year, month, day;
	struct tm OutTime = {0};
    char s = strptime(Date, "%Y-%m-%d", &OutTime);
    if (&s == NULL) { 
        printf("Invalid date input %s.\n", Date); 
        exit(0);
    }
    return(mktime(&OutTime));
}


double TimeDiffYear(time_t Time1, time_t Time2) {
	// for function difftime(Time2, Time1), Time1 is the starting time
	return(difftime(Time2, Time1)/(60*60*24*365.25));
}


char *YearDiffToDate(time_t Time1, double YearDiff) {
	time_t Time2 = Time1 + (60*60*24*365.25)*YearDiff;
	struct tm *OutTime = gmtime(&Time2);
	static char OutDate[IDandTimeLen];
	sprintf(OutDate, "%d-%d-%d", OutTime->tm_year + 1900, OutTime->tm_mon, OutTime->tm_mday);
	return(OutDate);
}


void ReadParam(const char *ParamFile) {
	CutOffMode = 0;
	ByYear = 0;
	EventMode = 0;
	WithAge = 0;
	FILE *Param;
	char *tok; char *p;
	Param = fopen(ParamFile, "r");
	
	if (Param == NULL) {
	    printf("Cannot open parameter file.\n");
	    exit(0);
	}
	else {
		while (fgets(buffer, sizeof(buffer), Param) != NULL) {
			p = buffer;
			tok = strtok_r(p, " \t", &p);
			if (tok != NULL) {
				if (strcmp(tok, "LongEndPtFile") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					strcpy(InLongFile, tok);
				}
				else if (strcmp(tok, "SampleFile") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					strcpy(SampleListFile, tok);
				}
				else if (strcmp(tok, "FeatureFile") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					strcpy(FeatureListFile, tok);
				}
				else if (strcmp(tok, "OutputFile") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					strcpy(OutFile, tok);
				}
				else if (strcmp(tok, "Cutoff") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "Age") == 0 || strcmp(tok, "age") == 0)
						CutOffMode = 0;
					else if (strcmp(tok, "Date") == 0 || strcmp(tok, "year") == 0 || strcmp(tok, "Year") == 0)
						CutOffMode = 1;
					else
						printf("Cutoff: Age/Year/Date. Using default age cutoff.\n");
				}
				else if (strcmp(tok, "ByYear") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						ByYear = 1;
					else if (strcmp(tok, "F") == 0)
						ByYear = 0;
					else
						printf("ByYear: T/F. Using default false.\n");
				}
				else if (strcmp(tok, "EventMode") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "Binary") == 0 || strcmp(tok, "binary") == 0)
						EventMode = 0;
					else if (strcmp(tok, "nEvent") == 0)
						EventMode = 1;
					else if (strcmp(tok, "EventDate") == 0)
						EventMode = 2;
					else if (strcmp(tok, "EventAge") == 0)
						EventMode = 3;
					else
						printf("EventMode: Binary/nEvent/EventDate/EventAge. Using default true.\n");
				}
				else if (strcmp(tok, "OutputAge") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						WithAge = 1;
					else if (strcmp(tok, "F") == 0)
						WithAge = 0;
					else
						printf("OutputAge: T/F. Using default false.\n");
				}
	    	}
		}
	}
	fclose(Param);
	printf("EventMode = %d, ByYear = %d, WithAge = %d\n", EventMode, ByYear, WithAge);
	fflush(stdout);
} // read parameter file


void ReadList() {
	char *tok; char *p;
	char tmpDOB[IDandTimeLen];
	long int i;
	
	FILE *Sample;
	long int ID;
	int bin, index;
	Sample = fopen(SampleListFile,"r");
	if (Sample == NULL) {
	    printf("Cannot open sample file.\n");
	    exit(0);
	}
	else {
		i = 0;
		while (fgets(buffer, sizeof(buffer), Sample) != NULL) {
			p = buffer;
			tok = strtok_r(p, " ,\t\n", &p);
			ID = atoi(tok + 2);
			bin = (int)floor(ID/MaxSamplePerBin);
			index = ID % MaxSamplePerBin;
			strcpy(SampleList[bin][index].FINREGISTRYID, tok);
			tok = strtok_r(p, " ,\t\n", &p);
			strcpy(tmpDOB, tok);
			SampleList[bin][index].DateOfBirth = MakeTime(tmpDOB);
			
			if (CutOffMode) {
				tok = strtok_r(p, " ,\t\n", &p);
				strcpy(tmpDOB, tok);
				SampleList[bin][index].lower = TimeDiffYear(SampleList[bin][index].DateOfBirth, MakeTime(tmpDOB));
				tok = strtok_r(p, " ,\t\n", &p);
				strcpy(tmpDOB, tok);
				SampleList[bin][index].upper = TimeDiffYear(SampleList[bin][index].DateOfBirth, MakeTime(tmpDOB));
			}
			else {
				tok = strtok_r(p, " ,\t\n", &p);
				SampleList[bin][index].lower = atof(tok);
				tok = strtok_r(p, " ,\t\n", &p);
				SampleList[bin][index].upper = atof(tok);
			}			
			i += 1;
		}
	}
	nSample = i;
	printf("Loading sample list, done. Including %ld samples.\n", nSample);
	fflush(stdout);
	fclose(Sample);

	FILE *Feature;
	Feature = fopen(FeatureListFile,"r");
	if (Feature == NULL) {
	    printf("Cannot open feature file.\n");
	    exit(0);
	}
	else {
		i = 0;
		while (fgets(buffer, sizeof(buffer), Feature) != NULL) {
			p = buffer;
			tok = strtok_r(p, " ,\t\n", &p);
			FeatureList[i] = malloc(sizeof(char) * FeatureLen);
			strcpy(FeatureList[i], tok);
			i += 1;
		}
	}
	nFeature = i;
	fclose(Feature);
	qsort(FeatureList, nFeature, sizeof(char *), StrComp);
	printf("Loading feature list, done. Including %d features.\n", nFeature);
	fflush(stdout);
} // read sample list and feature list 


int SampleIsIn(char FinRegID[IDandTimeLen]) {
	long int ID;
	int bin, index;
	ID = atoi(FinRegID + 2);
	bin = (int)floor(ID/MaxSamplePerBin);
	index = ID % MaxSamplePerBin;
	if (strcmp(FinRegID, SampleList[bin][index].FINREGISTRYID) == 0) {
		iSample[0] = bin;
		iSample[1] = index;
		return(1);
	}
	else {
		memset(iSample, -1, sizeof(int) * 2);
		return(0);
	}
} // check if sample is included, return 1 if is


int FeatureIsIn(char Feature[FeatureLen]) {
	int l = 0;
	int m;
	int r = nFeature - 1;
	int CompOut;
	while(l <= r) {
		m = (l + r)/2;
		CompOut = strcmp(FeatureList[m], Feature);
		if (CompOut == 0)
	    	return (m);
		else if (CompOut > 0)
			r    = m - 1;
		else if (CompOut < 0)
			l = m + 1;
    }
    return(-1);
}

int Include(double tmpAge, double lower, double upper) {
	return( ((tmpAge >= lower) && (tmpAge <= upper)) ? 1 : 0);
}


void ResetRecordInfo() {
	int k;
	if (!EventMode || EventMode == 1) 
		memset(SampleFeature, 0, sizeof(int) * nFeature);
	if (EventMode == 2 || EventMode == 3)
		for (k = 0; k < nFeature; k++)
			memset(SampleEventTime[k], '\0', sizeof(char) * MaxEventTimeLength);
	if (WithAge == 1)
		memset(SampleOnsetAge, 0.0, sizeof(double) * nFeature);
	RecordIncFlag = 0;
}


void UpdateRecordInfo(int iFeature, double tmpAge, time_t SampleDOB) {
	if (!EventMode || EventMode == 1) {
		if ( (WithAge == 1) && (SampleFeature[iFeature] == 0) )
			SampleOnsetAge[iFeature] = tmpAge;
		SampleFeature[iFeature] += 1;
	}
	else if (EventMode == 2) {
		if (WithAge &&  SampleEventTime[iFeature][0] == '\0')
			SampleOnsetAge[iFeature] = tmpAge;
		char EventTime[IDandTimeLen];
		sprintf(EventTime, "%s;", YearDiffToDate(SampleDOB, tmpAge));
		strcat(SampleEventTime[iFeature], EventTime);
	}
	else if (EventMode == 3) {
		if ( (WithAge == 1) &&  SampleEventTime[iFeature][0] == '\0')
			SampleOnsetAge[iFeature] = tmpAge;
		char EventTime[IDandTimeLen];
		sprintf(EventTime, "%0.4f;", tmpAge);
		strcat(SampleEventTime[iFeature], EventTime);
	}
	RecordIncFlag = 1;
}


void WriteOutput(char SampleID[IDandTimeLen], int SampleYear) {
	int k;
	FILE *OutPut;
	OutPut = fopen(OutFile, "a");

	if (ByYear == 1) 
		fprintf(OutPut, "%s\t%d\t", SampleID, SampleYear);
	else 
		fprintf(OutPut, "%s\t", SampleID);

	if (!EventMode || EventMode == 1) {
		if (!EventMode)
			for (k = 0; k < nFeature; k++) 
				SampleFeature[k] = (SampleFeature[k] ? 1 : 0);
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%d\t", SampleFeature[k]);
		if (WithAge == 1) {
			fprintf(OutPut, "%d\t", SampleFeature[nFeature-1]);
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%lf\t", SampleOnsetAge[k]);
			fprintf(OutPut, "%lf\n", SampleOnsetAge[nFeature-1]);
		}
		else
			fprintf(OutPut, "%d\n", SampleFeature[nFeature-1]);
	}
	if (EventMode == 2 || EventMode == 3) {
		for (k = 0; k < nFeature; k++) 
			if (SampleEventTime[k][0] == '\0')
				strcpy(SampleEventTime[k], NoVal);
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%s\t", SampleEventTime[k]);
		if (WithAge == 1) {
			fprintf(OutPut, "%s\t", SampleEventTime[nFeature-1]);
			for (k = 0; k < nFeature-1; k++)
				fprintf(OutPut, "%lf\t", SampleOnsetAge[k]);
			fprintf(OutPut, "%lf\n", SampleOnsetAge[nFeature-1]);
		}
		else
			fprintf(OutPut, "%s\n", SampleEventTime[nFeature-1]);
	}
	fclose(OutPut);
}


int main(int argc, char const *argv[]) {
	int nID = -1; char tmpID[IDandTimeLen]; char SampleID[IDandTimeLen];
	int nAge = -1; double tmpAge = 0; double SampleAge = 0;
	int nYear = -1; int tmpYear = 0; int SampleYear = 0;
	int nEndPt = -1; char tmpEndPt[FeatureLen]; char SampleEndPt[FeatureLen];
	time_t SampleDOB;
	double SampleLower, SampleUpper;
	int i, j, k; //i -- column counter, j -- event counter, k -- feature counter
	char *tok; char *p;
	long int rCnt;

	ReadParam(argv[1]);
	printf("Read parameters, done\n");
	fflush(stdout);
	ReadList();

	if (!EventMode || EventMode == 1) {
		SampleFeature = malloc(sizeof(int) * nFeature);
		if (SampleFeature == NULL)
			printf("SampleFeature memory allocation failed.\n");
	}
	if (EventMode == 2 || EventMode == 3)
		for (k = 0; k < nFeature; k++) {
			SampleEventTime[k] = malloc(sizeof(char) * MaxEventTimeLength);
			if (SampleEventTime[k] == NULL)
				printf("SampleEventTime[%d] memory allocation failed.\n", k);
		}
	if (WithAge == 1) {
		SampleOnsetAge = malloc(sizeof(double) * nFeature);
		if (SampleOnsetAge == NULL)
			printf("SampleOnsetAge memory allocation failed.\n");
	}
	ResetRecordInfo();
	SampleIncFlag = 0;

	FILE *OutPut;
	OutPut = fopen(OutFile, "w");
	if (OutPut == NULL) {
        printf("Cannot open output file.\n");
        exit(0);
    }
    if (ByYear == 1)
		fprintf(OutPut, "FINREGISTRYID\tYear\t");
	else 
		fprintf(OutPut, "FINREGISTRYID\t");

	for (k = 0; k < nFeature-1; k++) 
		fprintf(OutPut, "%s\t", FeatureList[k]);
	if (WithAge == 1) {
		fprintf(OutPut, "%s\t", FeatureList[nFeature-1]);
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%s_OnsetAge\t", FeatureList[k]);
		fprintf(OutPut, "%s_OnsetAge\n", FeatureList[nFeature-1]);
	}
	else
		fprintf(OutPut, "%s\n", FeatureList[nFeature-1]);
	fclose(OutPut);

	FILE *LongEndPt;
	LongEndPt = fopen(InLongFile,"r");
	if (LongEndPt == NULL) {
	    printf("Cannot open longitudinal file.\n");
	    exit(0);
	}
	else {
		fgets(buffer, sizeof(buffer), LongEndPt); // Read header
		rCnt = 1;

		p = buffer;
		i = 0;
		while (tok = strtok_r(p, " ,\t\n", &p)) {
			if (strcmp(tok, "FINREGISTRYID") == 0)
				nID = i;
			else if (strcmp(tok, "EVENT_AGE") == 0)
				nAge = i;
			else if (strcmp(tok, "EVENT_YEAR") == 0)
				nYear = i;
			else if (strcmp(tok, "ENDPOINT") == 0)
				nEndPt = i;
			i = i+1;
		}
		if ( (nID == -1) || (nEndPt == -1) ) {
			printf("Missing FINREGISTRYID or ENDPOINT column.\n");
			exit(0);
		}
		if ( nAge == -1 ) {
			printf("Missing EVENT_AGE column.\n");
			exit(0);
		}
		if ( ((CutOffMode == 1) || (ByYear == 1)) && (nYear == -1) ) {
			printf("Given year cutoff or requested output by year, but no EVENT_YEAR column.\n");
			exit(0);
		}
		while (fgets(buffer, sizeof(buffer), LongEndPt) != NULL) {
			p = buffer;
			i = 0;
			while (tok = strtok_r(p, " ,\t\n", &p)) {
				if (i == nID)
					strcpy(tmpID, tok);
				else if (i == nAge)
					tmpAge = atof(tok);					
				else if (i == nYear)
					tmpYear = atoi(tok);
				else if (i == nEndPt)
					strcpy(tmpEndPt, tok);
				i += 1;
			}

			if ( (strcmp(tmpID, SampleID) == 0) && (SampleIncFlag == 1) ) { // check if same as previous INCLUDED sample
				if ((tmpYear != SampleYear) && (ByYear == 1) && (RecordIncFlag == 1)) { // if output by year and the event year is different from existing record
					WriteOutput(SampleID, SampleYear); // write existing record if necessary
					ResetRecordInfo(); // starting new record
				}
				SampleYear = tmpYear;
				if ( Include(tmpAge, SampleLower, SampleUpper) == 1 ) { // check if to be considered given the event time
					iFeature = FeatureIsIn(tmpEndPt); // check if the endpoint is in the list
					if (iFeature != -1)  // update vector if feature is included, do nothing if not
						UpdateRecordInfo(iFeature, tmpAge, SampleDOB); // update the existing record with current observation
				} // do nothing if the event time is out of the window
			}

			else if (strcmp(tmpID, SampleID) != 0) { // if the observation is for different sample
				if ((RecordIncFlag == 1) && (SampleIncFlag == 1)) {
					WriteOutput(SampleID, SampleYear); // output existing record if necessary
					ResetRecordInfo(); // starting new record
				}
				strcpy(SampleID, tmpID);
				SampleYear = tmpYear;
				SampleIncFlag = SampleIsIn(SampleID);
				if (SampleIncFlag == 1) { // proceed only if the sample is to be included
					strcpy(SampleID, SampleList[iSample[0]][iSample[1]].FINREGISTRYID);
					SampleLower = SampleList[iSample[0]][iSample[1]].lower;
					SampleUpper = SampleList[iSample[0]][iSample[1]].upper;
					SampleDOB = SampleList[iSample[0]][iSample[1]].DateOfBirth;
					if ( Include(tmpAge, SampleLower, SampleUpper) == 1 ) { // check if to be considered given the event time
						iFeature = FeatureIsIn(tmpEndPt); // check if the endpoint is in the list
						if (iFeature != -1) // update vector if feature is included, do nothing if not
							UpdateRecordInfo(iFeature, tmpAge, SampleDOB); // update the existing record with current observation
					} // do nothing if onset time out of range
				} // do nothing if sample is not in the list
			} // do nothing if same sample as previous but not to be included
			rCnt += 1;
			if (rCnt % 10000000 == 0) {
				printf("Process %d0M records, done.\n", (int)(rCnt/10000000));
				fflush(stdout);
			}
		}
	}
	fclose(LongEndPt);
	if ((RecordIncFlag == 1) && (SampleIncFlag == 1))
		WriteOutput(SampleID, SampleYear);
}
