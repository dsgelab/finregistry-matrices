#include "header.h"

/**
 * @brief writes the omop sumstats to a file
 * 
 * @param omops unordered map of omop identifiers and their values
 * @param res_file file to write to
 * @return void
 * 
 * @details 
 * Writes the omop sumstats to a file. The omop identifiers are split into their components and written to the file. 
 * The omop values are sorted and the mean, median, standard deviation, first and third quantiles, min, max and number
 * of elements are calculated and written to the file.
**/
void write_omop_sumstats(std::unordered_map<std::string, std::vector<double>> &omops,
                         std::unordered_map<std::string, std::unordered_set<std::string>> &omop_indvs,
                         std::string res_dir_path,
                         std::string res_file_prefix,
                         int min_counts) {

    // Opening results file
    std::vector<std::string> full_res_path_vec = {res_dir_path, res_file_prefix, "_omop_sumstats.csv"};
    std::string full_res_path = concat_string(full_res_path_vec);
    std::ofstream res_file;
    res_file.open(full_res_path);
    check_out_open(res_file, full_res_path);

    // write header in all caps
    res_file << "OMOP_ID,OMOP_NAME,LAB_UNIT,MEAN,MEDIAN,SD,FIRST_QUANTILE,THIRD_QUANTILE,MIN,MAX,N_ELEMS,N_INDVS\n";

    cout << "Starting summary statistics" << endl;
    for(auto omop: omops) {
        std::string omop_identifier = omop.first;
        std::vector<double> values = omop.second;
        std::sort(values.begin(), values.end());

        double mean = get_mean(values);
        double median = get_median(values);
        double sd = get_sd(values, mean);
        double first_quantile = get_quantile(values, double(0.25));
        double third_quantile = get_quantile(values, double(0.75));
        double min = values[0];
        double max = values[values.size()-1];
        int n_elems = values.size();
        int n_indvs = omop_indvs[omop_identifier].size();

        if(n_elems >= min_counts) {
            // write to file 
            res_file << omop_identifier << "," << mean << "," << median << "," << sd << "," << first_quantile << "," << third_quantile << "," << min << "," << max << "," << n_elems << "," << n_indvs << "\n";
        }
    }

    res_file.close();
}

/**
 * @brief writes the individual omop sumstats to a file
 * 
 * @param indvs_omops_values unordered map of individual omop values
 * @param res_path path to write to
 * 
 * @return void
 * 
 * @details
 * Writes the individual omop sumstats to a file. The omop identifiers are split into their components and written to the file.
 * The omop values are sorted and the mean, median, standard deviation, first and third quantiles, min, max and number
 * of elements are calculated and written to the file.
*/
void write_indvs_omops_sumstats(std::unordered_map<std::string, std::unordered_map<std::string, std::vector<double>>> &indvs_omops_values,
                                std::unordered_map<std::string, std::string> &configs) {    
    // Opening results file
    std::string full_res_path = get_indvs_omop_sumstats_file_path(configs);
    std::ofstream res_file; res_file.open(full_res_path); check_out_open(res_file, full_res_path);

    // Write header in all caps
    res_file << "FINREGISTRYID,OMOP_ID,LAB_UNIT,MEAN,MEDIAN,SD,FIRST_QUANTILE,THIRD_QUANTILE,MIN,MAX,N_ELEMS" << std::endl;
    for(auto indv_data: indvs_omops_values) {
        std::string finregid = indv_data.first;
          for(auto omop:  indv_data.second) {
            std::string omop_identifier = omop.first;
            std::string omop_id = split(omop_identifier, "_")[0];
            std::string lab_unit = split(omop_identifier, "_")[1];

            // Getting all values for this omop
            std::vector<double> values = omop.second;
            std::sort(values.begin(), values.end());

            // Calculating summary statistics
            double mean = get_mean(values);
            double median = get_median(values);
            double sd = get_sd(values, mean);
            double first_quantile = get_quantile(values, double(0.25));
            double third_quantile = get_quantile(values, double(0.75));
            double min = values[0];
            double max = values[values.size()-1];
            int n_elems = values.size();

            // Writing to file
            res_file << finregid << "," << omop_id << "," << lab_unit << "," << mean << "," << median << "," << sd << "," << first_quantile << "," << third_quantile << "," << min << "," << max << "," << n_elems << std::endl;
        }
    }
}

/**
 * @brief calculates the quantile of a vector of values
 * 
 * @param values vector of values
 * @param quantile quantile to calculate
 * @return double quantile value
 * 
 * @details
 * Calculates the quantile of a vector of values. The vector is sorted and the quantile is calculated using linear interpolation.
*/
double get_quantile(std::vector<double> values, 
                    double quantile) {
    // Step 2: Calculate the position of the quantile
    int n = values.size();
    double position = (n - 1) * quantile; // Using quantile directly

    // Step 3: Find the value at the position with linear interpolation
    int lower_index = static_cast<int>(position);
    int upper_index = lower_index + 1;
    double lower_value = values[lower_index];
    double upper_value = values[upper_index];
    double index_diff = position - lower_index;
    double quantile_value = lower_value + index_diff * (upper_value - lower_value);

    return quantile_value;
}

/**
 * @brief calculates the mean of a vector of values
 * 
 * @param values vector of values
 * @return double mean
 * 
 * @details
 * Calculates the mean of a vector of values.
*/
double get_mean(std::vector<double> values) {
    double sum = std::accumulate(values.begin(), values.end(), 0.0);
    double mean = sum / values.size();
    return(mean);
}

/**
 * @brief calculates the median of a vector of values
 * 
 * @param values vector of values
 * @return double median
 * 
 * @details
 * Calculates the median of a vector of values. If the vector has an even number of elements, the median is calculated
 * as the mean of the two middle elements.
*/
double get_median(std::vector<double> values) {
    double median;
    if (values.size() % 2 == 0) {
        median = (values[values.size()/2 - 1] + values[values.size()/2]) / 2;
    } else {
        median = values[values.size()/2];
    }
    return(median);
}

/**
 * @brief calculates the standard deviation of a vector of values
 * 
 * @param values vector of values
 * @param mean mean of the vector of values
 * 
 * @return double standard deviation
 * 
 * @details
 * Calculates the standard deviation of a vector of values.
*/
double get_sd(std::vector<double> values,
              double mean) {
    double sum_of_squares = 0.0;

    for (const double& value : values) {
        double difference = value - mean;
        sum_of_squares += difference * difference;
    }

    double variance = sum_of_squares / (values.size()-1);
    double sd = std::sqrt(variance);
    return(sd);
}

/**
 * @brief reads in the individuals OMOP summary statistics file
 * 
 * @param indvs_omop_sumstats unordered map of individual omop summary statistics to fill in
 * @param indvs_omops_sumstats_path path to the individuals OMOP summary statistics file
 * @param relevant_omops unordered set of relevant omop identifiers. If empty, all omop identifiers are relevant.
 * @param relevant_indvs unordered map of relevant individuals. If empty, all individuals are relevant.
 * 
 * @return void
 * 
 * @details
 * Reads in the individuals OMOP summary statistics file. If relevant omop identifiers and individuals are passed, only
 * the relevant information is read in. Otherwise, all information is read in. The information is stored in the unordered
 * map indvs_omop_sumstats. The keys are the finregids and the values are unordered maps of omop identifiers and their
 * summary statistics. The summary statistics are stored in a vector of strings in the following order: mean, median, sd,
 * first quantile, third quantile, min, max, n_elems. This has to be the exact order they appear in the file.
*/
void read_indvs_omops_sumstats(std::string indvs_omops_sumstats_path,
                               std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string, std::string>>> &indvs_omop_sumstats,
                               std::unordered_set<std::string> &relevant_omops,
                               std::unordered_set<std::string> &relevant_indvs) {
    // Opening file
    std::ifstream indvs_omops_sumstats_file;
    indvs_omops_sumstats_file.open(indvs_omops_sumstats_path);
    check_in_open(indvs_omops_sumstats_file, indvs_omops_sumstats_path);
    char delim = find_delim(indvs_omops_sumstats_path);

    int first_line = 1;
    std::string line;
    std::vector<std::string> col_names;

    while(std::getline(indvs_omops_sumstats_file, line)) {
        if (first_line == 1) {
            col_names = splitString(line, delim);
            first_line = 0;
            continue;
        }

        std::vector<std::string> line_vec(splitString(line, delim));
        std::string finregid = line_vec[0];
        std::string omop_id = line_vec[1];
        std::string lab_unit = line_vec[2];

        std::string omop_identifier = concat_string(std::vector<std::string>({omop_id, lab_unit}), std::string("_"));
        // If not information for relevant indvs and omops passed, using all information
        if(relevant_indvs.empty() || (relevant_indvs.find(finregid) != relevant_indvs.end())) {
            if(relevant_omops.empty() || (relevant_omops.find(omop_identifier) != relevant_omops.end())) {
                std::unordered_map<std::string, std::string> sumstats;
                // Iterate over all sumstats
                for(long unsigned int elem_idx = 3; elem_idx <= (col_names.size()-1); elem_idx++) {
                    sumstats[col_names[elem_idx]] = line_vec[elem_idx];
                }
                indvs_omop_sumstats[finregid][omop_identifier] = sumstats;
            }
        }

    }
}

/**
 * @brief Reads the sample file with individuals start and end date to the study
 * 
 * @param relevant_indvs unordered map of relevant individuals to fill in. Made up of finregid -> <start, end> date
 * @param indvs_path path to the individuals sample file
 * 
 * @return void
 * 
 * @details 
 * Reads the sample file with individuals start and end date to the study. The information is stored in the unordered
 * map relevant_indvs. The keys are the finregids and the values are tuples of start and end dates.
*/
void read_indvs_date_file(std::unordered_map<std::string, std::tuple<date, date>> &relevant_indvs,
                          std::string indvs_path) {
    // Opening sample file
    std::ifstream indvs_file;
    indvs_file.open(indvs_path); check_in_open(indvs_file, indvs_path); std::string indv_line;

    char delim = find_delim(indvs_path);

    int first_line = 1;
    while(std::getline(indvs_file, indv_line)) {
        if (first_line == 1) {
            first_line = 0;
            continue;
        }

        // Getting relevant information
        std::vector<std::string> line_vec(splitString(indv_line, delim));
        std::string finregid = line_vec[0];
        std::string start_date = line_vec[2];
        std::string end_date = line_vec[3];

        // Converting dates to date objects
        date start_date_obj(from_simple_string(start_date));
        date end_date_obj(from_simple_string(end_date));

        // Creating tuple of dates <start, end>
        std::tuple<date, date> indv_dates(start_date_obj, end_date_obj);

        // Assining to individual
        relevant_indvs[finregid] = indv_dates;
    }
}

/**
 * @brief Reads the sample file with all relevant individuals, ignoring the start and end date
 * 
 * @param relevant_indvs unordered set of relevant individuals to fill in. Made up of finregids
 * @param indvs_path path to the individuals sample file
 * 
 * @return void
 * 
 * @details
 * Reads the sample file with all relevant individuals, ignoring the start and end date. The information is stored in the
 * unordered set relevant_indvs. The keys are the finregids. This is used when we do not care about the
 * start or end date to the study, but only about the relevant individuals for which we want to get information. 
*/
void read_indvs_file(std::unordered_set<std::string> &relevant_indvs,
                              std::string indvs_path) {
    // Opening file
    std::ifstream indvs_file;
    indvs_file.open(indvs_path); check_in_open(indvs_file, indvs_path); std::string indv_line;
    
    char delim = find_delim(indvs_path);

    // Reading
    int first_line = 1;
    while(std::getline(indvs_file, indv_line)) {
        if (first_line == 1) {
            first_line = 0;
            continue;
        }
        std::vector<std::string> line_vec(splitString(indv_line, delim));
        std::string finregid = line_vec[0];
        relevant_indvs.insert(finregid);
  }
}

/**
 * @brief Reads the omop file with all relevant omops for which we want to get data
 * 
 * @param relevant_omops unordered set of relevant omop identifiers to fill in. Made up of omop_id;lab_unit
 * @param omops_path path to the omops sample file
 * 
 * @return void
 * 
 * @details
 * Reads the omop file with all relevant omops for which we want to get data. The information is stored in the
 * unordered set relevant_omops. The keys are the omop identifiers. An omop identifier is made up of the
 * OMOP ID and the lab unit, separated by "_".
 * 
*/
void read_omops_file(std::unordered_set<std::string> &relevant_omops,
                     std::string omops_path) {

    std::ifstream omops_file; omops_file.open(omops_path); check_in_open(omops_file, omops_path); 
    
    char delim = find_delim(omops_path);
    std::string omop_line;
    int first_line = 1;
    while(std::getline(omops_file, omop_line)) {
        if (first_line == 1) {
            first_line = 0;
            continue;
        }

        std::vector<std::string> line_vec(splitString(omop_line, delim));
        std::string omop_id = line_vec[0];
        std::string lab_unit = line_vec[2];
        std::string omop_identifier = concat_string(std::vector<std::string>({omop_id, lab_unit}), std::string("_"));
        relevant_omops.insert(omop_identifier);
    }
}

/**
 * indvs_omop_sumstats has structure FINREGID -> OMOP_ID_LAB_UNIT -> measure_name > measure_value
*/
void write_relevant_sumstats_files( std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string, std::string>>> &indvs_omop_sumstats,
                                    std::vector<std::string> &relevant_sumstats,
                                    std::unordered_set<std::string> &relevant_omops,
                                    std::string res_dir_path,
                                    std::string res_file_prefix) {
    for(auto sumstat: relevant_sumstats) {
        // Opening file
        std::vector<std::string> full_res_path_vec = {res_dir_path, res_file_prefix, sumstat};
        std::string full_res_path = concat_string(full_res_path_vec);
        std::ofstream res_file;
        res_file.open(full_res_path);
        check_out_open(res_file, full_res_path);

        // Header
        res_file << "FINREGISTRYID" << ",";
        res_file << concat_string(relevant_omops, (std::string(","))) << std::endl;

        // Each row is a single individual
        for(auto indv_omop_sumstats: indvs_omop_sumstats) {
            std::string finregid = indv_omop_sumstats.first;
            res_file << finregid << ",";

            // All data of this individual
            std::unordered_map<std::string, std::unordered_map<std::string, std::string>> indv_data = indv_omop_sumstats.second;

            // Writing to file needs to be ordered the same for everyone as in relevant_omops
            // A relevant omop in this case is a combination of OMOP ID and lab unit
            for(auto crnt_omop: relevant_omops) {
                if(indv_data.find(crnt_omop) != indv_data.end()) {
                // If we have data for this omop get the relevant sumstat
                    res_file << indv_data[crnt_omop][sumstat] << ",";
                } else {
                    res_file << "NA" << ",";
                }
            }
            res_file << endl;
        }
        //Closing file
        res_file.close();
    }
}