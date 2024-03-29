# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath("../../plugins"))
# sys.path.insert(0, os.path.abspath("../../rkviewer/plugin"))

# -- Project information -----------------------------------------------------

project = 'SBcoyote'
copyright = '2023, Jin Xu, Gary Geng, Nhan D. Nguyen, Carmen Perena-Cortes, Claire Samuels, Herbert M. Sauro'
author = 'Jin Xu, Gary Geng, Nhan D. Nguyen, Carmen Perena-Cortes, Claire Samuels, Herbert M. Sauro'

# The full version, including alpha/beta/rc tags
release = '1.0.0'
import sphinx_rtd_theme

# readthedocs can't deal with wx, so we tell it to pretend it can
autodoc_mock_imports = ['sortedcontainers', 'numpy', 'wx', 'wxpython', 'gtk', 'gtk+', 'glib',
                        'pillow', 'commentjson']

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions =  [
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.mathjax',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.doctest',
    'sphinx.ext.inheritance_diagram',
    'sphinx_autodoc_typehints',
    'sphinx.ext.intersphinx'
]


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']
master_doc = 'index'
source_suffix = '.rst'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

napoleon_google_docstring = True
always_document_param_types = True
