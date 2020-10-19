## Documentation
The documentation can be found at: https://pyrkviewer.readthedocs.io/

## Building
The python version used is 3.7.7.

### Running locally
* If you have `pipenv`, run `pipenv install` and then `python main.py`.
* If not, you may use `pip` with `requirements.txt` and `requirements-dev.txt`. They are generated
from the Pipfile and may not be up-to-date though, so check the commit history to make sure.

### Bundling an Executable with PyInstaller
* Always run `pyinstaller rkviewer.spec` when `rkviewer.spec` is present.
* If somehow `rkviewer.spec` went missing or you want to regenerate the build specs,
run `pyinstaller -F --windowed --add-data ext/Iodine.dll;. main.py` on Windows
or `pyinstaller -F --windowed --add-data ext/Iodine.dll:. main.py` on Linux/Mac
to generate a file named `main.spec`. Note that if a `main.spec` file is already 
present **it will be overwritten**.

### Building Local Docs
* Run `sphinx-build -b html docs\source docs\build`

## Note on Style
Usually snake_case is used for function names. However, to retain some degree of backwards 
compatibility for wxPython, subclasses of wxPython classes use PascalCase for their methods,
e.g. `Canvas::RegisterAllChildren`.

## Testing and Profiling
* To run all tests, go to project root and run `python -m unittest`.
* To run a particular test, run e.g. `python -m unittest test.rkplugin.test_api`.
* To profile the application, run `sphinx-build -b html docs\source docs\build`.

## Mac Notes
* pyinstaller and wxPython require a python built with `enable-framework` 
on. Therefore, one should do
`env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.7` and
use that Python installation for building.
* If the text is blurry in the app bundled by `pyinstaller`, one needs to
add an entry in the pyinstaller settings as described
[here](https://stackoverflow.com/a/40676321)

## Linux Notes
* To install wxPython on linux, see https://wxpython.org/blog/2017-08-17-builds-for-linux-with-pip/index.html. `requirements-dev.txt` and `requirements.txt` assume the user is on Ubuntu 18.04 for readthedocs. If you have a different distro and have trouble using `requirements.txt`, just install wxPython manually using the previous link.
* Related to the last note, if readthedocs start having trouble building wxPython, understand that it might be because readthedocs updated its distro from Ubuntu 18.04. Go to `requirements-dev.txt` and change the line above `wxPython` to look in the appropriate link.

## TODOs
* BUG: The handle of a reaction may go out of bounds when a node is being moved. Make sure to clip
those values.
* OPTIMIZE: Do not rebuild reaction forms. Instead, keep them all in a dict() and only make the
currently used one visible.
* REFACTOR: Refactor Minimap so that it's a CanvasElement. We also need CanvasElement functions to
accept both a logical_pos and a device_pos as arguments.
* ENHANCEMENT: Add support for multiple net IDs. Currently all net IDs are set to 0 by default.
