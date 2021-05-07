# PyRKViewer: A visualization tool for the reaction networks.

## Introduction

PyRKViewer is a visualization tool for drawing the reaction networks written by wxPython (https://www.wxpython.org/) and applicable for different platforms. 
* It can draw reactants, products, reactions and compartments. Its features are listed below but not limited to:
* It supports floating and boundary species.
* Reactions can be displayed using Bezier curves and straight lines.
* It has plugin support, with some plugin examples: ArrowDesigner, RandomNetwork, Antolayout and etc. 
For the next version, we are going to add simulations of reaction networks.

## Quick Starts and Building

### Running locally
* If you have `pipenv`, run `pipenv install` and then `python main.py`.
* If not, you may use `pip` with `requirements.txt` and `requirements-dev.txt`. They are generated from the Pipfile and may not be up-to-date though, so check the commit history to make sure.

### Bundling an Executable with PyInstaller
* Always run `pyinstaller rkviewer.spec` when `rkviewer.spec` is present.
* If somehow `rkviewer.spec` went missing or you want to regenerate the build specs, run `pyinstaller -F --windowed --add-data ext/Iodine.dll;. main.py` on Windows or `pyinstaller -F -- windowed --add-data ext/Iodine.dll:. main.py` on Linux/Mac to generate a file named `main.spec`. Note that if a `main.spec` file is already  present **it will be overwritten**.

## Documentation

The documentation can be found at: https://pyrkviewer.readthedocs.io/

## For Different Platforms

The python version used is 3.7.7.

### Mac Notes
* pyinstaller and wxPython require a python built with `enable-framework` on. Therefore, one should do `env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.7` and
use that Python installation for building.
* If the text is blurry in the app bundled by `pyinstaller`, one needs to add an entry in the pyinstaller settings as described [here](https://stackoverflow.com/a/40676321).

### Linux Notes
* To install wxPython on linux, see https://wxpython.org/blog/2017-08-17-builds-for-linux-with-pip/index.html. `requirements-dev.txt` and `requirements.txt` assume the user is on Ubuntu 18.04 for readthedocs. If you have a different distro and have trouble using `requirements.txt`, just install wxPython manually using the previous link.
* Related to the last note, if readthedocs start having trouble building wxPython, understand that it might be because readthedocs updated its distro from Ubuntu 18.04. Go to `requirements-dev.txt` and change the line above `wxPython` to look in the appropriate link.

## Future Development

### Testing and Profiling
* To run all tests, go to project root and run `python -m unittest discover`.
* To run a specific test suite, run e.g. `python -m unittest test.api.test_node`.
* Or even more specific: `python -m unittest test.api.test_node.TestNode.test_add_nodes`.
* To profile the application, run `python -m cProfile -o rkviewer.stat main.py`.
* To visualize the profile result, run `tuna rkviewer.stat`.

### Building Local Docs
* Run `sphinx-build -b html docs\source docs\build`.

### Note on Style
Usually snake_case is used for function names. However, to retain some degree of backwards compatibility for wxPython, subclasses of wxPython classes use PascalCase for their methods, e.g. `Canvas::RegisterAllChildren`.
 
### TODOs
* BUG: The handle of a reaction may go out of bounds when a node is being moved. Make sure to clip those values.
* REFACTOR: Refactor Minimap so that it's a CanvasElement. We also need CanvasElement functions to accept both a logical_pos and a device_pos as arguments.
* ENHANCEMENT: Add support for multiple net IDs. Currently all net IDs are set to 0 by default.

### Shapes TODOs
* Add form fields for changing the CompositeShape and for setting primitive properties
* Add API functions for setting/getting shapes
* Add convenience API functions for creating rectangle nodes or circle nodes
* Serialize/deserialize shape properties (don't serialize shape list for now), use field like Color | str
* Events (NodeModified)
* Consideration for later: allow shape properties to get values from settings, such as default colors

### Roadmap for Shape Engine
A shape "engine" allows the user to specify custom composite shapes for nodes and compartments.
Composite shapes are constructed out of primitives such as circles, (rounded) rectangles, polygons,
etc.

RKViewer provides a default list of (composite) shapes, but the user may also create their own
shapes out of primitives. A (composite) shape is formed out of one or many primitives, each
scaled, rotated, and translated by certain amounts. User-created shapes will be
associated with each model in the exported `.json` files.

A shape-creation plugin may be created in the future to facilitate the process of designing
complex shapes.

Here is the roadmap for the shape engine:
* Create preliminary list of primitives and a default list of shapes. Allow model loader/saver to
reference that list.
* Modify renderer to be able to render these default shapes.
* Modify inspector to allow the user to change the properties of the primitives in the shape, such
as colors, border thickness, etc.
* Modify model loader/saver to allow users to create custom shape lists manually.
* Write shape-creation plugin?
