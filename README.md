## Mac Notes
* pyinstaller and wxPython require a python built with `enable-framework` 
on. Therefore, one should do
`env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.7` and
use that Python installation for building.
* If the text is blurry in the app bundled by `pyinstaller`, one needs to
add an entry in the pyinstaller settings as described
[here](https://stackoverflow.com/a/40676321)

## PyInstaller Build Notes
* Always run `pyinstaller rkviewer.spec` when `rkviewer.spec` is present.
* If somehow `rkviewer.spec` went missing or you want to regenerate the build specs,
run `pyinstaller -F --windowed --add-data ext/Iodine.dll;. main.py` on Windows
or `pyinstaller -F --windowed --add-data ext/Iodine.dll:. main.py` on Linux/Mac
to generate a file named `main.spec`. Note that if a `main.spec` file is already 
present **it will be overwritten**.
