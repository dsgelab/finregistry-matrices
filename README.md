# finregistry-matrices
Scripts to generate endpoint, drug, and socioeconomic-demographic matrices in FinRegistry


## MakeEndPtFile.c
Creates wide matrix (sample x feature) for disease endpoints from longitudinal file. 

**This is still a working prototype, please let Zhiyu know if anything goes wrong when you are using it. She will try to work it out (_hopefully_).** 

To Compile, download the code run 
<pre>gcc MakeEndPtFile.c -o <em>Where/and/what/you/want/it/to/be</em> -lm</pre>

To excute, run
<pre>./<em>Where/and/what/you/want/it/to/be</em> <em>ParamFile</em></pre>

See below for and example of *`ParamFile`*:
<pre>
LongEndPtFile <em> LongitudinalFile </em>
SampleFile  <em> SampleList </em>
FeatureFile <em> EndPtList </em>
OutputFile  <em> OutputPrefix </em>
ByYear  <em> T </em>
OutputEventCount  <em> T </em>
OutputBinary  <em> T </em>
OutputAge <em> T </em>
</pre>

*** TBD Zhiyu will explain parameters ***

## MakeDrugFile.c
Creates wide matrix (sample x feature) for drug from detailed longitudinal file. Works similarly to the endpoint file generator above.

**This is also still a working prototype, please let Zhiyu know if anything goes wrong when you are using it. She will try to work it out (_hopefully_).** 

To Compile, download the code run 
<pre>gcc MakeDrugFile.c -o <em>Where/and/what/you/want/it/to/be</em> -lm</pre>

To excute, run
<pre>./<em>Where/and/what/you/want/it/to/be</em> <em>ParamFile</em></pre>

See below for and example of *`ParamFile`*:
<pre>
LongEndPtFile <em> LongitudinalFile </em>
SampleFile  <em> SampleList </em>
FeatureFile <em> EndPtList </em>
OutputFile  <em> OutputPrefix </em>
ByYear  <em> T </em>
OutputEventCount  <em> T </em>
OutputBinary  <em> T </em>
OutputAge <em> T </em>
Source  <em> PURCH </em>
MultiplyPackage <em> F </em>
</pre>

*** TBD Zhiyu will explain parameters ***
