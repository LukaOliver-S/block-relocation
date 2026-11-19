#include "astar.h"

#include <chrono>
#include <cmath>
#include <queue>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

extern bool verbose;

namespace {
// Keep stack identities: the stored history refers to their original indices.
// Delimiters make this encoding unambiguous, including empty stacks.
std::string keyFor(const BRPState &state) {
    std::ostringstream key;
    key << state.next() << ':';
    for (const auto &stack : state.stacks()) {
        for (int item : stack) {
            key << item << ',';
        }
        key << ';';
    }
    return key.str();
}

struct Node {
    std::shared_ptr<BRPState> state;
    std::string key;
    unsigned int g;
    unsigned long long f;
    unsigned long long serial;
};

struct Later {
    bool operator()(const Node &a, const Node &b) const {
        if (a.f != b.f) return a.f > b.f;
        if (a.g != b.g) return a.g < b.g;
        return a.serial > b.serial;
    }
};
}

AStar::AStar(double timeLimitSeconds) : timeLimitSeconds_(timeLimitSeconds) {
    if (!std::isfinite(timeLimitSeconds) || timeLimitSeconds < 0) {
        throw std::invalid_argument("ASTAR: time limit must be finite and nonnegative");
    }
}

std::shared_ptr<BRPState> AStar::solve(const BRPState &initialState) const {
    const auto started = std::chrono::steady_clock::now();
    const auto checkTime = [&]() {
        if (timeLimitSeconds_ > 0 &&
            std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count()
                >= timeLimitSeconds_) {
            throw AStarTimeout();
        }
    };
    std::priority_queue<Node, std::vector<Node>, Later> open;
    std::unordered_map<std::string, unsigned int> bestG;
    unsigned long long serial = 0;
    unsigned long long prunedByUB = 0;

    // Build a feasible RESTRICTED incumbent with the base policy's destination
    // rule (Min-Max). Do not use ubSolver: it may allow voluntary relocations.
    auto incumbent = std::make_shared<BRPState>(initialState);
    while (!incumbent->empty()) {
        checkTime();
        if (incumbent->retrieveNext()) continue;
        const int from = incumbent->stackForItem(incumbent->next());
        const unsigned int to = bestDestForLaRelocate(*incumbent, incumbent->top(from));
        if (to >= static_cast<unsigned int>(incumbent->W())) {
            // Greedy failure does not prove infeasibility. Search without a UB.
            incumbent.reset();
            break;
        }
        incumbent->relocate(from, to);
    }
    if (verbose) {
        if (incumbent) std::cout << "ASTAR initial UB = " << incumbent->nRelocations() << '\n';
        else std::cout << "ASTAR initial UB unavailable\n";
    }

    const auto enqueue = [&](std::shared_ptr<BRPState> state) {
        // Retrievals cost zero and never hurt feasibility in the BRP.
        while (state->retrieveNext()) checkTime();
        const unsigned int g = state->nRelocations();
        // Every blocking block needs at least one relocation: admissible LB1.
        const auto f = static_cast<unsigned long long>(g) + state->LB1();
        if (incumbent && f >= incumbent->nRelocations()) {
            ++prunedByUB;
            return;
        }
        if (state->empty()) {
            incumbent = state;
            return;
        }
        std::string key = keyFor(*state);
        auto found = bestG.find(key);
        if (found != bestG.end() && found->second <= g) return;
        bestG[key] = g;
        open.push(Node{state, std::move(key), g, f, serial++});
    };

    enqueue(std::make_shared<BRPState>(initialState));
    while (!open.empty()) {
        checkTime();
        Node current = open.top();
        open.pop();
        if (bestG.at(current.key) != current.g) continue;
        // A better incumbent can make previously queued nodes unpromising.
        // Since this is the smallest f, no remaining node can improve the UB.
        if (incumbent && current.f >= incumbent->nRelocations()) {
            prunedByUB += open.size() + 1;
            break;
        }

        // Restricted: only the top blocker of the next retrieval target moves.
        const int from = current.state->stackForItem(current.state->next());
        for (int to = 0; to < current.state->W(); ++to) {
            checkTime();
            if (from == to || current.state->height(to) >= current.state->H()) continue;
            auto child = std::make_shared<BRPState>(*current.state);
            child->relocate(from, to);
            enqueue(child);
        }
    }
    if (verbose) std::cout << "ASTAR pruned by UB = " << prunedByUB << '\n';
    // The feasible incumbent is now proven optimal; nullptr means infeasible.
    return incumbent;
}
