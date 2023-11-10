FLAGS = -std=c++11 -static -Wall


## HELPERS
bin/string_helpers.o: src/string_helpers.cpp
	$(info Buildung String Helpers...)  g++ -c $(FLAGS) -o bin/string_helpers.o src/string_helpers.cpp

bin/file_helpers.o: src/file_helpers.cpp
	$(info Buildung File Helpers...)  g++ -c $(FLAGS) -o bin/file_helpers.o src/file_helpers.cpp

bin/config_file_readers.o: src/config_file_readers.cpp
	$(info Buildung config file readr...)  g++ -c $(FLAGS) -o bin/config_file_readers.o src/config_file_readers.cpp

bin/sumstats_utils.o: src/sumstats_utils.cpp
	$(info Buildung Main omop_sumstats...)  g++ -c $(FLAGS) -o bin/sumstats_utils.o src/sumstats_utils.cpp

## OMOP Sumstats
omop_sumstats: bin/omop_sumstats_main.o bin/file_helpers.o bin/string_helpers.o bin/sumstats_utils.o bin/config_file_readers.o
	g++ $(FLAGS) bin/omop_sumstats_main.o bin/file_helpers.o bin/string_helpers.o bin/sumstats_utils.o bin/config_file_readers.o -o exec/omop_sumstats

bin/omop_sumstats_main.o: src/omop_sumstats_main.cpp
	$(info Buildung Main omop_sumstats...)  g++ -c $(FLAGS) -o bin/omop_sumstats_main.o src/omop_sumstats_main.cpp

## Indiv Sumstats
indv_sumstats: bin/indv_sumstats_main.o bin/file_helpers.o bin/string_helpers.o bin/sumstats_utils.o bin/config_file_readers.o
	g++ $(FLAGS) bin/indv_sumstats_main.o bin/file_helpers.o bin/string_helpers.o bin/sumstats_utils.o bin/config_file_readers.o -o exec/indv_sumstats

bin/indv_sumstats_main.o: src/indv_sumstats_main.cpp
	$(info Buildung Main indv_sumstats...)  g++ -c $(FLAGS) -o bin/indv_sumstats_main.o src/indv_sumstats_main.cpp

## Matrix Generation
kanta_lab_matrix: bin/kanta_lab_matrix.o bin/file_helpers.o bin/string_helpers.o bin/sumstats_utils.o bin/config_file_readers.o
	g++ $(FLAGS) bin/kanta_lab_matrix.o bin/file_helpers.o bin/string_helpers.o bin/sumstats_utils.o bin/config_file_readers.o -o exec/kanta_lab_matrix

bin/kanta_lab_matrix.o: src/kanta_lab_matrix.cpp
	$(info Buildung Main kanta_lab_matrix...)  g++ -c $(FLAGS) -o bin/kanta_lab_matrix.o src/kanta_lab_matrix.cpp

clean:
	$(info Cleaning up...)
	rm bin/*.o
	rm exec/*