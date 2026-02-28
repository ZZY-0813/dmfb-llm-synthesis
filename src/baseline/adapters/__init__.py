"""
Adapters for external DMFB tools.

This module provides unified interfaces to external DMFB synthesis tools
such as MFSim (UCR), Splash-2, CS220, and other academic implementations.
"""

from .base_adapter import BaseAdapter, AdapterError
from .python_fallback import PythonFallbackAdapter

__all__ = ["BaseAdapter", "AdapterError", "PythonFallbackAdapter"]

# Optional adapters - only available if external tools are installed
try:
    from .mfsim_adapter import MFSimAdapter, MFSimImporter, MFSimConfig
    from .mfsim_adapter import MFSimScheduler, MFSimPlacer, MFSimRouter, MFSimPinMapper
    __all__.extend(["MFSimAdapter", "MFSimImporter", "MFSimConfig",
                   "MFSimScheduler", "MFSimPlacer", "MFSimRouter", "MFSimPinMapper"])
except ImportError:
    pass

try:
    from .splash_adapter import SplashAdapter
    __all__.append("SplashAdapter")
except ImportError:
    pass

try:
    from .cs220_adapter import CS220Adapter, CS220Importer
    __all__.extend(["CS220Adapter", "CS220Importer"])
except ImportError as e:
    pass
