# Architectural Rationale: Design Decisions and Justifications

## Purpose of This Document

This document explains **why** each component is designed the way it is. Every architectural choice has a rationale grounded in theory, validated mechanisms, or methodological necessity.

---

## System-Level Architecture

### Decision: Two-Domain System (State + Agent) for Tier 1

**Rationale**:
1. **Minimal Viable Test**: Tests arousal integration hypothesis with simplest possible case
2. **Domain Separability**: Navigation (State) and social assessment (Agent) are maximally distinct
3. **Computational Tractability**: Two modules manageable for hyperparameter search
4. **Clear Failure Mode**: If 2-domain doesn't work, 3-domain won't either

**Alternatives Considered**:
- **Single domain**: Can't test integration (no integration needed)
- **Three domains immediately**: Too many confounds, expensive to debug
- **Four+ domains**: Premature; validate basic concept first

**Risk**: Might not generalize to 3+ domains  
**Mitigation**: Explicitly document as Tier 1 limitation; scale in Tier 2 if successful

---

## Environment Design

### Decision: SimpleSocialGridWorld with Forced Interaction

**Key Design Features**:
1. Grid size: 5x5
2. NPC position: (2,2) - center of grid
3. Goal position: (4,4) - opposite corner
4. NPC mood changes: Every 75 episodes

#### Rationale: Grid Size (5x5)

**Why small?**
- Q-learning requires tabular state space: 5×5 positions = 25 states (tractable)
- Combined with NPC states: ~150 total states (learnable in <200 episodes)
- Large enough to require multiple steps to reach goal
- Small enough for exhaustive hyperparameter search

**Why not larger?**
- 10×10 grid = 10,000 combined states → requires function approximation (DQN)
- DQN adds confounds: network architecture, replay buffer tuning, etc.
- Tier 1 isolates arousal mechanism; function approximation is Tier 2 concern

#### Rationale: NPC Position (2,2)

**Critical Design Requirement**: Agent must interact with NPC to learn optimal policy.

**Why center placement?**
- Shortest path from random start to goal (4,4) likely passes near (2,2)
- Can't easily route around NPC (grid too small for long detours)
- Forces decision: "Should I interact to learn mood, or risk hostile encounter?"

**Why not other positions?**
- Corner: Easy to avoid entirely (undermines Agent domain necessity)
- Goal-adjacent: Forced interaction every episode (no strategic choice)
- Center: Optimal balance of unavoidability and strategic decision-making

#### Rationale: Mood Change Frequency (75 Episodes)

**Ty's original suggestion**: ~75 episodes per mood change

**Why this frequency?**
- **Too frequent** (e.g., every 10 episodes): Agent never converges before mood changes
- **Too infrequent** (e.g., every 500 episodes): Doesn't test adaptation within training
- **75 episodes**: 2-3 mood changes per typical training run (~200 episodes)

**What this tests**:
- Does arousal enable faster re-learning when environment changes?
- PVT advantage increased under stress - mood changes create temporal stress

#### Rationale: Reward Structure

**Reward values chosen for specific behavioral shaping**:

| Event | Reward | Rationale |
|-------|--------|-----------|
| Goal reached | +10 | Primary objective; must be large enough to drive exploration |
| Step cost | -0.1 | Efficiency incentive; small enough to not dominate goal reward |
| Hostile NPC | -5 | Major penalty; 2 hostile interactions ≈ one goal reward lost |
| Friendly NPC | +1 | Minor bonus; encourages interaction but not exploitation |
| Wall collision | -1 | Navigation error signal; more than step cost, less than hostile NPC |

**Design Philosophy**: Multiple reward sources with different magnitudes create genuine domain conflict:
- State domain optimizes: shortest path, avoid walls
- Agent domain optimizes: assess mood, avoid hostile, seek friendly
- Integration challenge: balance efficiency vs. social caution

---

## Arousal System Design

### Decision: PVT-Inspired Arousal Formula

**Formula**:
```
arousal = base × surprise_boost × salience_boost × stress_penalty

surprise_boost = 1 + (|prediction_error| × surprise_sensitivity)
salience_boost = 1 + (|reward| × salience_sensitivity)
stress_penalty = 1 / (1 + ((arousal - threshold) / threshold)²)
```

#### Rationale: Multiplicative (Not Additive) Combination

**Why multiply components?**
- Arousal should spike when surprise AND salience are BOTH high
- Additive: Large surprise + small salience = high arousal (incorrect)
- Multiplicative: Large surprise + small salience = moderate arousal (correct)

**Biological grounding**:
- PVT integrates multiple information streams non-linearly
- Inverted-U (Yerkes-Dodson) requires non-linear relationship

#### Rationale: Stress Penalty (Inverted-U)

**Why include stress penalty?**
- Extreme arousal impairs performance (biological finding)
- Prevents runaway arousal positive feedback
- Tested in your pvt-inspired-ai validation

**Mathematical form**:
- Quadratic penalty: smooth degradation, no sharp cutoff
- Threshold parameter: tunable per domain (some domains tolerate higher arousal)

#### Rationale: Domain-Specific Arousal Monitors

**Why separate monitors for State and Agent?**
1. **Credit assignment**: Navigation errors shouldn't spike Agent arousal
2. **Differential sensitivity**: Domains might have different arousal thresholds
3. **Independent dynamics**: State arousal might decay faster than Agent arousal

**Alternative considered**: Global arousal pool
**Rejected because**: Can't distinguish which domain needs updating

---

## Integration Layer Design

### Decision: Two Integration Strategies (Weighted + Gated)

#### Strategy 1: Weighted Integration (Softmax)

**Formula**:
```
weights = softmax([arousal_state, arousal_agent] / temperature)
Q_integrated = weights[0] * Q_state + weights[1] * Q_agent
```

**Rationale**:
- **Continuous**: Smooth transitions between domain priorities
- **Differentiable**: Could enable gradient-based meta-learning (future work)
- **Temperature tunable**: Controls integration smoothness

**When this should work**:
- Both domains provide partial information
- Optimal action is compromise between domain recommendations
- Example: Navigate toward goal but avoid NPC if hostile

#### Strategy 2: Gated Integration (Winner-Take-All)

**Formula**:
```
if |arousal_state - arousal_agent| > threshold:
    winner = argmax([arousal_state, arousal_agent])
    weights = [1, 0] or [0, 1]
else:
    weights = [0.5, 0.5]
```

**Rationale**:
- **Discrete**: Models attention as resource allocation (can't attend to both)
- **Efficient**: Simpler computation, no softmax
- **Biological**: Winner-take-all consistent with attention literature

**When this should work**:
- One domain clearly more important than other
- Optimal action comes from single domain recommendation
- Example: If hostile NPC, Agent domain should dominate completely

**Testing both because**:
- Unclear which is biologically accurate
- Might depend on task structure
- Empirical question: which performs better?

---

## Agent Architecture Decisions

### Decision: Q-Learning (Tabular) for Tier 1

**Why Q-learning?**
1. **Simplicity**: Easy to understand, debug, analyze
2. **Proven**: Decades of theory and empirical validation
3. **Transparent**: Can inspect Q-tables directly
4. **Baseline**: Standard for discrete action spaces

**Why tabular (not function approximation)?**
1. **Small state space**: 150 states manageable with tables
2. **Convergence guarantees**: Tabular Q-learning provably converges
3. **No confounds**: No network architecture, replay buffer, target network decisions

**Limitations acknowledged**:
- Doesn't scale to large/continuous spaces
- No generalization across states
- Not how modern RL works (DQN, PPO, etc.)

**Tier 2 plan**: Upgrade to function approximation if Tier 1 succeeds

### Decision: ε-Greedy Exploration with Arousal Modulation

**Formula**:
```
ε_effective = base_ε × (1 + arousal)
```

**Rationale**:
- High arousal → uncertain environment → explore more
- Low arousal → confident in policy → exploit more
- Validated in your pvt-inspired-ai project

**Alternative considered**: Boltzmann exploration
**Rejected because**: ε-greedy simpler, well-understood, sufficient for Tier 1

---

## Experimental Design Decisions

### Decision: Three Architectures (A, B, C)

**Architecture A: Monolithic PVT**
- **Purpose**: Baseline with arousal modulation
- **Tests**: Whether global arousal helps at all

**Architecture B: Separate-Manual**
- **Purpose**: Control for modularity alone
- **Tests**: Whether specialization helps without arousal integration

**Architecture C: Integrated-Arousal**
- **Purpose**: Full hypothesis test
- **Tests**: Whether arousal-weighted integration is the critical factor

**Why all three?**
- Compare C vs. A: Tests modularity + arousal
- Compare C vs. B: Tests arousal integration specifically
- Compare B vs. A: Tests modularity alone

**Design pattern**: Factorial experiment

### Decision: Hyperparameter Search Strategy

**Grid search over**:
```
learning_rate: [0.01, 0.05, 0.1]
arousal_sensitivity: [0.1, 0.5, 1.0]
discount_factor: [0.9, 0.95, 0.99]
```
= 27 configurations per architecture

**Why grid search (not random/Bayesian)?**
1. **Interpretability**: Know exactly what was tested
2. **Reproducibility**: Same grid for all architectures
3. **Fair comparison**: Equal search budget for each
4. **Small space**: 27 configs feasible

**Why these parameters?**
- **learning_rate**: Standard range for Q-learning
- **arousal_sensitivity**: Controls arousal magnitude effect
- **discount_factor**: Balances immediate vs. future rewards

### Decision: N=20 Seeds

**Why 20?**
- **Statistical power**: Sufficient for detecting medium effect sizes (d=0.5) with 80% power
- **Computational feasibility**: 20 × 27 configs × 3 architectures = 1620 runs (~2 days)
- **Standard practice**: Many RL papers use 10-30 seeds

**Why not more?**
- Diminishing returns: 50 seeds → marginal power increase, 2.5× cost
- Phase gating: If results clearly fail, abort rather than run all seeds

**Why not fewer?**
- N=10 underpowered for small effects
- N=5 high variance, unreliable

### Decision: Mann-Whitney U Test (Not t-test)

**Why non-parametric?**
- Episode counts often non-normal (right-skewed)
- Sample size modest (N=20)
- U-test robust to outliers

**Significance threshold**: α = 0.05 (standard)
**Effect size**: Report Cohen's d (interpret regardless of p-value)

---

## Metric Selection Rationale

### Primary Metrics

**M1: Convergence Speed** (episodes to 95% max performance)
- **Why episodes (not steps)?** Captures learning efficiency per experience
- **Why 95% (not 90% or 99%)?** Balance between strict and lenient
- **Alternative**: Time to first optimal episode (too noisy)

**M2: Sample Efficiency** (total steps to convergence)
- **Why include?** Distinguishes fast episodes from efficient learning
- **Alternative**: Total reward accumulated (confounds exploration vs. exploitation)

**M3: Final Performance** (mean reward, last 100 episodes)
- **Why last 100?** Sufficient sample for reliable estimate
- **Alternative**: Best episode ever (too noisy, lucky runs)

### Secondary Metrics

**M4: Arousal Conflict Rate**
- **Threshold**: Both arousals > 0.7
- **Why 0.7?** High enough to indicate genuine conflict, not noise
- **Purpose**: Tests whether integration faces impossible dilemmas

**M5: Error Attribution Correlation**
- **Measure**: Pearson correlation between prediction errors and arousal deltas
- **Purpose**: Validates that arousal tracks domain-specific errors
- **Expected**: r > 0.7 if mechanism working correctly

**M6: Computational Cost**
- **Training time**: Wall-clock seconds to convergence
- **Inference time**: Milliseconds per action selection
- **Purpose**: Practical feasibility check

---

## Success/Failure Criteria Rationale

### Success Criterion C1: >10% Convergence Improvement

**Why 10%?**
- **Practical significance**: Meaningfully faster in real applications
- **Statistical detectability**: Effect size d ≈ 0.5-0.7 (medium-large)
- **Cost justification**: Integration overhead worth 10% gain

**Alternative thresholds considered**:
- **5%**: Too small; might be noise or implementation artifact
- **20%**: Too strict; excludes valuable but modest improvements

### Failure Criterion F4: Training Time >3x Baseline

**Why 3x (not 2x)?**
- **C4 allows 2x**: This is outer boundary for complete failure
- **Rationale**: If integration takes 3× longer to train AND doesn't converge faster, architecture is strictly worse

---

## Ablation Study Rationale

### Ablation A: Fixed-Weight Integration

**Purpose**: Test if arousal *dynamics* matter

**Hypothesis**:
- If fixed 50/50 weights ≈ arousal-weighted: Dynamics don't matter
- If fixed weights < arousal-weighted: Dynamics are critical

### Ablation B: Random-Weight Integration

**Purpose**: Test if integration *weights* matter at all

**Hypothesis**:
- If random ≈ arousal-weighted: Weights irrelevant (modularity alone sufficient)
- If random < arousal-weighted: Weighting strategy matters

### Ablation C: Arousal-Logging-Only

**Purpose**: Test if arousal signal is informative but unused in baseline

**Hypothesis**:
- If monolithic with logging ≈ monolithic without: Arousal not informative
- If monolithic with logging < monolithic without: Signal is available but not exploited

---

## Design Philosophy Summary

Every decision reflects core principles:

1. **Isolation of Variables**: Control all confounds to isolate arousal mechanism
2. **Biological Grounding**: Design choices reflect validated neuroscience
3. **Computational Pragmatism**: Tractable implementation for rapid iteration
4. **Statistical Rigor**: Sufficient power to detect effects, avoid false positives
5. **Conservative Scaling**: Validate simple case before adding complexity

**Core Belief**: Good science requires explicit rationales. Every choice has reasons. Some will be wrong. Data will tell us which.

---

## Anticipated Criticisms and Responses

**Criticism 1**: "Environment too simple to be meaningful"
**Response**: Tier 1 is proof-of-concept. If mechanism fails in simple case, it won't work in complex cases. Scaling is Tier 2+.

**Criticism 2**: "State/Agent split is arbitrary"
**Response**: Designed to be maximally separable for Tier 1. Future work: learned decomposition.

**Criticism 3**: "Q-learning is outdated"
**Response**: Modern RL (DQN, PPO) adds confounds. Q-learning isolates arousal mechanism. Function approximation in Tier 2.

**Criticism 4**: "N=20 is small"
**Response**: Sufficient power for medium effects. If true effect is small, we want to know (might not be practically valuable).

**Criticism 5**: "Only tests one task type"
**Response**: Correct. This is Tier 1. Generalization testing is Tier 2-3.

---

## Future Architecture Evolution

### Tier 2 Additions (If Tier 1 Passes)
- Add Action domain (full DMN architecture)
- Implement affective memory
- Function approximation (DQN)
- Continuous state spaces

### Tier 3 Additions (If Tier 2 Passes)
- Real LLM modules (not toy Q-learners)
- Complex tasks (coding, planning, conversation)
- Transfer learning tests
- Temporal coding integration

**Guardrail**: Each tier must pass strict criteria before proceeding. No wishful thinking.

---

## Conclusion

This architecture embodies **conservative empiricism**: test the simplest possible instantiation of the hypothesis with maximum methodological rigor. If it works, scale carefully. If it fails, we learn why and iterate.

Every design choice reflects trade-offs between biological plausibility, computational tractability, and experimental control. Some choices will prove suboptimal. That's fine - this is science, not engineering. We're testing a hypothesis, not building a product.

**Next**: Run the tests. Let data decide.
