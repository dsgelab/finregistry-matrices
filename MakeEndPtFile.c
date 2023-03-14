#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define nSampleBin 720
#define MaxSamplePerBin 10000
#define MaxFeature 5000
#define FeatureLen 100
#define IDandTimeLen 15
#define MaxRec 20 // allow same individual having multiple record, with different time period

char buffer[100000];
char InLongFile[10000];
char OutFile[10000];
char SampleListFile[10000];
char FeatureListFile[10000];
int ByYear; // 0 -- no, 1 -- yes, default no
int WithBinary;
int WithNEvent;
int WithAge; // 0 -- no, 1 -- yes, default no
int Pad; // 0 -- no, 1 -- yes, default no
int SampleIncFlag, RecordIncFlag; // Inclusion flags
int iFeature;
int iSample[2];
int * SampleFeature[MaxRec];
double * SampleOnsetAge[MaxRec];
char * SampleEventTime[MaxFeature];

struct SampleInfo {
   char FINREGISTRYID[IDandTimeLen];
   time_t DateOfBirth;
   double lower[MaxRec];
   double upper[MaxRec]; // upper and lower bound for age/year cutoff
   int nRec;
} NullSample = {.nRec = 0};
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
	return(difftime(Time2, Time1)/(60*60*24*365.25));
}


char *YearDiffToDate(time_t Time1, double YearDiff) {
	time_t Time2 = Time1 + (60*60*24*365.25)*YearDiff;
	struct tm *OutTime = gmtime(&Time2);
	static char OutDate[IDandTimeLen];
	static char Year[IDandTimeLen];
	static char Month[IDandTimeLen];
	static char Day[IDandTimeLen];
	sprintf(Year, "%d", OutTime->tm_year + 1900);
	if ((OutTime->tm_mon) + 1 >= 10)
		sprintf(Month, "%d", (OutTime->tm_mon) + 1);
	else
		sprintf(Month, "0%d", (OutTime->tm_mon) + 1);

	if (OutTime->tm_mday >= 10)
		sprintf(Day, "%d", OutTime->tm_mday);
	else
		sprintf(Day, "0%d", OutTime->tm_mday);

	// sprintf(OutDate, "%d-%d-%d", OutTime->tm_year + 1900, (OutTime->tm_mon) + 1, OutTime->tm_mday);
	sprintf(OutDate, "%s-%s-%s", Year, Month, Day);
	return(OutDate);
}


void ReadParam(const char *ParamFile) {
	ByYear = 0;
	Pad = 0;
	WithAge = 0;
	WithBinary = 0;
	WithNEvent = 0;
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
				else if (strcmp(tok, "EndPtList") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					strcpy(FeatureListFile, tok);
				}
				else if (strcmp(tok, "OutputPrefix") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					strcpy(OutFile, tok);
					strcat(OutFile, ".EndPt");
				}
				else if (strcmp(tok, "EndPtByYear") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						ByYear = 1;
					else if (strcmp(tok, "F") == 0)
						ByYear = 0;
					else
						printf("EndPtByYear: T/F. Using default false.\n");
				}
				else if (strcmp(tok, "EndPtOutputBinary") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						WithBinary = 1;
					else if (strcmp(tok, "F") == 0)
						WithBinary = 0;
					else
						printf("EndPtOutputBinary: T/F. Using default false.\n");
				}
				else if (strcmp(tok, "EndPtOutputEventCount") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						WithNEvent = 1;
					else if (strcmp(tok, "F") == 0)
						WithNEvent = 0;
					else
						printf("EndPtOutputEventCount: T/F. Using default false.\n");
				}
				else if (strcmp(tok, "EndPtOutputAge") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						WithAge = 1;
					else if (strcmp(tok, "F") == 0)
						WithAge = 0;
					else
						printf("EndPtOutputAge: T/F. Using default false.\n");
				}
				else if (strcmp(tok, "PadNoEvent") == 0) {
					tok = strtok_r(p, " \t\n", &p);
					if (strcmp(tok, "T") == 0)
						Pad = 1;
					else if (strcmp(tok, "F") == 0)
						Pad = 0;
					else
						printf("PadNoEvent: T/F. Only possible with EndPtByYear = F. Using default false.\n");
				}
	    	}
		}
	}
	fclose(Param);
	if (WithAge + WithNEvent + WithBinary == 0) {
		printf("No output required. Program terminates.\n");
		fflush(stdout);
		exit(0);
	}
	if ((ByYear == 1) && (Pad == 1)) {
		printf("Padding only possible without output by year. Disabled.\n");
		Pad = 0;
	}
} // read parameter file

void ReadList() {
	char *tok; char *p;
	char tmpDOB[IDandTimeLen];
	long int i; int j, k;
	double tmpLower; double tmpUpper;
	
	FILE *Sample;
	long int ID;
	int bin, index;
	Sample = fopen(SampleListFile,"r");
	if (Sample == NULL) {
	    printf("Cannot open sample file.\n");
	    exit(0);
	}
	else {
		fgets(buffer, sizeof(buffer), Sample);
		i = 0;
		while (fgets(buffer, sizeof(buffer), Sample) != NULL) {
			p = buffer;
			tok = strtok_r(p, " ,\t\n", &p);
			ID = atoi(tok + 2);
			bin = (int)floor(ID/MaxSamplePerBin);
			index = ID % MaxSamplePerBin;		
			if (!SampleList[bin][index].nRec) {
				strcpy(SampleList[bin][index].FINREGISTRYID, tok);
			}
			tok = strtok_r(p, " ,\t\n", &p);
			strcpy(tmpDOB, tok);
			if (!SampleList[bin][index].nRec) {
				SampleList[bin][index].DateOfBirth = MakeTime(tmpDOB);
				if (SampleList[bin][index].DateOfBirth != MakeTime(tmpDOB))
					printf("Different date of birth for %s, using the last one.\n", SampleList[bin][index].FINREGISTRYID);
			}
			tok = strtok_r(p, " ,\t\n", &p);
			strcpy(tmpDOB, tok);
			tmpLower = TimeDiffYear(SampleList[bin][index].DateOfBirth, MakeTime(tmpDOB));
			k = 0;
			while (tmpLower>SampleList[bin][index].lower[k] && k<SampleList[bin][index].nRec)
				k++;
			tok = strtok_r(p, " ,\t\n", &p);
			strcpy(tmpDOB, tok);
			tmpUpper = TimeDiffYear(SampleList[bin][index].DateOfBirth, MakeTime(tmpDOB));
			while (tmpLower==SampleList[bin][index].lower[k] && tmpUpper>SampleList[bin][index].upper[k] && k<SampleList[bin][index].nRec)
				k++;
			for (j = SampleList[bin][index].nRec; j >= k; j--) {
				SampleList[bin][index].lower[j+1] = SampleList[bin][index].lower[j];
				SampleList[bin][index].upper[j+1] = SampleList[bin][index].upper[j];
			}
			SampleList[bin][index].lower[k] = tmpLower;
			SampleList[bin][index].upper[k] = tmpUpper;	
			if (SampleList[bin][index].nRec <= MaxRec)
				SampleList[bin][index].nRec += 1;
			else {
				printf("Increase MaxRes per sample!\n");
				exit(0);
			}
			i += 1;
		}
	}
	nSample = i;
	printf("Loading sample list, done. Including %ld records.\n", nSample);
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


int SampleIsIn(long int ID) {
	char FinRegID[15];
	int bin, index;
	bin = (int)floor(ID/MaxSamplePerBin);
	index = ID % MaxSamplePerBin;
	if (ID == atoi(SampleList[bin][index].FINREGISTRYID + 2)) {
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
	for (k = 0; k < MaxRec; k ++) {
		memset(SampleFeature[k], 0, sizeof(int) * nFeature);
		if (WithAge == 1)
			memset(SampleOnsetAge[k], 0.0, sizeof(double) * nFeature);
	}
	RecordIncFlag = 0;
}


void UpdateRecordInfo(int m, int iFeature, double tmpAge, time_t SampleDOB) {
	if ( (WithAge == 1) && (SampleFeature[m][iFeature] == 0) )
		SampleOnsetAge[m][iFeature] = tmpAge;
	SampleFeature[m][iFeature] += 1;
	RecordIncFlag = 1;
}


void WriteOutput(long int bin, long int index, int SampleYear) {
	int i, k, nRec;
	char SampleID[IDandTimeLen];
	char DateLower[IDandTimeLen];
	char DateUpper[IDandTimeLen];
	char DateDoB[IDandTimeLen];
	time_t SampleDOB;

	double lower; double upper;
	FILE *OutPut;
	OutPut = fopen(OutFile, "a");

	strcpy(SampleID, SampleList[bin][index].FINREGISTRYID);
	SampleDOB = SampleList[bin][index].DateOfBirth;
	sprintf(DateDoB, "%s", YearDiffToDate(SampleDOB, 0.0));
	nRec = SampleList[bin][index].nRec;

	for (i = 0; i < nRec; i++) {
		lower = SampleList[bin][index].lower[i];
		sprintf(DateLower, "%s", YearDiffToDate(SampleDOB, lower));
		upper = SampleList[bin][index].upper[i];
		sprintf(DateUpper, "%s", YearDiffToDate(SampleDOB, upper));

		if (ByYear == 1) 
			fprintf(OutPut, "%s,%s,%s,%s,%d,", SampleID, DateDoB, DateLower, DateUpper, SampleYear);
		else 
			fprintf(OutPut, "%s,%s,%s,%s,", SampleID, DateDoB, DateLower, DateUpper);

		if (WithBinary + WithNEvent == 1) {
			if ((WithBinary == 1) && (WithNEvent == 0)) {
				for (k = 0; k < nFeature; k++) 
					SampleFeature[i][k] = (SampleFeature[i][k] > 0.0 ? 1 : 0);
			}
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%d,", SampleFeature[i][k]);
			if (WithAge == 1) {
				fprintf(OutPut, "%d,", SampleFeature[i][nFeature-1]);
				for (k = 0; k < nFeature-1; k++) 
					fprintf(OutPut, "%.2f,", ((SampleFeature[i][k] > 0.0) ? SampleOnsetAge[i][k] : -9.0));
				fprintf(OutPut, "%.2f\n", ((SampleFeature[i][nFeature-1] > 0.0) ? SampleOnsetAge[i][nFeature-1] : -9.0));
			}
			else
				fprintf(OutPut, "%d\n", SampleFeature[i][nFeature-1]);
		}
		else if ((WithBinary == 1) && (WithNEvent == 1)) {
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%d,%d,", SampleFeature[i][k], (SampleFeature[i][k] > 0.0 ? 1 : 0));
			if (WithAge == 1) {
				fprintf(OutPut, "%d,%d,", SampleFeature[i][nFeature-1], (SampleFeature[i][nFeature-1] > 0.0 ? 1 : 0));
				for (k = 0; k < nFeature-1; k++) 
					fprintf(OutPut, "%.2f,", ((SampleFeature[i][k] > 0.0) ? SampleOnsetAge[i][k] : -9.0));
				fprintf(OutPut, "%.2f\n", ((SampleFeature[i][nFeature-1] > 0.0) ? SampleOnsetAge[i][nFeature-1] : -9.0));
			}
			else
				fprintf(OutPut, "%d,%d\n", SampleFeature[i][nFeature-1], (SampleFeature[i][nFeature-1] > 0.0 ? 1 : 0));
		}
		else if ((WithBinary + WithNEvent == 0) && (WithAge == 1)) {
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%.2f,", ((SampleFeature[i][k] > 0.0) ? SampleOnsetAge[i][k] : -9.0));
			fprintf(OutPut, "%.2f\n", ((SampleFeature[i][nFeature-1] > 0.0) ? SampleOnsetAge[i][nFeature-1] : -9.0));
		}
	}
	fclose(OutPut);
}


int main(int argc, char const *argv[]) {
	int nID = -1; char tmpID[IDandTimeLen]; char SampleID[IDandTimeLen]; long int tmpIDcnt; 
	long int FinRegIDcnt; // char tmpID[IDandTimeLen];
	int nAge = -1; double tmpAge = 0; double SampleAge = 0;
	int nYear = -1; int tmpYear = 0; int SampleYear = 0;
	int nEndPt = -1; char tmpEndPt[FeatureLen]; char SampleEndPt[FeatureLen];
	time_t SampleDOB;
	double SampleLower, SampleUpper;
	int i, j, k; //i -- column counter, j -- event counter, k -- feature counter
	char *tok; char *p;
	long int rCnt;

	long int m,n;
	for (m = 0; m < nSampleBin; m++) {
		for (n = 0; n < MaxSamplePerBin; n++)
			SampleList[m][n] = NullSample;
	}

	ReadParam(argv[1]);
	printf("Read parameters, done\n");
	fflush(stdout);
	ReadList();

	for (m = 0; m < MaxRec; m++) {
		SampleFeature[m] = malloc(sizeof(int) * nFeature);
		if (SampleFeature[m] == NULL)
			printf("SampleFeature memory allocation failed.\n");
	}

	if (WithAge == 1) {
		for (m = 0; m < MaxRec; m++) {
			SampleOnsetAge[m] = malloc(sizeof(double) * nFeature);
			if (SampleOnsetAge[m] == NULL)
				printf("SampleOnsetAge memory allocation failed.\n");
		}
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
		fprintf(OutPut, "FINREGISTRYID,date_of_birth,start_of_followup,end_of_followup,Year,");
	else 
		fprintf(OutPut, "FINREGISTRYID,date_of_birth,start_of_followup,end_of_followup,");

	if ((WithBinary == 1) && (WithNEvent == 1)) {
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%s_nEvent,%s,", FeatureList[k], FeatureList[k]);
		if (WithAge == 1) {
			fprintf(OutPut, "%s_nEvent,%s,", FeatureList[nFeature-1], FeatureList[nFeature-1]);
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%s_OnsetAge,", FeatureList[k]);
			fprintf(OutPut, "%s_OnsetAge\n", FeatureList[nFeature-1]);
		}
		else
			fprintf(OutPut, "%s_nEvent,%s\n", FeatureList[nFeature-1], FeatureList[nFeature-1]);
	}
	else if (WithNEvent == 1) {
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%s_nEvent,", FeatureList[k]);
		if (WithAge == 1) {
			fprintf(OutPut, "%s_nEvent,", FeatureList[nFeature-1]);
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%s_OnsetAge,", FeatureList[k]);
			fprintf(OutPut, "%s_OnsetAge\n", FeatureList[nFeature-1]);
		}
		else
			fprintf(OutPut, "%s_nEvent\n", FeatureList[nFeature-1]);
	}
	else if (WithBinary == 1) {
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%s,", FeatureList[k]);
		if (WithAge == 1) {
			fprintf(OutPut, "%s,", FeatureList[nFeature-1]);
			for (k = 0; k < nFeature-1; k++) 
				fprintf(OutPut, "%s_OnsetAge,", FeatureList[k]);
			fprintf(OutPut, "%s_OnsetAge\n", FeatureList[nFeature-1]);
		}
		else
			fprintf(OutPut, "%s\n", FeatureList[nFeature-1]);
	}
	else if (WithAge == 1) {
		for (k = 0; k < nFeature-1; k++) 
			fprintf(OutPut, "%s_OnsetAge,", FeatureList[k]);
		fprintf(OutPut, "%s_OnsetAge\n", FeatureList[nFeature-1]);
	}
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
		if ( (ByYear == 1) && (nYear == -1) ) {
			printf("Requested output by year, but no EVENT_YEAR column.\n");
			exit(0);
		}

		FinRegIDcnt = 0;

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
					WriteOutput(iSample[0], iSample[1], SampleYear); // write existing record if necessary
					ResetRecordInfo(); // starting new record
				}
				SampleYear = tmpYear;

				for (m = 0; m < SampleList[iSample[0]][iSample[1]].nRec; m++) {
					SampleLower = SampleList[iSample[0]][iSample[1]].lower[m];
					SampleUpper = SampleList[iSample[0]][iSample[1]].upper[m];
					if ( Include(tmpAge, SampleLower, SampleUpper) == 1 ) { // check if to be considered given the event time
						iFeature = FeatureIsIn(tmpEndPt); // check if the endpoint is in the list
						if (iFeature != -1)  { // update vector if feature is Included, do nothing if not
							UpdateRecordInfo(m, iFeature, tmpAge, SampleDOB); // update the existing record with current observation
						}
					} // do nothing if onset time out of range
				} // Loop for all time period required for this sample

			}
			else if (strcmp(tmpID, SampleID) != 0) { // if the observation is for different person
				if (SampleIncFlag == 1) {
					if (((RecordIncFlag == 1) && (ByYear == 1)) || !ByYear )
						WriteOutput(iSample[0], iSample[1], SampleYear); // output existing record if necessary
				}
				ResetRecordInfo(); // starting new record

				tmpIDcnt = atoi(tmpID + 2);
				if (Pad == 1) {
					FinRegIDcnt += 1;
					while (tmpIDcnt > FinRegIDcnt) {
						if (SampleIsIn(FinRegIDcnt)) {
							WriteOutput(iSample[0], iSample[1], 0);
						}
						FinRegIDcnt += 1;
					}
				}

				strcpy(SampleID, tmpID);
				SampleYear = tmpYear;
				SampleIncFlag = SampleIsIn(tmpIDcnt);
				if (SampleIncFlag == 1) { // proceed only if the sample is to be included
					strcpy(SampleID, SampleList[iSample[0]][iSample[1]].FINREGISTRYID);
					SampleDOB = SampleList[iSample[0]][iSample[1]].DateOfBirth;
					for (m = 0; m < SampleList[iSample[0]][iSample[1]].nRec; m++) {
						SampleLower = SampleList[iSample[0]][iSample[1]].lower[m];
						SampleUpper = SampleList[iSample[0]][iSample[1]].upper[m];
						if ( Include(tmpAge, SampleLower, SampleUpper) == 1 ) { // check if to be considered given the event time
							iFeature = FeatureIsIn(tmpEndPt); // check if the endpoint is in the list
							if (iFeature != -1) // update vector if feature is included, do nothing if not
								UpdateRecordInfo(m, iFeature, tmpAge, SampleDOB); // update the existing record with current observation
						} // do nothing if onset time out of range
					} // Loop for all time period required for this sample
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
		WriteOutput(iSample[0], iSample[1], SampleYear);
}
