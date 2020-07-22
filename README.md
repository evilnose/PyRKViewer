## Mac Notes
* pyinstaller and wxPython require a python built with `enable-framework` 
on. Therefore, one should do
`env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.7` and
use that Python installation for building.
* If the text is blurry in the app bundled by `pyinstaller`, one needs to
add an entry in the pyinstaller settings as described
[here](https://stackoverflow.com/a/40676321)
