# finregistry-matrices

Scripts to generate endpoint, drug, and socioeconomic-demographic matrices in FinRegistry

**Now allows to output multiple records per individual!**
The same individual can appear for multiple times in your `SampleFile`, with different dates for inclusion periods. The program will output for each inclusion period, each individual, with the first column as `FINREGISTRYID`, followed by `LowerAge` and `UpperAge` indicating the lower and upper bound of inclusion period in terms of individual's age. The output will be sorted by the these three columns in the same order. The program code allows you to have at max 20 differnet inclusion periods for each individual in your `SampleFile`. If that is not enough, you can expand it by changing
<pre>
#define MaxRec 20 
</pre>
to a larger number in row 12 of the source code and recompile :D

*All examples appear below are hypothetical and do not contain any real data*

Now you can use one single parameter file that looks like below to run both wide endpoint generator and wide drug generator. In this case, some parameters will be shared between the two programs. Using separate parameter files still works if you prefer. Please see below for more details. 

Param | Description | Type | Default
----- | ----------- | ---- | -------
`SampleFile` | List of FinRegistry IDs to include | file | None
`OutputPrefix` | Output path | str | None
`LongEndPtFile` | Longitudinal endpoints file path (input data) | str | None 
`EndPtList` | List of endpoints to be included | file | None
`EndPtByYear` | Endpoint output file by year | bool | F
`EndPtOutputEventCount` | Endpoint output file with event counts | bool | F
`EndPtOutputBinary` | Endpoint output file with binary indicators | bool | F
`EndPtOutputAge` | Endpoint output file with age at onset | bool | F
`LongFile` | Detailed longitudinal file path (input data) | str | None
`DrugList` | List of drugs (ATC codes or truncated ATC codes) to be included | file | None 
`DrugByYear` | Drug output file by year | bool | F
`DrugOutputEventCount` | Drug output file with event counts | bool | F
`DrugOutputBinary` | Drug output file with binary indicators | bool | F 
`DrugOutputAge` | Drug output file with age at first purchase | bool | F
`RegSource` | Source registry to be considered for drugs | str | None
`DrugMultiplyPackage` | Drug output file with counts weighted by the number of packages | bool | T
`PadNoEvent` | Output zeros if the sample does not have any event within the inclusion period, if F then only output samples with at least one event | bool | F


## MakeEndPtFile.c
Creates wide matrix (sample x feature) for disease endpoints from longitudinal file. 

**This is still a _(hopefully)_ working prototype, please let Zhiyu know if anything goes wrong when you are using it. She will try to work it out (_hopefully_).** 

To Compile, download the code and run 
<pre>gcc MakeEndPtFile.c -o <em>Where/and/what/you/want/it/to/be</em> -lm</pre>

To excute, run
<pre>./<em>Where/and/what/you/want/it/to/be</em> <em>ParamFile</em></pre>

See below for and example of *`ParamFile`*:
<pre>
SampleFile  <em> SampleList </em>
OutputPrefix  <em> OutputPrefix </em>
LongEndPtFile <em> LongitudinalEndPtFile </em>
EndPtList <em> EndPtList </em>
EndPtByYear  <em> T/F </em>
EndPtOutputEventCount  <em> T/F </em>
EndPtOutputBinary  <em> T/F </em>
EndPtOutputAge <em> T/F </em>
</pre>

<em> `SampleFile` </em> is a **headless** file listing the samples you would like to include in the output. It should have four columns in the following order: *FINREGISTRYID*, *DateOfBirth for this sample*, *Lowerbound of record inclusion date for this sample*, *Upperbound of record inclusion date for this sample*. All dates should be in a `yyyy-mm-dd` format. The output will only include records for the sample happening between `Lowerbound date` - `Upperbound date`, including the two ends of the window. This allows each sample to have different inclusion periods. The program should be able to accept space, comma or tab separated file (Please let Zhiyu know if it doesn't). See below for a demo of this file 
<pre>
FRXXXXXX1 2001-01-01  2005-01-01  2020-12-31
FRXXXXXX2 1991-02-05  2000-01-01  2015-12-31
FRXXXXXX5 1984-06-13  2001-09-01  2004-12-31
FRXXXXXX8 2007-10-29  2005-12-01  2021-12-31
FRXXXXX10 1997-04-11  2001-04-01  2020-12-31
...
</pre>

<em> `OutputPrefix` </em> is where you would like the output to be written to. The program should output a file named as </em>`OutputPrefix`</em>`.EndPt`.

<em>`LongEndPtFile`</em> is the longitudinal file to be converted from that looks like `/data/processed_data/endpointer/longitudinal_endpoints_no_omits_DF10_2022_09_29.txt.ALL`. It should have at least `FINREGISTRYID`, `ENDPOINT` and `EVENT_AGE` colunms. `EVENT_YEAR` is optional, but it will complain if this column is missing whereas some specific options are specified that requires year information. The file should be sorted by first `FINREGISTRYID` and then `EVENT_AGE`. To the best of Zhiyu's knowledge files generated by Andrius' code should be so already. If you do any preporcessing on the longitudinal please make sure it is still sorted.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Zhiyu is aware that this info is technically implied by EVENT_AGE, but she was too lazy to add that for this version. She will update this in the near future :)*

<em> `EndPtList` </em> is a **headless** file with one column listing the endpoints you would like to include. The program will look for **exact** match of enpoint names in the longitudinal file from the `ENDPOINT` column. 

<em> `PadNoEvent` </em> is a boolean with which you specify if you want the samples with no events within the inclusion period to be padded with 0s. This parameter works for both endpoint and drug file generator. Please input **T** or **F**. **F** means that the output will only include rows with at least one non-zero. An example for the `SampleFile` above, say if individual <em>FRXXXXXX2</em> does not have any endpoints within the given `EndPtList` during his inclusion period <em>2000-01-01</em> to <em>2015-12-31</em>, under the default **F** for `PadNoEvent`, the output will not include the coresponding row, ie as below: 
<pre>
FINREGISTRYID  Endpt1  EndPt2  Endpt3  ...
FRXXXXXX1  xx  xx  xx  ...
FRXXXXXX5  xx  xx  xx  ...
FRXXXXXX8  xx  xx  xx  ...
FRXXXXX10  xx  xx  xx  ...
...
</pre>
Whereas if **T** is selected, the output will be like
<pre>
FINREGISTRYID  Endpt1  EndPt2  Endpt3  ...
FRXXXXXX1  xx  xx  xx  ...
FRXXXXXX2  0  0 0 ...
FRXXXXXX5  xx  xx  xx  ...
FRXXXXXX8  xx  xx  xx  ...
FRXXXXX10  xx  xx  xx  ...
...
</pre>

<em> `EndPtByYear` </em> is a boolean where you indicate if you would like to output sample info by year. Please input **T** or **F**. Output by year means that each row of the output will be an individuals record for a certain year within the inclusion period. *Note that each row output only events occured in a specific year, and if nothing happens that year, the row of zero will not be written.* ie. it can look like below with some gaps in year
<pre>
FINREGISTRYID Year  Endpt1  EndPt2  Endpt3  ...
FRXXXXXX1 2001  xx  xx  xx  ...
FRXXXXXX1 2002  xx  xx  xx  ...
FRXXXXXX1 2005  xx  xx  xx  ...
FRXXXXXX2 2001  xx  xx  xx  ...
FRXXXXXX2 2004  xx  xx  xx  ...
...
</pre>

If chosen **F**, it will output one row for each sample without the `Year` column and look like below
<pre>
FINREGISTRYID  Endpt1  EndPt2  Endpt3  ...
FRXXXXXX1  xx  xx  xx  ...
FRXXXXXX2  xx  xx  xx  ...
FRXXXXXX5  xx  xx  xx  ...
FRXXXXXX8  xx  xx  xx  ...
FRXXXXX10  xx  xx  xx  ...
...
</pre>

<em> `EndPtOutputEventCount` </em> is a boolean where you indicate if you would like to output the number of occurance for each endpoint. It counts the number of times the endpoint appears in the longitudinal file for a sample within the inclusion period of time. *Zhiyu noticed that sometimes the same endpoint occures at certain time/age can appear more than once in the longitudinal file with different EVENT_TYPE (eg. HILMO, ERIK_AVO etc.). If that happens, the current code will count them as more than one occurance. She is not sure if it is the right way to handle (or if she should count all occurance at the same age as only one) and will double check with the team. Please also let her know what you think is the best.* The output should look like this
<pre>
FINREGISTRYID  Endpt1_nEvent  EndPt2_nEvent  Endpt3_nEvent  ...
FRXXXXXX1  10  0  3  ...
FRXXXXXX2  0  4  1  ...
FRXXXXXX5  0  0  2  ...
FRXXXXXX8  5  1  0  ...
FRXXXXX10  0  0  3  ...
...
</pre>

<em> `EndPtOutputBinary` </em> is a boolean where you indicate if you would like to output binary indicator for each endpoint. It outputs one if the endpoint occures in the longitudinal file for a sample within the inclusion period of time and zero otherwise. The output will look like this
<pre>
FINREGISTRYID  Endpt1  EndPt2  Endpt3  ...
FRXXXXXX1  1  0  1  ...
FRXXXXXX2  0  1  1  ...
FRXXXXXX5  0  0  1  ...
FRXXXXXX8  1  1  0  ...
FRXXXXX10  0  0  1  ...
...
</pre>

<em> `EndPtOutputAge` </em> is a boolean where you indicate if you would like to output the age of onset for each endpoint. It outputs sample's age at the earliet occurance of the endpoint in the longitudinal file for a sample within the inclusion period of time and zero otherwise. *The ages are rounded to two decimal places.* The output should look like this
<pre>
FINREGISTRYID  Endpt1_OnsetAge  EndPt2_OnsetAge  Endpt3_OnsetAge  ...
FRXXXXXX1  10.23  0  15.36  ...
FRXXXXXX2  0  20.14  34.25  ...
FRXXXXXX5  0  0  32.30  ...
FRXXXXXX8  24.35  29.31  0  ...
FRXXXXX10  0  0  41.23  ...
...
</pre>

All these boolean output parameters are not exclusive. ie. you can output both binary and event count, and on top of them, age of onset, in a by-year manner. If so, the output will look something like below
<pre>
FINREGISTRYID  Year Endpt1_nEvent Endpt1  Endpt2_nEvent Endpt2 Endpt3_nEvent Endpt3  Endpt1_OnsetAge  EndPt2_OnsetAge  Endpt3_OnsetAge  ...
FRXXXXXX1 2001  8 1 3 1 0 0 10.23 10.18 0.00  ...
FRXXXXXX1 2002  2 1 0 0 0 0 11.24 0.00  0.00  ...
FRXXXXXX1 2005  0 0 1 1 2 1 0.00  14.13 14.67 ...
FRXXXXXX2 2001  0 0 0 0 3 1 0.00  0.00  23.45 ...
FRXXXXXX2 2004  2 1 0 0 4 1 26.14 0.00  26.73 ...
...
</pre>
Please choose accordingly what you would like to output. The output file will be tab-seperated. 


## MakeDrugFile.c
Creates wide matrix (sample x feature) for drug from detailed longitudinal file. Works similarly to the endpoint file generator above.

**This is again just a prototype. Zhiyu has recently tested it on larger scale (~3M) samples and it was working for her. But please let her know if you find some of the many problems.** 

To Compile, download the code run 
<pre>gcc MakeDrugFile.c -o <em>Where/and/what/you/want/it/to/be</em> -lm</pre>

To excute, run
<pre>./<em>Where/and/what/you/want/it/to/be</em> <em>ParamFile</em></pre>

See below for and example of *`ParamFile`*:
<pre>
SampleFile  <em> SampleList </em>
OutputPrefix  <em> OutputPrefix </em>
LongFile <em> LongitudinalFile </em>
DrugList <em> DrugList </em>
DrugByYear  <em> T/F </em>
DrugOutputEventCount  <em> T/F </em>
DrugOutputBinary  <em> T/F </em>
DrugOutputAge <em> T/F </em>
RegSource  <em> PURCH </em>
DrugMultiplyPackage <em> T/F </em>
</pre>

`SampleFile` and `OutputPrefix` are oarameters shared with the wide endpoint generator above. The program should output a file named as </em>`OutputPrefix`</em>`.Drug`. `DrugByYear`, `DrugOutputEventCount`, `DrugOutputBinary`, and `DrugOutputAge` work in the same way as `EndPtByYear`, `EndPtOutputEventCount`, `EndPtOutputBinary`, and `EndPtOutputAge`.

`LongFile` here is a detailed longitudinal file to be converted from that looks like `/data/processed_data/detailed_longitudinal/detailed_longitudinal.csv`. If should at least have `FINREGISTRYID`, `SOURCE`, `EVENT_AGE` and a column named `CODE1` as the feature name column. It will also try to find `PVM` or `EVENT_YRMNTH` and throw a complain if `DrugByYear` option is chosen, which Zhiyu will fix at some point. A difference from the endpoint generator: this drug program allows to output occurance of drug purchase multiplied by number of packages. If the option is chosen, a column named `CODE4` should be included indicating the number of packages. Or else this option will be override to default (false).

`RegSource` is the source registry records to be considered, and should be `PURCH` for drug matrix generation. Technically this program can also be used to generate wide matrix from other sources, as long as specified here and coresponding `DrugList` is provided. In other cases, `DrugList` may not specifically be "drugs", but any other register codes you would like to include as analyses features. The program will try to match listed codes with column CODE1 in the detailed longitudinal file.

`DrugMultiplyPackage` is a boolean indicating if you want the output count of occurance to be weighted by number of packages. If **T**, then the event count will basically become the number of packages a sample purchased within the inclusion time period. Otherwise it should be the number of time he made purchase. *Becareful using this when multiple drugs/ACT codes fall into one feature in the input drug list. Does it still make sense to count the total number of packages? Zhiyu is not very familiar with drug codes so please choose accordingly given your analyses goal.*

`DrugList` is a list of **ATC codes** or **truncated ATC codes** that you want to include in the output. **Truncated ATC codes** means the first *n*-digits of the ATC code. The program tries to match codes in `CODE1` column of the input detailed longitudinal file **from the beginning** with each ATC code in the given list to find a match for the first *n* digits. *n* can vary for each code in the list. For example, you can input a drug list that looks like below
<pre>
A02BC02
C07AB
R0
J01
...
</pre>
where only `A02BC02` is an ATC code of full length which will be match as **exact**. The other columns will be counting occurences of sample purchasing **any** drug whose code starts with the given items. ie. `J01CA08`, `J01CE02`, `J01EA01` ... all start with `J01` so will be counted in that column.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*A known "problem" which Zhiyu is working on fixing is that if you input a drug list that has ATC codes encompassing each other, eg. a list with both `J01` and `J01CE`, then the purchase of, say, `J01CE02` or `J01CE01` in this case, will only be counted in only one of these two columns, depending on which code is found first through binary search in your list. She thinks it's a rather rare case and is not sure if anyone would want do something like that, but please don't if you see this!*

