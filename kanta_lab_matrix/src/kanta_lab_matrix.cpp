#include "header.h"


int main(int argc, char *argv[]) {
  std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
  
  std::string config_path = argv[1];
  std::unordered_map<std::string, std::string> configs;
  read_config_file(config_path, configs);
  
  std::unordered_set<std::string> relevant_indvs;
  read_indvs_file_from_config(configs, relevant_indvs, int(0));
  
  std::unordered_set<std::string> relevant_omops;
  read_omops_file_from_config(configs, relevant_omops, int(0));
  
  // Reading mean, median, min, max, sd, first quantile, third quantile, n_elems
  std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string, std::string>>> indvs_omop_sumstats;
  read_indvs_omop_sumstats_from_config(configs, indvs_omop_sumstats, relevant_omops, relevant_indvs);
  
  // List of sumstats we are interested in
  std::vector<std::string> relevant_sumstats = read_relevant_sumstats_from_config(configs);
  write_relevant_sumstats_files(indvs_omop_sumstats, relevant_sumstats, relevant_omops, configs["ResDirPath"], configs["ResFilePrefix"]);

  write_end_run_summary(begin);
}
