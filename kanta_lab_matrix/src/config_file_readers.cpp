#include "header.h"

/**
 * @brief Reads config file for the analyses
 * 
 * @param config_path Path to config file
 * @param configs Map for storing config values
 * 
 * @return void
 *
 * 
 * @details Config file can be commented with #, the separator should be either \t, ; or ,
 *          Information in the config file should be:
 *          - KantaLabFile: Path to the KantaLabFile
 *          - SampleFile: Path to the file containing the relevant individuals and the dates
 *          - OmopFile: Path to the file containing the relevant OMOPs
 *          - IndvsOmopSumstatsFile: Path to the file containing the summary statistics for each individual and OMOP
 *          - ResDirPath: Path to the folder where the results are stored
 *          - ResFilePrefix: Prefix for the name of the results files
 *          - RelevantSumstats: Comma separated list of sumstats to be stored in separate files
 *         
*/
void read_config_file(std::string config_path,
                      std::unordered_map<std::string, std::string>& configs) {
    // Open config file
    std::ifstream config_file; config_file.open(config_path); check_in_open(config_file, config_path);

    // Optional file separators are `\t`, `;` and `,`
    char delim = find_delim(config_path);

    std::string config_line;
    while(std::getline(config_file, config_line)) {
        // ignore lines that start with #
        if(config_line[0] != '#') {
            std::vector<std::string> line_vec(splitString(config_line, delim));
            std::string config_name = line_vec[0];
            std::string config_value = line_vec[1];
            configs[config_name] = config_value;
        }
    }
    // check if last element of resdirpath is a slash
    if(configs.find("ResDirPath") != configs.end()) {
        check_and_fix_last_char(configs["ResDirPath"], '/');
    } else {
        std::cout << "Could not find necessary ResDirPath from config file " << std::endl;
        exit(EXIT_FAILURE);
    }
    // check if last element of resfileprefix is an underscore and if not add it
    if(configs.find("ResFilePrefix") != configs.end()) {
        check_and_fix_last_char(configs["ResFilePrefix"], '_');
    // if not found use generic kanta_lab_
    } else {
        std::cout << "Could not find ResFilePrefix from config file, using generic kanta_lab_" << std::endl;
        configs["ResFilePrefix"] = "kanta_lab_";
    }

    // check if kantalabfile is found
    if(configs.find("KantaLabFile") == configs.end()) {
        std::cout << "Could not find KantaLabFile from config file " << std::endl;
        exit(EXIT_FAILURE);
    }

    // Printing config
    std::cout << "Printing config" << std::endl;
    for (auto const &config : configs)
    {
        std::cout << config.first << " <--> " << config.second << std::endl;
    }
}

void read_indvs_date_file_from_config(std::unordered_map<std::string, std::string> &configs,
                                       std::unordered_map<std::string, std::tuple<date, date>> &relevant_indvs,
                                       int stop_if_not_found = 0) {
    if(configs.find("SampleFile") != configs.end()) {
        read_indvs_date_file(relevant_indvs, configs["SampleFile"]);
    } else { 
        std::cout << "Could not find SampleFile path from config file " << std::endl; 
        if(stop_if_not_found) exit(EXIT_FAILURE);
        else std::cout << "Using all individuals found in the summary statistics file" << endl;
    }

    // print first 5 elements
    std::cout << "Printing first 5 elements from the Sample File" << std::endl;
    int i = 0;
    for (auto const &indv : relevant_indvs) {
        std::cout << indv.first << " " << std::get<0>(indv.second) << " " << std::get<1>(indv.second) << std::endl;
        i++;
        if (i == 5)
            break;
    }
}


void read_indvs_file_from_config(std::unordered_map<std::string, std::string> &configs,
                                          std::unordered_set<std::string> &relevant_indvs,
                                          int stop_if_not_found = 0) {
    if(configs.find("SampleFile") != configs.end()) {
        read_indvs_file(relevant_indvs, configs["SampleFile"]);
    } else { 
        std::cout << "Could not find SampleFile path from config file " << std::endl; 
        if(stop_if_not_found) exit(EXIT_FAILURE);
        else std::cout << "Using all OMOPs found in the summary statistics file" << endl;
    }

    // print first 5 elements
    std::cout << "Printing first 5 relevant individuals" << std::endl;
    int i = 0;
    for (auto const &indv : relevant_indvs) {
        std::cout << indv << std::endl;
        i++;
        if (i == 5)
            break;
    }
}



void read_omops_file_from_config(std::unordered_map<std::string, std::string> &configs,
                                 std::unordered_set<std::string> &relevant_omops,
                                 int stop_if_not_found = 0) {
    if(configs.find("OmopFile") != configs.end()) {
        read_omops_file(relevant_omops, configs["OmopFile"]);
    } else { 
        std::cout << "Could not find OmopFile path from config file " << std::endl; 
        if(stop_if_not_found) exit(EXIT_FAILURE);
        else std::cout << "Using all OMOPs found in the summary statistics file" << endl;
    }

    // print first 5 elements
    std::cout << "Printing first 5 relevant OMOPs" << std::endl;
    int i = 0;
    for (auto const &omop : relevant_omops) {
        std::cout << omop << std::endl;
        i++;
        if (i == 5)
            break;
    }
}

void read_indvs_omop_sumstats_from_config(std::unordered_map<std::string, std::string> &configs,
                                          std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string, std::string>>> &indvs_omop_sumstats,
                                          std::unordered_set<std::string> &relevant_omops,
                                          std::unordered_set<std::string> &relevant_indvs) {
    if(configs.find("IndvsOmopSumstatsFile") != configs.end()) {
        read_indvs_omops_sumstats(configs["IndvsOmopSumstatsFile"], indvs_omop_sumstats, relevant_omops, relevant_indvs);
    } else {
        // If not explicitly named using the same as previously created based on the reuslts directory and the
        // indvs omop sumstats file prefix.
        if((configs.find("ResDirPath") != configs.end()) & (configs.find("ResFilePrefix") != configs.end())) {
            std::string indvs_omops_sumstats_file_path = get_indvs_omop_sumstats_file_path(configs);
            read_indvs_omops_sumstats(indvs_omops_sumstats_file_path, indvs_omop_sumstats, relevant_omops, relevant_indvs);
        } else {
            std::cout << "Could not find IndvsOmopSumstatsFile path from config file " << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    // print first 5 elements
    std::cout << "Printing first 5 elements from the individuals summary statistics file" << std::endl;
    int i = 0;
    for (auto const &indv : indvs_omop_sumstats) {
        std::cout << indv.first;
        int j = 0;
        for(auto const &omop : indv.second) {
            int k = 0;
            std::cout << omop.first << " : ";
            for(auto const &sumstat : omop.second) {
                std::cout << " -> " << sumstat.first << " : " << sumstat.second << " ";
                k++; if(k == 5) break;
            }
            std::cout << endl;
            j++; if(j == 5) break;
        }
        i++; if (i == 5) break;
    }
}

std::string get_indvs_omop_sumstats_file_path(std::unordered_map<std::string, std::string> &configs) {
    std::string indvs_omop_sumstats_file_path = concat_string(std::vector<std::string>({configs["ResDirPath"], configs["ResFilePrefix"], std::string("indvs_omop_sumstats.csv")}));
    return(indvs_omop_sumstats_file_path);
}

std::vector<std::string> read_relevant_sumstats_from_config(std::unordered_map<std::string, std::string> &configs) {
    std::vector<std::string> relevant_sumstats;
    //if(configs.find("OutputEventCount") != configs.end()) relevant_sumstats.push_back("nelems");
    //if(configs.find("OutputBinary") != configs.end()) relevant_sumstats.push_back("binary");
    if(configs.find("RelevantSumstats") != configs.end()) {
        std::vector<std::string> relevant_sumstats_vec(split(configs["RelevantSumstats"], " "));
        for(std::string sumstat: relevant_sumstats_vec) {
            boost::to_upper(sumstat); // Casting to upper case
            relevant_sumstats.push_back(sumstat);
        }
    }
    return(relevant_sumstats);
}