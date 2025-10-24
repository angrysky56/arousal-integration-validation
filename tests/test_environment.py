"""
Environment Validation Tests

Methodological Purpose:
    Verify environment satisfies design requirements before agent training:
    1. Domain separability (navigation vs. social distinct)
    2. Solvability (optimal policy exists)
    3. Correct reward structure implementation
    4. Mood dynamics function as specified
"""

from src.environment.social_gridworld import Action, NPCMood, SimpleSocialGridWorld


def test_environment_initialization():
    """Verify environment initializes correctly."""
    env = SimpleSocialGridWorld(seed=42)
    state = env.reset()

    assert state.agent_pos != state.goal_pos, "Agent shouldn't start at goal"
    assert state.agent_pos != state.npc_pos, "Agent shouldn't start at NPC"
    assert state.npc_mood_estimate is None, "Agent shouldn't know mood initially"
    assert state.steps == 0, "Steps should start at 0"
    print("✓ Environment initialization correct")


def test_navigation_mechanics():
    """Verify State domain mechanics work correctly."""
    env = SimpleSocialGridWorld(seed=42)
    env.reset()

    # Test valid movement
    transition = env.step(Action.RIGHT)

    assert transition.reward < 0, "Step cost should apply"
    assert not transition.done or transition.reward > 5, "Shouldn't end early"
    print("✓ Navigation mechanics functional")


def test_interaction_mechanics():
    """Verify Agent domain mechanics work correctly."""
    env = SimpleSocialGridWorld(seed=42)
    state = env.reset()

    # Force NPC to be hostile
    env.current_mood = NPCMood.HOSTILE
    state.npc_mood_actual = NPCMood.HOSTILE

    # Move adjacent to NPC
    state.agent_pos = (2, 1)  # Above NPC at (2,2)

    # Interact
    transition = env.step(Action.INTERACT)

    assert transition.reward < -1, "Hostile interaction should penalize"
    assert transition.next_state.npc_mood_estimate == NPCMood.HOSTILE
    assert transition.info["agent_error"] > 0, "Should signal Agent domain error"
    print("✓ Interaction mechanics functional")


def test_goal_reaching():
    """Verify goal reward is awarded correctly."""
    env = SimpleSocialGridWorld(seed=42)
    state = env.reset()

    # Place agent adjacent to goal
    state.agent_pos = (3, 4)  # Next to goal at (4,4)

    transition = env.step(Action.RIGHT)

    assert transition.done, "Should end when goal reached"
    assert transition.reward > 5, "Should get large goal reward"
    print("✓ Goal reaching functional")


def test_mood_change_dynamics():
    """Verify NPC mood changes as specified."""
    env = SimpleSocialGridWorld(mood_change_frequency=5, seed=42)

    initial_mood = env.current_mood

    # Run 5 episodes to trigger mood change
    for _ in range(5):
        env.reset()
        env.step(Action.UP)  # Take any action

    assert env.current_mood != initial_mood, "Mood should change after frequency threshold"
    print("✓ Mood dynamics functional")


def test_domain_error_attribution():
    """
    Critical Test: Verify errors are correctly attributed to domains.

    This validates the assumption that State and Agent errors are separable.
    """
    env = SimpleSocialGridWorld(seed=42)
    env.reset()

    # Test State domain error (wall collision)
    state = env.reset()
    state.agent_pos = (0, 0)  # Corner
    transition_wall = env.step(Action.LEFT)  # Try to go through wall

    assert transition_wall.info["state_error"] > 0, "Wall collision is State error"
    assert transition_wall.info["agent_error"] == 0, "Wall collision not Agent error"

    # Test Agent domain error (hostile interaction)
    state = env.reset()
    env.current_mood = NPCMood.HOSTILE
    state.npc_mood_actual = NPCMood.HOSTILE
    state.agent_pos = (2, 1)  # Adjacent to NPC

    transition_hostile = env.step(Action.INTERACT)

    assert transition_hostile.info["agent_error"] > 0, "Hostile interaction is Agent error"

    print("✓ Domain error attribution correct")


def test_optimal_policy_exists():
    """
    Philosophical Verification: Confirm environment is solvable.

    Tests that an agent following a simple heuristic can reach the goal
    without catastrophic failure, proving an optimal policy exists.
    """
    env = SimpleSocialGridWorld(seed=42)

    for trial in range(10):
        state = env.reset()
        total_reward = 0
        steps = 0

        # Simple heuristic: move toward goal, avoid NPC if hostile
        while steps < 50:
            # Check if adjacent to NPC
            dist_to_npc = abs(state.agent_pos[0] - state.npc_pos[0]) + \
                         abs(state.agent_pos[1] - state.npc_pos[1])

            if dist_to_npc == 1 and state.npc_mood_estimate == NPCMood.HOSTILE:
                # Move away from hostile NPC
                if state.agent_pos[0] < state.npc_pos[0]:
                    action = Action.LEFT
                elif state.agent_pos[0] > state.npc_pos[0]:
                    action = Action.RIGHT
                elif state.agent_pos[1] < state.npc_pos[1]:
                    action = Action.UP
                else:
                    action = Action.DOWN
            elif dist_to_npc == 1 and state.npc_mood_estimate is None:
                # Query NPC mood if adjacent
                action = Action.INTERACT
            else:
                # Move toward goal
                if state.agent_pos[0] < state.goal_pos[0]:
                    action = Action.RIGHT
                elif state.agent_pos[0] > state.goal_pos[0]:
                    action = Action.LEFT
                elif state.agent_pos[1] < state.goal_pos[1]:
                    action = Action.DOWN
                else:
                    action = Action.UP

            transition = env.step(action)
            total_reward += transition.reward
            state = transition.next_state
            steps += 1

            if transition.done:
                break

        # At least some trials should reach goal with positive reward
        if total_reward > 5:
            print(f"✓ Trial {trial}: Reached goal with reward {total_reward:.2f}")
            print("✓ Optimal policy existence confirmed")
            return

    raise AssertionError("No trial reached goal - environment may not be solvable")


if __name__ == "__main__":
    print("Running Environment Validation Tests\n")
    print("=" * 60)

    test_environment_initialization()
    test_navigation_mechanics()
    test_interaction_mechanics()
    test_goal_reaching()
    test_mood_change_dynamics()
    test_domain_error_attribution()
    test_optimal_policy_exists()

    print("=" * 60)
    print("\n✅ All validation tests passed")
    print("\nEnvironment satisfies design requirements:")
    print("  • Domain separability: State and Agent errors distinct")
    print("  • Solvability: Optimal policy confirmed to exist")
    print("  • Reward structure: Correctly implemented")
    print("  • Mood dynamics: Functioning as specified")
    print("\nReady for Phase 1: Baseline agent training")
