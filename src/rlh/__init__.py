"""rlh: a terminal coding agent whose tool-calling policy is trained with RL.

The package holds the agent loop, its tools, the command line and the glue
that turns episodes into training data. The policy itself is Qwen + LoRA and
is loaded from configs/, never bundled here.
"""

__version__ = "0.0.1"
