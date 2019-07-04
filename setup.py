#      Copyright (C) 2019  Frank Riley
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

REQUIRES = ['dbus-python>=1.2.8', 'PyGObject>=3.22.0', 'pyserial>=3.4', 'PyYAML>=3.13']

setuptools.setup(
    name="bumpemu",
    version="0.0.8",
    author="Frank Riley",
    author_email="fhriley@gmail.com",
    description="A bump controller emulator on Raspberry Pi Zero W.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fhriley/bumpemu",
    license='GNU GPLv3',
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={'bumpemu': ['config/presets.yml']},
    python_requires='>=3.5',
    install_requires=REQUIRES,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
    ],
    entry_points={
        'console_scripts': [
            'bumpemu-controller = bumpemu.main:main',
            'powerlab-tester = bumpemu.charger.tester:main'
        ]
    }
)
