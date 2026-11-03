"""The rlh agent: tools, model backends, the turn loop and trajectories.

The loop sends the alert to a model, executes exactly one tool call per turn
inside the episode folder, and records every step so the same trajectory can
be graded, read by a human, and later used as SFT or RL training data.
"""
