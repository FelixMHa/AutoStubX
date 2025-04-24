from distutils.core import setup
from Cython.Build import cythonize

setup(ext_modules=cythonize(["DummyTypes.pyx", "CustomFunctions.pyx", 'GeneticAlgorithm.pyx', 'Main.pyx']))
