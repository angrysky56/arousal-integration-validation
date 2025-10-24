"""
Arousal Computation Framework

Conceptual Foundation:
    Implements PVT-inspired arousal modulation mechanisms for reinforcement learning.
    Arousal serves as a computational attention signal, dynamically allocating
    cognitive resources based on prediction errors, salience, and contextual factors.

Theoretical Grounding:
    Based on validated mechanisms from pvt-inspired-ai project:
    - Arousal ↑ with surprise (prediction error magnitude)
    - Arousal ↑ with threat/opportunity salience
    - Arousal ↑ with time pressure
    - Arousal ↓ with extreme stress (inverted-U relationship)

Methodological Design:
    Arousal formula: arousal = base × surprise_boost × salience_boost × stress_penalty

    Where:
    - surprise_boost = 1 + (prediction_error / error_scale)
    - salience_boost = 1 + (|reward| / reward_scale)
    - stress_penalty = 1 / (1 + stress^2)  # Inverted-U
"""

from typing import Protocol

import numpy as np


class ArousalConfig(Protocol):
    """
    Configuration interface for arousal computation.

    Design Rationale:
        Protocol rather than dataclass allows flexible implementation
        while maintaining type safety and explicit contracts.
    """
    base_arousal: float
    surprise_sensitivity: float
    salience_sensitivity: float
    stress_threshold: float
    time_pressure_factor: float


class ArousalMonitor:
    """
    Domain-specific arousal computation and tracking.

    Philosophical Commitment:
        We adopt an instrumentalist view of arousal - it is a computational
        signal for resource allocation, not a claim about phenomenology.

    Implementation Notes:
        - Each domain (State, Agent) maintains independent arousal
        - Arousal values in [0, 1] for comparability across domains
        - Historical tracking enables arousal dynamics analysis
    """

    def __init__(
        self,
        domain_name: str,
        base_arousal: float = 0.3,
        surprise_sensitivity: float = 0.5,
        salience_sensitivity: float = 0.3,
        stress_threshold: float = 0.8,
        time_pressure_factor: float = 0.2,
    ):
        """
        Initialize arousal monitor for specific domain.

        Args:
            domain_name: Identifier for this domain ("state" or "agent")
            base_arousal: Baseline arousal level (controls responsiveness)
            surprise_sensitivity: Weight for prediction error influence
            salience_sensitivity: Weight for reward magnitude influence
            stress_threshold: Point where stress begins impairing performance
            time_pressure_factor: Weight for temporal urgency

        Calibration Philosophy:
            Default values from pvt-inspired-ai validation, but domain-specific
            tuning may be necessary (tested in hyperparameter search).
        """
        self.domain = domain_name
        self.base = base_arousal
        self.surprise_sens = surprise_sensitivity
        self.salience_sens = salience_sensitivity
        self.stress_thresh = stress_threshold
        self.time_sens = time_pressure_factor

        # State tracking
        self.current_arousal = base_arousal
        self.arousal_history: list[float] = []

        # Component tracking (for analysis)
        self.surprise_component: list[float] = []
        self.salience_component: list[float] = []
        self.stress_component: list[float] = []

    def compute_arousal(
        self,
        prediction_error: float,
        reward_magnitude: float,
        time_remaining: float,
        max_time: float,
    ) -> float:
        """
        Compute current arousal level based on contextual factors.

        Conceptual Model:
            Arousal = f(surprise, salience, stress)

            Where:
            - Surprise: How unexpected was the outcome?
            - Salience: How important is this outcome?
            - Stress: Are we under excessive pressure?

        Args:
            prediction_error: Magnitude of prediction error (TD-error, etc.)
            reward_magnitude: Absolute value of reward received
            time_remaining: Steps remaining before timeout
            max_time: Maximum steps per episode

        Returns:
            Arousal level in [0, 1]

        Methodological Note:
            Each component is tracked separately for ablation analysis.
        """
        # Component 1: Surprise (prediction error magnitude)
        # Higher errors → more surprise → higher arousal
        surprise_boost = 1.0 + (abs(prediction_error) * self.surprise_sens)

        # Component 2: Salience (reward magnitude)
        # Larger rewards/penalties → more salient → higher arousal
        salience_boost = 1.0 + (abs(reward_magnitude) * self.salience_sens)

        # Component 3: Time pressure
        # Less time remaining → higher urgency → higher arousal
        time_fraction = time_remaining / max_time
        time_pressure = 1.0 + (1.0 - time_fraction) * self.time_sens

        # Component 4: Stress penalty (inverted-U)
        # Moderate arousal optimal; extreme arousal impairs
        raw_arousal = self.base * surprise_boost * salience_boost * time_pressure

        if raw_arousal > self.stress_thresh:
            # Apply stress penalty: 1 / (1 + excess^2)
            excess = (raw_arousal - self.stress_thresh) / self.stress_thresh
            stress_penalty = 1.0 / (1.0 + excess**2)
        else:
            stress_penalty = 1.0

        # Final arousal (clipped to [0, 1])
        arousal = np.clip(raw_arousal * stress_penalty, 0.0, 1.0)

        # Track components for analysis
        self.surprise_component.append(surprise_boost)
        self.salience_component.append(salience_boost)
        self.stress_component.append(stress_penalty)

        # Update state
        self.current_arousal = arousal
        self.arousal_history.append(arousal)

        return arousal

    def get_learning_rate_multiplier(
        self,
        base_lr: float,
        arousal: float | None = None,
    ) -> float:
        """
        Convert arousal to learning rate multiplier.

        Theoretical Foundation:
            High arousal → fast learning (capitalize on salient events)
            Low arousal → slow learning (stable background processing)

            Validated in pvt-inspired-ai: ~30% convergence improvement

        Args:
            base_lr: Baseline learning rate
            arousal: Current arousal (uses self.current_arousal if None)

        Returns:
            Modulated learning rate

        Implementation Note:
            Linear scaling: lr = base_lr * (1 + arousal)
            Could explore non-linear relationships in future work.
        """
        arousal_value = arousal if arousal is not None else self.current_arousal

        # Linear arousal modulation
        # arousal=0 → lr = base_lr
        # arousal=1 → lr = 2 * base_lr
        multiplier = 1.0 + arousal_value

        return base_lr * multiplier

    def get_exploration_bonus(
        self,
        base_epsilon: float,
        arousal: float | None = None,
    ) -> float:
        """
        Convert arousal to exploration rate.

        Theoretical Rationale:
            High arousal → more exploration (uncertain environment)
            Low arousal → more exploitation (confident in policy)

        Args:
            base_epsilon: Baseline exploration rate (ε-greedy)
            arousal: Current arousal (uses self.current_arousal if None)

        Returns:
            Modulated exploration rate
        """
        arousal_value = arousal if arousal is not None else self.current_arousal

        # Arousal increases exploration
        # arousal=0 → ε = base_epsilon
        # arousal=1 → ε = 2 * base_epsilon (capped at 1.0)
        exploration = base_epsilon * (1.0 + arousal_value)

        return np.clip(exploration, 0.0, 1.0)

    def reset(self) -> None:
        """Reset arousal to baseline (between episodes)."""
        self.current_arousal = self.base

    def get_statistics(self) -> dict[str, float]:
        """
        Compute summary statistics for analysis.

        Returns:
            Dictionary with mean, std, min, max arousal
        """
        if not self.arousal_history:
            return {
                "mean": self.base,
                "std": 0.0,
                "min": self.base,
                "max": self.base,
                "final": self.base,
            }

        return {
            "mean": float(np.mean(self.arousal_history)),
            "std": float(np.std(self.arousal_history)),
            "min": float(np.min(self.arousal_history)),
            "max": float(np.max(self.arousal_history)),
            "final": self.arousal_history[-1],
        }


class ArousalIntegrator:
    """
    Integration layer for multi-domain arousal signals.

    Conceptual Purpose:
        Implements the "Precuneus function" - selectively integrating
        parallel arousal streams to coordinate attention allocation.

    Integration Strategies:
        1. Weighted: Softmax over arousal values
        2. Gated: Discrete selection based on threshold

    Philosophical Question:
        Is weighted integration (continuous) or gated selection (discrete)
        more aligned with biological mechanisms? We test both empirically.
    """

    @staticmethod
    def weighted_integration(
        arousal_state: float,
        arousal_agent: float,
        temperature: float = 1.0,
    ) -> tuple[float, float]:
        """
        Compute attention weights via softmax over arousal values.

        Args:
            arousal_state: State domain arousal
            arousal_agent: Agent domain arousal
            temperature: Softmax temperature (higher = more uniform)

        Returns:
            (weight_state, weight_agent) summing to 1.0

        Methodological Note:
            Temperature parameter allows tuning integration smoothness.
            Will be optimized in hyperparameter search.
        """
        arousals = np.array([arousal_state, arousal_agent])

        # Softmax with temperature
        exp_arousals = np.exp(arousals / temperature)
        weights = exp_arousals / np.sum(exp_arousals)

        return float(weights[0]), float(weights[1])

    @staticmethod
    def gated_integration(
        arousal_state: float,
        arousal_agent: float,
        threshold: float = 0.2,
    ) -> tuple[float, float]:
        """
        Discrete selection based on arousal difference.

        Args:
            arousal_state: State domain arousal
            arousal_agent: Agent domain arousal
            threshold: Minimum difference for discrete selection

        Returns:
            (weight_state, weight_agent) - one will be 1.0, other 0.0,
            or (0.5, 0.5) if difference below threshold

        Theoretical Motivation:
            Models winner-take-all attention mechanisms.
            May be more efficient but less robust than weighted.
        """
        diff = abs(arousal_state - arousal_agent)

        if diff < threshold:
            # Too close to call - average
            return 0.5, 0.5
        elif arousal_state > arousal_agent:
            # State domain wins
            return 1.0, 0.0
        else:
            # Agent domain wins
            return 0.0, 1.0
