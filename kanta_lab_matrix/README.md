# Creating matrices from lab value data

## Usage

All C++ files are provided so that you can change/adapt/fix and compile them yourselves as well as already in the form of ready executables. Do note that you will likely need to compile them locally since some of the code is running with `boost` that is not available in epouta.

After adjusting the config file, preparing the sample and the OMOP file you can run the full programm with the simple command

```
  make run_kanta_lab_matrix
```

This does two steps, it first creates a file with the summary statistics for each pair of OMOP IDs and lab units for each individual. Where each set of <`FINREGISTRYID`, `OMOP_ID`, `LAB_UNIT`> has it's own row.

```
  exec/indv_sumstats config_file
```

Then it creates a single file based on the selected relevant summary statistics, i.e. the mean value. Here each row is a single individual and each column the i.e. mean value of a selected `OMOP_ID` and `LAB_UNIT` pair.

```
  exec/kanta_lab_matrix config_file
```

This way you can also rerun the second step and choose a different summary stat value. Or you can only run the first step if you are interested in further detailed summary statistics. 

### Config File

You can find an example of a config file under `configs/kanta_lab_matrix_mean.config`.

The Config file expects at least the following two entries (the delimiter can be tab, comma or semicolon):
- `KantaLabFile`: The complete path to the kanta lab data file. (so likely something like `/data/processed_data/kela_lab/kanta_lab_20xx-xx-xx.csv).
- `ResDirPath`: The path to the results directory where you want your results saved to.

It is also a good idea to pass it:

- `ResFilePrefix`: The default will be `kanta_lab_`. But maybe you will want it to be more specific.

Additionally needed depending on which step you are performing are:

- `SampleFile`: The complete path to the sample file as described here <-link-todo->
- `OmopFile`: The OMOP concepts you are interested in. This file will need at least as a first column the OMOP IDs and as a thirds column the lab units. Ideally you should create this file based on section <-link-todo->.
- `RelevantSumstats`: The summary statistics you are interested in for each individual in the selected period for each combinationof OMOP ID and lab units chosen. Currently supported are: `MEAN`,`MEDIAN`,`SD`,`FIRST_QUANTILE`,`THIRD_QUANTILE`,`MIN`,`MAX`. If you choose multiple summary statistics you can space separate them and the results will be written to separate files.

Not you can comment any row with a `#` in front and it will be ignored by the config file reader.

### Finding your OMOP IDs

Additionally, to the sample file you will need a set of OMOP concepts that you are interested in. To figure out those I have added a file that creates summary statstics for all of the OMOP concepts that you can then use to filter the most relevant ones for you. For example choosing the top 20 most common measurements.

You can create this list, using the following command:

```
  ./omop_sumstats config_file
```

You can add a minimum number the OMOP concepts should occur in the file. I actually recommend this as an initial screening because there is still a lot of mistakes in the data. For example you can use:

```
  ./omop_sumstats config_file 100
```

where each combination of OMOP concept and lab unit has to appear at least 100 times to be considered relevant. The file will be written to `<ResDirPath>/<ResFilePrefix>_omop_sumstats.csv`. I will later add some script to further process these statistics, for now you find ready-made lists at `/data/projects/project_kdetrois/omop_sumstats/`


[Go to top of page](#top)
