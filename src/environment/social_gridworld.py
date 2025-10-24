"""
SimpleSocialGridWorld: Minimal two-domain reinforcement learning environment.

Conceptual Framework:
    Designed to isolate and test domain-specific arousal integration by creating
    genuinely separable State (navigation) and Agent (social assessment) domains
    with forced interaction requirements.

Theoretical Foundations:
    - State domain: Spatial reasoning, path planning
    - Agent domain: Social inference, theory of mind (simplified)
    - Integration requirement: Both domains necessary for optimal policy

Methodological Design Decisions:
    1. NPC positioned to force interaction (no easy avoidance path)
    2. Mood revealed only through interaction (partial observability)
    3. Mood changes periodically to test adaptation
    4. Multiple reward sources create genuine domain conflict
"""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

import numpy as np


class Action(Enum):
    """Available actions in the environment."""
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    INTERACT = 4  # Query/approach NPC


class NPCMood(Enum):
    """NPC emotional states with distinct interaction outcomes."""
    FRIENDLY = 0  # Positive interaction reward
    NEUTRAL = 1   # No reward, no penalty
    HOSTILE = 2   # Strong negative penalty


@dataclass
class GridState:
    """Complete environment state representation.

    Conceptual Separation:
        - agent_pos, goal_pos: State domain (navigation)
        - npc_mood_estimate, interaction_count: Agent domain (social)
    """
    agent_pos: tuple[int, int]
    goal_pos: tuple[int, int]
    npc_pos: tuple[int, int]
    npc_mood_actual: NPCMood  # Hidden from agent
    npc_mood_estimate: NPCMood | None  # Agent's belief about NPC
    interaction_count: int
    steps: int


class Transition(NamedTuple):
    """Experience tuple for learning."""
    state: GridState
    action: Action
    reward: float
    next_state: GridState
    done: bool
    info: dict[str, float]


class SimpleSocialGridWorld:
    """
    Minimal environment for testing arousal-based integration.

    Design Rationale:
        - Small enough for tractable analysis (5x5 grid)
        - Complex enough to require both domains
        - NPC mood changes test adaptation (every 75 episodes per your suggestion)

    State Space Decomposition:
        Navigation (State): (x, y, goal_x, goal_y, walls) → ~25 states
        Social (Agent): (npc_mood_estimate, interaction_history) → ~6 states
        Combined: ~150 total states (tractable for Q-learning)

    Reward Structure:
        Goal reached: +10 (primary objective)
        Step cost: -0.1 (efficiency incentive)
        Hostile interaction: -5 (strong penalty)
        Friendly interaction: +1 (minor bonus)
        Wall collision: -1 (navigation error)

    Critical Design Choice:
        NPC positioned at (2,2) in 5x5 grid ensures agent must either:
        A) Navigate around NPC (longer path, more step cost)
        B) Assess mood and interact strategically (requires Agent domain)
    """

    def __init__(
        self,
        size: int = 5,
        npc_position: tuple[int, int] = (2, 2),
        goal_position: tuple[int, int] = (4, 4),
        mood_change_frequency: int = 75,
        max_steps: int = 50,
        seed: int | None = None,
    ):
        """
        Initialize environment with configurable parameters.

        Args:
            size: Grid dimensions (size x size)
            npc_position: Fixed NPC location (should force interaction)
            goal_position: Fixed goal location
            mood_change_frequency: Episodes between NPC mood changes
            max_steps: Maximum steps per episode before timeout
            seed: Random seed for reproducibility
        """
        self.size = size
        self.npc_pos = npc_position
        self.goal_pos = goal_position
        self.mood_change_freq = mood_change_frequency
        self.max_steps = max_steps

        self.rng = np.random.default_rng(seed)

        # Episode tracking for mood changes
        self.episode_count = 0
        self.current_mood = NPCMood.NEUTRAL

        # Current state
        self.state: GridState | None = None

        # Performance tracking
        self.total_rewards: list[float] = []

    def reset(self) -> GridState:
        """
        Reset environment to initial state.

        Methodological Note:
            Agent starts at random position (not goal or NPC) to vary
            initial conditions across episodes.
        """
        self.episode_count += 1

        # Update NPC mood periodically (per Ty's suggestion: ~75 episodes)
        if self.episode_count % self.mood_change_freq == 0:
            self._update_npc_mood()

        # Random agent starting position (avoid goal and NPC)
        while True:
            agent_pos = (
                int(self.rng.integers(0, self.size)),
                int(self.rng.integers(0, self.size))
            )
            if agent_pos != self.goal_pos and agent_pos != self.npc_pos:
                break

        self.state = GridState(
            agent_pos=agent_pos,
            goal_pos=self.goal_pos,
            npc_pos=self.npc_pos,
            npc_mood_actual=self.current_mood,
            npc_mood_estimate=None,  # Agent doesn't know mood initially
            interaction_count=0,
            steps=0,
        )

        return self.state

    def step(self, action: Action) -> Transition:
        """
        Execute action and return transition.

        Reward Logic (Explicit for Reproducibility):
            1. Check if goal reached: +10 (terminal)
            2. Apply step cost: -0.1 (always)
            3. Handle interaction if INTERACT action
            4. Check wall collision: -1
            5. Check timeout: episode ends

        Domain-Specific Feedback:
            State domain errors: wall collision, inefficient path
            Agent domain errors: hostile interaction, mood misestimation
        """
        if self.state is None:
            raise RuntimeError("Must call reset() before step()")

        reward = 0.0
        done = False
        info: dict[str, float] = {
            "state_error": 0.0,  # Navigation mistakes
            "agent_error": 0.0,  # Social assessment mistakes
        }

        # Always apply step cost (efficiency incentive)
        reward -= 0.1

        # Process action
        next_pos = self.state.agent_pos
        new_pos = self.state.agent_pos  # Initialize new_pos for all action types

        if action == Action.INTERACT:
            # Agent domain: Social interaction
            if self._is_adjacent_to_npc(self.state.agent_pos):
                mood = self.state.npc_mood_actual

                # Update agent's belief about NPC mood
                new_mood_estimate = mood

                # Interaction rewards based on actual mood
                if mood == NPCMood.HOSTILE:
                    reward -= 5.0
                    info["agent_error"] = 5.0  # Major social misjudgment
                elif mood == NPCMood.FRIENDLY:
                    reward += 1.0
                elif mood == NPCMood.NEUTRAL:
                    reward += 0.0

                # Update interaction count
                new_interaction_count = self.state.interaction_count + 1

                # Severe penalty: 3 hostile interactions ends episode
                if new_interaction_count >= 3 and mood == NPCMood.HOSTILE:
                    done = True
            else:
                # Tried to interact but not adjacent
                new_mood_estimate = self.state.npc_mood_estimate
                new_interaction_count = self.state.interaction_count
                reward -= 0.5  # Wasted action penalty
                info["state_error"] = 0.5  # Navigation error (position misjudgment)

        else:
            # State domain: Navigation actions
            dx, dy = self._action_to_delta(action)
            new_pos = (
                self.state.agent_pos[0] + dx,
                self.state.agent_pos[1] + dy
            )

            # Wall collision check
            if not self._is_valid_position(new_pos):
                reward -= 1.0
                new_pos = self.state.agent_pos  # Stay in place
                info["state_error"] = 1.0  # Navigation error

            new_mood_estimate = self.state.npc_mood_estimate
            new_interaction_count = self.state.interaction_count

        # Check goal reached
        if next_pos == self.goal_pos or new_pos == self.goal_pos:
            reward += 10.0
            done = True

        # Timeout check
        new_steps = self.state.steps + 1
        if new_steps >= self.max_steps:
            done = True

        # Create next state
        next_state = GridState(
            agent_pos=new_pos,
            goal_pos=self.state.goal_pos,
            npc_pos=self.state.npc_pos,
            npc_mood_actual=self.state.npc_mood_actual,
            npc_mood_estimate=new_mood_estimate,
            interaction_count=new_interaction_count,
            steps=new_steps,
        )

        transition = Transition(
            state=self.state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            info=info,
        )

        self.state = next_state

        if done:
            self.total_rewards.append(reward)

        return transition

    def _update_npc_mood(self) -> None:
        """
        Change NPC mood periodically to test adaptation.

        Methodological Justification:
            Mood changes force agents to re-assess social context,
            testing whether Agent domain arousal enables faster adaptation.
        """
        moods = list(NPCMood)
        # Don't stay in same mood (force change)
        moods.remove(self.current_mood)
        mood_indices = list(range(len(moods)))
        selected_index = self.rng.choice(mood_indices)
        self.current_mood = moods[selected_index]

    def _action_to_delta(self, action: Action) -> tuple[int, int]:
        """Convert action enum to position delta."""
        if action == Action.UP:
            return (0, -1)
        elif action == Action.DOWN:
            return (0, 1)
        elif action == Action.LEFT:
            return (-1, 0)
        elif action == Action.RIGHT:
            return (1, 0)
        else:
            return (0, 0)

    def _is_valid_position(self, pos: tuple[int, int]) -> bool:
        """Check if position is within grid bounds."""
        x, y = pos
        return 0 <= x < self.size and 0 <= y < self.size

    def _is_adjacent_to_npc(self, pos: tuple[int, int]) -> bool:
        """Check if position is adjacent to NPC (Manhattan distance = 1)."""
        dist = abs(pos[0] - self.npc_pos[0]) + abs(pos[1] - self.npc_pos[1])
        return dist == 1

    def render(self) -> str:
        """Simple text rendering for debugging."""
        if self.state is None:
            return "Environment not initialized. Call reset()."

        grid = [["." for _ in range(self.size)] for _ in range(self.size)]

        # Place entities
        grid[self.state.goal_pos[1]][self.state.goal_pos[0]] = "G"
        grid[self.state.npc_pos[1]][self.state.npc_pos[0]] = "N"
        grid[self.state.agent_pos[1]][self.state.agent_pos[0]] = "A"

        # Add NPC mood indicator
        mood_str = f"NPC: {self.state.npc_mood_actual.name}"
        if self.state.npc_mood_estimate:
            mood_str += f" (Agent believes: {self.state.npc_mood_estimate.name})"

        grid_str = "\n".join([" ".join(row) for row in grid])
        return f"{grid_str}\n{mood_str}\nSteps: {self.state.steps}"
