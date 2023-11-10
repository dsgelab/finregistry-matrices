# Creating matrices from lab value data

## Usage

All C++ files are provided so that you can change/adapt/fix and compile them yourselves as well as already in the form of ready executables. Do note that you will likely need to compile them locally since some of the code is running with boost that is not available in epouta.

To be able to run this you will need the same `SampleFile` as described here <-link-todo->. Note **this does not support multiple time periods for the same individual**, please ask Kira if this is a feature you are interested in. 

Additionally, you will need a set of OMOP concepts that you are interested in. To figure out those I have added a file that creates summary statstics for all of the OMOP concepts that you can then use to filter the most relevant ones for you. For example choosing the top 20 most common measurements.

```
  cat /data/processed/kela_lab/kanta_lab_xxxx-xx-xx.csv | ./omop_sumstats /path/to/results/folder
```


[Go to top of page](#top)
