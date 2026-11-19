#ifndef ASTAR_H
#define ASTAR_H

#include <stdexcept>
#include "brppolicy.h"

class AStarTimeout : public std::runtime_error {
public:
    AStarTimeout() : std::runtime_error("ASTAR: time limit reached; optimality not proven") {}
};

// Exact A* for the restricted BRP, with LB1 and a feasible greedy upper bound.
// Only blockers of the next target can be relocated. Zero time means unlimited.
// Returns nullptr only when the state space is exhausted (infeasible).
// Throws AStarTimeout on timeout, rather than returning a partial solution.
class AStar : public BRPPolicy {
public:
    explicit AStar(double timeLimitSeconds = 0);
    std::string name() const override { return "ASTAR"; }
    std::shared_ptr<BRPState> solve(const BRPState &initialState) const override;

private:
    double timeLimitSeconds_;
};

#endif
