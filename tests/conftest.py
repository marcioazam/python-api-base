"""Pytest configuration - creates my_app alias for src."""
import importlib
import sys
from pathlib import Path

_src = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(_src))

# Register all src submodules as my_app.X
_submodules = ['core', 'application', 'infrastructure', 'interface', 'domain', 'shared']

for sub in _submodules:
    try:
        mod = importlib.import_module(sub)
        sys.modules[f'my_app.{sub}'] = mod
    except ImportError:
        pass

# Create my_app package
import types
my_app = types.ModuleType('my_app')
my_app.__path__ = [str(_src)]
my_app.__file__ = str(_src / '__init__.py')
for sub in _submodules:
    if f'my_app.{sub}' in sys.modules:
        setattr(my_app, sub, sys.modules[f'my_app.{sub}'])
sys.modules['my_app'] = my_app
