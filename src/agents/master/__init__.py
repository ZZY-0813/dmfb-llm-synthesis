"""Master Agent for DMFB synthesis pipeline.

Coordinates Placement → Scheduling → Routing in sequence.
"""

from .agent import MasterAgent, PipelineStage

__all__ = ['MasterAgent', 'PipelineStage']
