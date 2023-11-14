#include <fstream>
#include <sstream>
#include <iostream>
#include <string>
#include <vector>
#include <regex>
#include <unordered_map>
#include <unordered_set>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <boost/date_time/gregorian/gregorian.hpp>

using namespace std;
using namespace boost::gregorian;

// Helper functions
std::vector<std::string> split(const std::string &s, const char *delim);
std::string concat_string(const std::vector<std::string> &elems, std::string sep = std::string(""));
std::string concat_string(const std::unordered_set<string> &elems, std::string sep = std::string(""));
void check_out_open(std::ofstream &file_stream, std::string file_path);
void check_in_open(std::ifstream &file_stream, std::string file_path);
std::string to_lower(std::string str);
std::string remove_chars(std::string str, char remove_char);
std::string get_omop_identifier(std::string lab_id,
                                std::string lab_abbreviation,
                                std::string lab_unit,
                                std::string sep);
std::vector<std::string> splitString(const std::string &input, 
                                     char delimiter);
char find_delim(std::string file_path);
void write_line_update(int n_lines, 
                       std::chrono::steady_clock::time_point &begin,
                       int line_limit=10000000);
void write_end_run_summary(std::chrono::steady_clock::time_point &begin);
void check_and_fix_last_char(std::string &str, char last_char);
void add_quotation(std::string &str);

// Config file functions
void read_config_file(std::string config_path,
                      std::unordered_map<std::string, std::string> &configs);
void read_indvs_date_file_from_config(std::unordered_map<std::string, std::string> &configs,
                              std::unordered_map<std::string, std::tuple<date, date>> &relevant_indvs,
                              int stop_if_not_found);
void read_indvs_file_from_config(std::unordered_map<std::string, std::string> &configs,
                                          std::unordered_set<std::string> &relevant_indvs,
                                          int stop_if_not_found);
void read_omops_file_from_config(std::unordered_map<std::string, std::string> &configs,
                                 std::unordered_set<std::string> &relevant_omops,
                                 int stop_if_not_found);
void read_indvs_omop_sumstats_from_config(std::unordered_map<std::string, std::string> &configs,
                                          std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string,  std::string>>> &indvs_omop_sumstats,
                                          std::unordered_set<std::string> &relevant_omops,
                                          std::unordered_set<std::string> &relevant_indvs);
std::vector<std::string> read_relevant_sumstats_from_config(std::unordered_map<std::string, std::string> &configs);
std::string get_indvs_omop_sumstats_file_path(std::unordered_map<std::string, std::string> &configs);

// Writing functions
void write_omop_sumstats(std::unordered_map<std::string, std::vector<double>> &omops,
                         std::unordered_map<std::string, std::unordered_set<std::string>> &omop_indvs,
                         std::string res_dir_path,
                         std::string res_file_prefix,
                         int min_counts = 0);
void write_indvs_omops_sumstats(std::unordered_map<std::string, std::unordered_map<std::string, std::vector<double>>> &indvs_omops_values,
                                std::unordered_map<std::string, std::string> &configs);
void write_relevant_sumstats_files( std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string, std::string>>> &indvs_omop_sumstats,
                                    std::vector<std::string> &relevant_sumstats,
                                    std::unordered_set<std::string> &relevant_omops,
                                    std::string res_dir_path,
                                    std::string res_file_prefix);

// Reading files functions
void read_indvs_date_file(std::unordered_map<std::string, std::tuple<date, date>> &relevant_indvs,
                      std::string indvs_path);
void read_indvs_file(std::unordered_set<std::string> &relevant_indvs,
                      std::string indvs_path);
void read_omops_file(std::unordered_set<std::string> &relevant_omops,
                     std::string omops_path);
void read_indvs_omops_sumstats(std::string indvs_omops_sumstats_path,
                               std::unordered_map<std::string, std::unordered_map<std::string, std::unordered_map<std::string, std::string>>> &indvs_omop_sumstats,
                               std::unordered_set<std::string> &relevant_omops,
                               std::unordered_set<std::string> &relevant_indvs);

// Math helper function
double get_mean(std::vector<double> values_vec);
double get_median(std::vector<double> values_vec);
double get_sd(std::vector<double> values_vec, double mean);
double get_quantile(std::vector<double> values, double quantile);
