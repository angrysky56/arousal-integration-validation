# Arousal Integration Validation - Tier 1

**Status**: 🚧 Implementation in progress
**Goal**: Validate arousal-weighted integration hypothesis in minimal two-domain setting

## Experimental Hypothesis

**H₁**: Arousal-weighted integration of domain-specific modules enables faster convergence than:
- Monolithic agents with global arousal
- Modular agents with fixed integration rules

## Project Structure

```
arousal-integration-validation/
├── src/
│   ├── environment/
│   │   └── social_gridworld.py      # SimpleSocialGridWorld implementation
│   ├── agents/
│   │   ├── base.py                  # Abstract base agent
│   │   ├── monolithic.py            # Architecture A: Monolithic PVT
│   │   ├── separate_manual.py       # Architecture B: Fixed integration
│   │   └── integrated_arousal.py    # Architecture C: Arousal-weighted
│   ├── modules/
│   │   ├── state_module.py          # Navigation-specific PVT agent
│   │   └── agent_module.py          # Social-assessment PVT agent
│   └── utils/
│       ├── arousal.py               # Arousal computation utilities
│       └── metrics.py               # Measurement and analysis tools
├── experiments/
│   ├── run_baseline.py              # Phase 1: Baseline validation
│   ├── run_comparison.py            # Phase 3: Full comparison
│   └── run_ablations.py             # Phase 4: Ablation studies
├── analysis/
│   └── statistical_analysis.py      # Result analysis and visualization
└── tests/
    └── test_environment.py          # Environment validation

```

## Success Criteria (Tier 1)

**Must Pass All:**
1. **C1**: Architecture C converges >10% faster than A and B (p < 0.05)
2. **C2**: Final performance within 5% of baselines
3. **C3**: Arousal conflicts < 20% of timesteps
4. **C4**: Training time < 2x baseline, inference < 100ms

**Abort if Any:**
1. **F1**: No convergence benefit (p > 0.05)
2. **F2**: Performance degradation > 5%
3. **F3**: Variance 2x higher than baseline
4. **F4**: Training time > 3x baseline

## Implementation Phases

- [ ] **Phase 1**: Baseline (Week 1)
  - [ ] Environment implementation
  - [ ] Architecture A + hyperparameter search
  - [ ] Baseline performance (N=20 seeds)

- [ ] **Phase 2**: Control (Week 1-2)
  - [ ] Architecture B implementation
  - [ ] Parameter parity verification
  - [ ] Control performance (N=20 seeds)

- [ ] **Phase 3**: Experimental (Week 2)
  - [ ] Architecture C implementation (weighted + gated)
  - [ ] Full metric collection
  - [ ] Experimental results (N=20 seeds)

- [ ] **Phase 4**: Analysis (Week 2-3)
  - [ ] Ablation studies
  - [ ] Statistical analysis
  - [ ] Decision: Pass/Fail Tier 1

## Key Design Decisions

### Environment Configuration
- Grid size: 5x5
- NPC position: (2, 2) - forces interaction
- NPC mood changes: Every 75 episodes
- Episode timeout: 50 steps

### Arousal Sources
- **State domain**: Navigation errors, wall collisions, goal proximity
- **Agent domain**: Interaction outcomes, mood prediction errors
- **Global**: Time pressure (steps remaining)

### Integration Methods
1. **Weighted**: `Q = softmax([arousal_s, arousal_a]) · [Q_s, Q_a]`
2. **Gated**: Discrete selection based on arousal threshold

## Current Status

🚧 Scaffolding complete, beginning environment implementation

## Next Steps

1. Implement `SimpleSocialGridWorld` with mood dynamics
2. Verify environment is solvable (optimal policy exists)
3. Implement Architecture A baseline
4. Hyperparameter search and baseline validation
