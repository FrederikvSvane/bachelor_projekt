#ifndef test_data_generator_hpp
#define test_data_generator_hpp

#include "json.hpp"
#include <cmath>
#include <random>

using json = nlohmann::json;
using namespace std;
namespace test_data_generator {

// we create this because we want a special normal distribution.
// the duration of meetings are distributed between [5, 360] minutes
// with most of them being 30 min. We generate numbers that adhere to this distribution by creating
// a normal distribution with mean=30, sd=80 and truncating it at 5 and 360.
// we then apply some neat CDF, error and inverse error function math to transform the truncated normal dist
// into a valid normal dist with a total area under the curve that =1.
    class TruncatedNormalDistribution {
    private:
        double mu;    // mean
        double sigma; // standard deviation
        double a;     // lower bound
        double b;     // upper bound
        std::uniform_real_distribution<double> uniform{0.0, 1.0};

        float
        erfinv(float x) { // snupset direkte fra https://stackoverflow.com/questions/27229371/inverse-error-function-in-c
            float tt1, tt2, lnx, sgn;
            sgn = (x < 0) ? -1.0f : 1.0f;

            x = (1 - x) * (1 + x); // x = 1 - x*x;
            lnx = logf(x);

            tt1 = 2 / (M_PI * 0.147) + 0.5f * lnx;
            tt2 = 1 / (0.147) * lnx;

            return (sgn * sqrtf(-tt1 + sqrtf(tt1 * tt1 - tt2)));
        }

        // Standard normal CDF
        double standard_normal_cdf(double x) {
            return 0.5 * (1 + std::erf(x / std::sqrt(2.0)));
        }

        // Inverse CDF method for sampling
        double sample(std::mt19937 &gen) {
            double alpha = standard_normal_cdf((a - mu) / sigma);
            double beta = standard_normal_cdf((b - mu) / sigma);

            // uniform random number between alpha and beta
            double u = uniform(gen) * (beta - alpha) + alpha;

            // return the inverse CDF (using the inverse error function)
            return mu + sigma * std::sqrt(2.0) * erfinv(2.0 * u - 1.0);
        }

    public:
        TruncatedNormalDistribution(double mean, double stddev, double min, double max)
                : mu(mean), sigma(stddev), a(min), b(max) {}

        double operator()(
                std::mt19937 &gen) { // this enables generating a number from the dist simply by TruncatedNormalDist(gen)
            return sample(gen);
        }
    };

    static random_device rd;
    static mt19937 gen(rd()); // for generating random int between 0 and UINT32_MAX

    static TruncatedNormalDistribution duration_dist(30.0, 80.0, 5.0, 360.0);

    int generate_duration() {
        double raw_duration = duration_dist(gen);
        return static_cast<int>(round(raw_duration / 5.0) * 5); // round to nearest 5
    }

    inline Sagstype generate_sagstype() {
        int randomVal = gen() % 3;
        switch (randomVal) {
            case 0:
                return Sagstype::Straffe;
            case 1:
                return Sagstype::Civile;
            default:
                return Sagstype::Tvang;
        }
    }

    std::vector<Sagstype> generate_judge_skills(int num_skills = 2) {
        std::vector<Sagstype> skills;
        std::vector<Sagstype> all_types = {Sagstype::Straffe, Sagstype::Civile, Sagstype::Tvang};

        // Shuffle the types to get random but unique skills
        std::shuffle(all_types.begin(), all_types.end(), gen);

        // Take the first num_skills elements (default 2)
        for (int i = 0; i < std::min(num_skills, static_cast<int>(all_types.size())); i++) {
            skills.push_back(all_types[i]);
        }

        return skills;
    }


    json generate_fixed_meetings(int n, int fixed_duration) {
        json meetings = json::array();
        for (int i = 1; i <= n; i++) {
            meetings.push_back({{"id",       i},
                                {"duration", fixed_duration},
                                {"sagstype", generate_sagstype()},
                                {"virtual",  false}});
        }
        return meetings;
    }

    json generate_random_meetings(int n) {
        json meetings = json::array();
        for (int i = 1; i <= n; i++) {
            meetings.push_back({{"id",       i},
                                {"duration", generate_duration()}});
        }
        return meetings;
    }

    json generate_judges(int n) {
        json judges = json::array();
        for (int i = 1; i <= n; i++) {
            std::vector<Sagstype> judge_skills = generate_judge_skills();

            judges.push_back({{"id", i,},
                              {"skills", {judge_skills[0], judge_skills[1]}},
                              {"virtual", false}});
        }
        return judges;
    }

    json generate_court_rooms(int n) {
        json rooms = json::array();
        for (int i = 1; i <= n; i++) {
            rooms.push_back({{"id", i},
                             {"virtual", false}});
        }
        return rooms;
    }

    json generate_constraints() {
        json constraints;
        json hard = json::array();
        json soft = json::array();

        // for now all constraints as true
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

        request["meetings"] = normal_request ? generate_random_meetings(n_meetings) : generate_fixed_meetings(
                n_meetings, granularity);
        request["Judges"] = generate_judges(n_judges);
        request["CourtRooms"] = generate_court_rooms(n_rooms);
        request["work_days"] = num_days;
        request["granularity"] = granularity;
        request["min_per_work_day"] = min_pr_day;

        json constraints = json::array();
        constraints.push_back(generate_constraints());
        request["constraints"] = constraints;

        return request;
    }

} // namespace test_data_generator
#endif