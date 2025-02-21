#ifndef test_data_generator_hpp
#define test_data_generator_hpp

#include "json.hpp"
#include <cmath>
#include <random>

using json = nlohmann::json;
using namespace std;
namespace test_data_generator {

class TruncatedNormalDistribution {
  private:
    double mu;    // mean
    double sigma; // standard deviation
    double a;     // lower bound
    double b;     // upper bound
    std::uniform_real_distribution<double> uniform{0.0, 1.0};

    float erfinv(float x){ // snupset direkte fra https://stackoverflow.com/questions/27229371/inverse-error-function-in-c
        float tt1, tt2, lnx, sgn;
        sgn = (x < 0) ? -1.0f : 1.0f;
     
        x = (1 - x)*(1 + x);        // x = 1 - x*x;
        lnx = logf(x);
     
        tt1 = 2/(M_PI*0.147) + 0.5f * lnx;
        tt2 = 1/(0.147) * lnx;
     
        return(sgn*sqrtf(-tt1 + sqrtf(tt1*tt1 - tt2)));
     }

    // Standard normal CDF (Phi function)
    double standard_normal_cdf(double x) {
        return 0.5 * (1 + std::erf(x / std::sqrt(2.0)));
    }

    // Inverse CDF method for sampling
    double sample(std::mt19937& gen) {
        // Calculate Phi((a-mu)/sigma) and Phi((b-mu)/sigma)
        double alpha = standard_normal_cdf((a - mu) / sigma);
        double beta  = standard_normal_cdf((b - mu) / sigma);

        // Generate uniform random number between alpha and beta
        double u = uniform(gen) * (beta - alpha) + alpha;

        // Return inverse CDF
        return mu + sigma * std::sqrt(2.0) * erfinv(2.0 * u - 1.0);
    }

  public:
    TruncatedNormalDistribution(double mean, double stddev, double min, double max)
        : mu(mean), sigma(stddev), a(min), b(max) {}

    double operator()(std::mt19937& gen) {
        return sample(gen);
    }
};


static random_device rd;
static mt19937 gen(rd());

static TruncatedNormalDistribution duration_dist(30.0, 180.0, 5.0, 360.0);


int generate_duration() {
    double raw_duration = duration_dist(gen);
    return static_cast<int>(round(raw_duration / 5.0) * 5); // round to nearest 5
}

json generate_fixed_meetings(int n, int fixed_duration) {
    json meetings = json::array();
    for (int i = 1; i <= n; i++) {
        meetings.push_back({{"id", i},
                            {"duration", fixed_duration}});
    }
    return meetings;
}

json generate_random_meetings(int n) {
    json meetings = json::array();
    for (int i = 1; i <= n; i++) {
        meetings.push_back({{"id", i},
                            {"duration", generate_duration()}});
    }
    return meetings;
}

json generate_judges(int n) {
    json judges = json::array();
    for (int i = 1; i <= n; i++) {
        judges.push_back({{"id", i}});
    }
    return judges;
}

json generate_court_rooms(int n) {
    json rooms = json::array();
    for (int i = 1; i <= n; i++) {
        rooms.push_back({{"id", i}});
    }
    return rooms;
}

json generate_constraints() {
    json constraints;
    json hard = json::array();
    json soft = json::array();

    // Always add all constraints as true
    hard.push_back({{"no overlaps", true}});
    hard.push_back({{"coverage", true}});
    soft.push_back({{"judge movement", true}});

    constraints["hard"] = hard;
    constraints["soft"] = soft;

    return constraints;
}

json generate_request(
    int n_meetings,
    int n_judges,
    int n_rooms,
    int num_days,
    int granularity,
    int min_pr_day,
    bool normal_request = true) {
    json request;

    // Generate meetings based on type
    request["meetings"] = normal_request ? generate_random_meetings(n_meetings) : generate_fixed_meetings(n_meetings, granularity);

    request["Judges"]      = generate_judges(n_judges);
    request["CourtRooms"]  = generate_court_rooms(n_rooms);
    request["work_days"]    = num_days;
    request["granularity"] = granularity;
    request["min_per_work_day"]  = min_pr_day;

    // Generate constraints with default probabilities
    json constraints = json::array();
    constraints.push_back(generate_constraints());
    request["constraints"] = constraints;

    return request;
}

} // namespace test_data_generator
#endif