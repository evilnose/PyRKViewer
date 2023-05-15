
# SBcoyote: An Extensible Python-Based Reaction Editor and Viewer.

## Introduction

SBcoyote, initially called PyRKViewer or Coyote, is a cross-platform visualization tool for drawing reaction networks written with the
[wxPython](https://www.wxpython.org/) framework. It can draw reactants, products, reactions, and compartments, and its features include but are not limited to:
* Support for floating and boundary species.
* Reactions can be displayed using Bezier curves and straight lines.
* Plugin support, with some plugin examples: arrow designer, random network, auto layout, etc.

## Citing

If you are using any of the code, please cite the article (https://arxiv.org/abs/2302.09151). 

## Installing SBcoyote

* Install Python 3.8, 3.9 or 3.10 if not already in the system.
* Go to the command line and type `pip install SBcoyote`.
* If wxPython doesn't get installed automatically, please try to install wxPython 4.1.1 or 4.2.0 manually referring to https://wxpython.org/pages/downloads/index.html. Note wxPython 4.1.1 does not work with Python 3.10. 
* To run the application, simply type in the command line `SBcoyote`.

## Documentation

The full documentation can be found at: https://sys-bio.github.io/SBcoyote/

## Visualization Example

Here is a visualization example by SBcoyote for the large-scale Escherichia coli core 
metabolism network (King et al., 2015; Orth et al., 2010).

<img src="https://raw.githubusercontent.com/sys-bio/SBcoyote/main/examples/ecoli.png" width="500" height="400">

## Installation Options for Developers

### Installing with Poetry
1. If you do not have poetry installed on your computer, follow the quick steps shown [here](https://python-poetry.org/docs/).
2. Once you have poetry installed, you will download SBcoyote. Click the green button at the top of this page that says “Code” and choose “Download ZIP”, then unzip the folder to your desired directory. Make a note of the directory location as you will need it for the next step.
3. Open your terminal and navigate to the directory containing SBcoyote.
4. Once inside the main folder of the application you can install the dependencies. To install the base dependencies simply run `poetry install`. To install the optional ones as well, run `poetry install -E simulation`. Note that this step may take a while. To learn more about which set of dependencies is right for you, refer to the [Dependencies](#Dependencies) section below.
5. Finally, you will run the application with the command `poetry run SBcoyote`.

After you have completed all of these steps, you will not have to repeat them every time you want to run the application. Once the setup is done you will only need to open the terminal, navigate into the folder that contains your SBcoyote application, and run the command `poetry run SBcoyote`.

### Installing without Poetry
We strongly advise following the steps above as it makes the set-up process much faster and simpler. However, to install SBcoyote without Poetry, here is the process you will follow:

1. First, download SBcoyote. Click the green button at the top of this page that says “Code” and choose “Download ZIP”, then unzip the folder to your desired directory. Make a note of the directory location as you will need it for the next step.
2. Open your terminal and navigate to the directory containing SBcoyote.
3. To install the base set of dependencies, you will run `pip install -r requirements.txt`. Then if you want to install the optional dependencies as well, run `pip install -r requirements-simulation.txt`. To learn more about which set of dependencies is right for you, refer to the [Dependencies](#Dependencies) section below.
4. Finally, you will run the application with the command `python -m rkviewer.main`.
After you have completed all of these steps, you will not have to repeat them every time you want to run the application. Once the setup is done you will only need to open the terminal, navigate into the folder that contains your SBcoyote application, and run the command `python -m rkviewer.main`.

### Running
* If you have poetry, simply run `poetry run SBcoyote`.
* Otherwise, in your virtual environment, run `python -m rkviewer.main`.
* Then, check out the [documentation](#documentation).

## Development Setup

### Dependencies
We are using [poetry](https://python-poetry.org/) for dependency management. If you are just looking
to build and run, though, you can work solely with `pip` as well.

There are currently three dependency groups: "base", "development", and "simulation".
* "base" is the bare minimum requirements to run the application without any plugins.
* "development" includes the additional requirements for development, such as for documentation
and testing.
* "simulation" includes a large set of dependencies required for running simulation related plugins. (This is in addition to the base requirements).

The dependency groups are specified in `pyproject.toml` for `poetry`. There are additionally
`requirement.txt` files generated by `poetry`, including `requirements.txt`, `requirements-dev.txt`,
and `requirements-simulation.txt`. If you do not have poetry, you can opt for those as well. If you are
using linux, extra work would need to be done on installing wxPython. Please refer to the
"Linux Notes" section below.

### Installing Dependencies
`poetry` is recommended for installing dependencies. Simply `poetry install` for the base
dependencies and `poetry install -E simulation` to install the optional ones as well.

If you don't have poetry, you can simply run `pip install -r <>` for any of the aforementioned
`requirements.txt` files.

### Running locally
* If you have poetry, simply `poetry run SBcoyote`.
* Otherwise, in your virtual environment, run `python -m rkviewer.main`.

## Development Distributing

* Use `poetry build` and `poetry publish`. Refer to [poetry docs](https://python-poetry.org/docs/)
for more detail.
* To re-generate the `requirements*.txt`, run `scripts/gen_requirements.py`.

### Bundling an Executable with PyInstaller
**NOTE: This section is obsolete for now, as we are currently distributing with pip.**
* Always run `pyinstaller rkviewer.spec` when `rkviewer.spec` is present.
* If somehow `rkviewer.spec` went missing or you want to regenerate the build specs, run `pyinstaller -F --windowed --add-data ext/Iodine.dll;. main.py` on Windows or `pyinstaller -F -- windowed --add-data ext/Iodine.dll:. main.py` on Linux/Mac to generate a file named `main.spec`. Note that if a `main.spec` file is already  present **it will be overwritten**.

## Development for Different Platforms

The python version for development was 3.7.7.

### Mac Notes
* Note that on MacOS, if you wish to use SBcoyote in a virtual environment, use `venv` instead of
`virtualenv`, due to the latter's issues with wxPython.
* pyinstaller and wxPython require a python built with `enable-framework` on. Therefore, one should do `env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.7` and
use that Python installation for building.
* If the text is blurry in the app bundled by `pyinstaller`, one needs to add an entry in the pyinstaller settings as described [here](https://stackoverflow.com/a/40676321).

### Linux Notes
* To install wxPython on linux, see https://wxpython.org/blog/2017-08-17-builds-for-linux-with-pip/index.html. `requirements-dev.txt` and `requirements.txt` assume the user is on Ubuntu 18.04 for readthedocs. If you have a different distro and have trouble using `requirements.txt`, just install wxPython manually using the previous link.
* Related to the last note, if readthedocs start having trouble building wxPython, understand that it might be because readthedocs updated its distro from Ubuntu 18.04. Go to `requirements-dev.txt` and change the line above `wxPython` to look in the appropriate link.
* i.e. `-f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-18.04/ \n wxPython==4.1.1`

## Future Development

### Testing and Profiling
* To run all tests, go to project root and run `python -m unittest discover`.
* To run a specific test suite, run e.g. `python -m unittest test.api.test_node`.
* Or even more specific: `python -m unittest test.api.test_node.TestNode.test_add_nodes`.
* To profile the application, run `python -m cProfile -o rkviewer.stat main.py`.
* To visualize the profile result, run `tuna rkviewer.stat`.

### Building Local Docs
* Run `sphinx-apidoc -f -o docs/source/rkviewer rkviewer rkviewer/plugin rkviewer/resources ` to regenerate the full reference doc source
code if new files were added to the package rkviewer.
* Run `sphinx-build -b html docs\source docs\build`.

### Note on Style
Usually snake_case is used for function names. However, to retain some degree of backwards
compatibility for wxPython, subclasses of wxPython classes use PascalCase for their methods, e.g. `Canvas::RegisterAllChildren`.

### TODOs
* ENHANCEMENT: Add support for multiple net IDs. Currently all net IDs are set to 0 by default.

### Shapes TODOs
* Events (NodeModified)

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
