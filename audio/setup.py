from setuptools import Extension, setup

ext = Extension(
    name='audio',
    sources=['audio.c'],
)

setup(
    name='audio',
    version='0.1.0',
    ext_modules=[ext],
)
