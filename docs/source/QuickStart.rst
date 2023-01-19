.. _QS:

====================
Quick Start
====================

--------------------------
INSTALLING
--------------------------

**Installing with Pypi**

* ``pip install pyrkviewer`` for the base application.

* To run the application, simply run ``coyote`` or ``python -m coyote``

* If wxPython won't get installed automatically, please try to install wxPython manually referring to https://wxpython.org/pages/downloads/index.html.

* Note that on MacOS, if you wish to use Coyote in a virtual environment, use ``venv`` instead of ``virtualenv``, due to the latter's issues with wxPython.

**Installing with Poetry**

1. If you do not have poetry installed on your computer, follow the quick steps shown here (https://python-poetry.org/docs/).

2. Once you have poetry installed, you will download Coyote. Click the green button at the top of this page that says “Code” and choose “Download ZIP”. You want to make sure you know where you have downloaded this. Unzip the folder to your desired directory.

3. Next, open your terminal and navigate to the directory containing Coyote.

4. Once inside the main folder of the application you can install the dependencies. To install the base dependencies simply run ``poetry install``. To install the optional ones as well, run ``poetry install -E simulation``. Note that this step may take a while. To learn more about which set of dependencies is right for you.

5. Finally, you will run the application with the command ``poetry run coyote``.

After you have completed all of these steps, you will not have to repeat them every time you want to run the application. Once the setup is done you will only need to open the terminal, navigate into the folder that contains your Coyote application, and run the command ``poetry run coyote``.

**Installing without Poetry**

Again, we strongly advise following the steps above, as it makes the set-up process much faster and simpler. However, to install Coyote without Poetry, here is the process you will follow:

1. First, download Coyote. Click the green button at the top of this page that says “Code” and choose “Download ZIP”. You want to make sure you know where you have downloaded this. Unzip the folder to your desired directory.

2. Next, open your terminal and navigate to the directory containing Coyote.

3. To install the base set of dependencies, you will run ``pip install -r requirements.txt``. Then if you want to install the optional dependencies as well, run ``pip install -r requirements-simualtion.txt``. To learn more about which set of dependencies is right for you.

4. Finally, you will run the application with the command ``python -m rkviewer.main``. After you have completed all of these steps, you will not have to repeat them every time you want to run the application. Once the setup is done you will only need to open the terminal, navigate into the folder that contains your Coyote application, and run the command ``python -m rkviewer.main``.

**Running**

* If you have poetry, simply run ``poetry run coyote``.

* Otherwise, in your virtual environment, run ``python -m rkviewer.main``.

--------------------------------------------------
RUNNING AND BUILDING
--------------------------------------------------

**Running locally:**

* If you have ``pipenv``, run ``pipenv install`` and then ``python main.py``.

* If not, you may use ``pip`` with ``requirements.txt`` and ``requirements-dev.txt``. They are generated from the Pipfile and may not be up-to-date though, so check the commit history to make sure.

--------------------------------------------------
Building an Executable with Pyinstaller
--------------------------------------------------

* Always run ``pyinstaller rkviewer.spec`` when ``rkviewer.spec`` is present.

* If somehow ``rkviewer.spec`` went missing or you want to regenerate the build specs, run ``pyinstaller -F --windowed --add-data ext/Iodine.dll;. main.py`` on Windows or ``pyinstaller -F -- windowed --add-data ext/Iodine.dll:. main.py`` on Linux/Mac to generate a file named ``main.spec``. Note that if a ``main.spec`` file is already present it will be overwritten.

--------------------------------------------------
USING ON DIFFERENT PLATFORMS
--------------------------------------------------

The python version for development was 3.7.7.

**Mac Notes:**

* pyinstaller and wxPython require a python built with ``enable-framework`` on. Therefore, one should do ``env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.7.7`` and use that Python installation for building.

* If the text is blurry in the app bundled by ``pyinstaller``, one needs to add an entry in the pyinstaller settings as described in https://stackoverflow.com/a/40676321 .

**Linux Notes:**

* To install wxPython on linux, see https://wxpython.org/blog/2017-08-17-builds-for-linux-with-pip/index.html. ``requirements-dev.txt`` and ``requirements.txt`` assume the user is on Ubuntu 18.04 for readthedocs. If you have a different distro and have trouble using ``requirements.txt``, just install wxPython manually using the previous link.

* Related to the last note, if readthedocs start having trouble building wxPython, understand that it might be because readthedocs updated its distro from Ubuntu 18.04. Go to ``requirements-dev.txt`` and change the line above ``wxPython`` to look in the appropriate link.
