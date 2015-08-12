from setuptools import setup, find_packages

setup(
    name = 'pyanimenc',
    version = '0.1b1',
    description = 'Audio/Video Transcoding Frontend',
    long_description = '',
    url = 'https://github.com/alucryd/pyanimenc',
    author = 'Maxime Gauduin',
    author_email = 'alucryd@gmail.com',
    license = 'GPL3',
    classifiers = [
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
    keywords = 'audio video conversion',
    packages = find_packages(),
    install_requires = [
        'lxml',
        'pygobject',
        'pymediainfo',
        'setuptools',
    ],
    package_data = {'': ['glade/*.glade']},
    data_files = [
        ('/usr/share/applications', ['data/pyanimenc.desktop']),
        ('/usr/share/pixmaps', ['data/pyanimenc.png']),
    ],
    entry_points = {'gui_scripts': [
        'pyanimenc = pyanimenc',
        ],
    },
)

# vim: ts=4 sw=4 et:
