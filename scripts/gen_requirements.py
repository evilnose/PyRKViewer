import os
root_dir = os.path.join(os.path.realpath(__file__), '..', '..')

def apath(filename):
    return os.path.abspath(os.path.join(root_dir, filename))

os.system('poetry export -f requirements.txt --output {}'.format(apath('requirements.txt')))
os.system('poetry export --dev -f requirements.txt --output {}'.format(apath('requirements-dev.txt')))
os.system('poetry export -E sbml -f requirements.txt --output {}'.format(apath('requirements-sbml.txt')))
