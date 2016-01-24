#!/usr/bin/env python3

from setuptools import setup

setup(
    name='pyhenkan',
    version='0.1.0',
    packages=['pyhenkan'],
    url='https://github.com/alucryd/pyhenkan',
    license='GPL3',
    author='Maxime Gauduin',
    author_email='alucryd@gmail.com',
    description='Video Transcoding Frontend',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
        'Topic :: Multimedia :: Video :: Conversion',
    ],
    keywords='audio video conversion',
    install_requires=[
        'lxml',
        'pygobject',
        'pymediainfo',
        'setuptools',
    ],
    data_files=[
        ('/usr/share/applications', ['data/pyhenkan.desktop']),
        ('/usr/share/pixmaps', ['data/pyhenkan.svg']),
    ],
    entry_points={'gui_scripts': [
        'pyhenkan = pyhenkan',
    ],
    },
)

# vim: ts=4 sw=4 et:
