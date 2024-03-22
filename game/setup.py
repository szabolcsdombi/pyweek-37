from setuptools import Extension, setup

ext = Extension(
    name='game',
    sources=[
        'game.cpp',
        'bullet/btBulletCollisionAll.cpp',
        'bullet/btBulletDynamicsAll.cpp',
        'bullet/btLinearMathAll.cpp',
    ],
    define_macros=[
        ('BT_USE_DOUBLE_PRECISION', None),
    ],
    include_dirs=['./bullet'],
    library_dirs=[],
    libraries=[],
)

setup(
    name='game',
    version='0.1.0',
    ext_modules=[ext],
)
