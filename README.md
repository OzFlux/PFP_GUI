# PyFluxPro

Welcome to the repository for the integrated GUI version of PyFluxPro.

PyFluxPro is a suite of Python scripts, now integrated into a single GUI, that is designed to simplify and standardise the quality control, post-processing, gap filling and partitioning of data from flux towers.  PyFluxPro has been developed by the OzFlux (http://ozflux.org.au) community in Australia and is used by the community as the operational tool for processing data from the OzFlux network of flux towers.  PyFluxPro is not limited to Australia and can be used for flux tower data collected anywhere in the world.  Using PyFluxPro does not require any knowledge of Python (though we would always recommend people learn Python anyway!), all aspects of the processing can be controlled via the integrated GUI.  PyFluxPro can read data from Excel workbooks and CSV files and uses netCDF files (http://www.unidata.ucar.edu/software/netcdf/) for storing intermediate and final output data.

The following documentation gives basic information on how to install and use PyFluxPro.  Details on the algorithms used in PyFluxPro and results for several sites in the Australian OzFlux network can be found in a recent publication in the OzFlux Special Issue of Biogeosciences (https://www.biogeosciences.net/14/2903/2017/).

# Installation and Updating
There are 4 steps to installing PyFluxPro on Windows:
* 1. Install Python.
* 2. Install the "git" version control software.
* 3. Clone the PyFluxPro repository using the "git" version control software.
* 4. Create a Python virtual environment for running PyFluxPro.

A fifth step is required when installing PyFluxPro on Linux or Mac OSX.  The extra step is to build the executable files for the SOLO neural network, the MPT u* threshold detection scheme and the MDS gap filling routine, see below for details.

## Installing Python
PyFluxPro is written for Python V2.7 and uses a number of standard and 3rd party Python modules.

OzFlux uses and recommends the Miniconda2 (https://conda.io/miniconda.html) Python V2.7 distribution.  This is a minimilist installation of Python2 which installs into your home directory and can then be automatically configured to provide all of the Python modules used by PyFluxPro.

**NOTE:** The GUI version of PyFluxPro uses PyQt5 to provide the GUI elements.  We have not found a way of installing PyQt5 using "pip" so a "requirements.txt" file for automatically configuring the Miniconda2 installation using "pip" is not supplied at present.  The currently recommended way to configure the Miniconda2 installation is to create a virtual environment using "conda env create ..." using the YAML file ("environment.yml") supplied.

To install Miniconda2, follow these steps:
* 1. Download the Miniconda2 Python V2.7 installer for your operating system from https://conda.io/miniconda.html.
* 2. Follow the instructions on the Conda web page (https://conda.io/docs/user-guide/install/index.html) to install the Miniconda2 Python V2.7 distribution.
* 3. Accept all the defaults during the installation, including having Conda append the path to this Python installation to your system PATH environment variable.

At the end of this process, you should have a functioning, although minimal, installation of the Python language interpeter.

## Installing "git"
The version control program "git" provides a convenient way to install PyFluxPro and to update PyFluxPro once it has been installed.

To install "git", follow these steps:
* 1. Download the "git" installer for your operating system from https://git-scm.com/downloads.
* 2. Follow the instructions on the "git" web page to install the "git" version control software.
* 3. Accept all the defaults during the installation.

## Installing PyFluxPro
PyFluxPro is easily installed using the "git" version control software.  This process is refered to as "cloning" the PyFluxPro repository (this web page).  When PyFluxPro is installed using "git" then "git" can also be used to easily update PyFluxPro to make sure you are always using the most recent version.  This is a good idea because PyFluxPro is frequently updated to fix bugs and add new features.

To install PyFluxPro, follow these steps:
* 1. Open a command line window or terminal session and use the "cd" (shorthand for "change directory") command to navigate to the directory into which you want to install PyFluxPro.  Note that the installation process will create a subdirectory called PyFluxPro in the directory from which the install is run.
* 2. Clone the PyFluxPro repository by typing "git clone https://github.com/OzFlux/PyFluxPro.git" at the command prompt.
* 3. PyFluxPro is now installed but needs a Python virtual environment to be created with the required packages before it can be used.

## Creating the PyFluxPro virtual environment
Miniconda2 installs a minimal version of Python that does not include all of the packages required by PyFluxPro.  The easiest way to configure the Miniconda2 installation so that it includes all of the required packages is to create a virtual environment using the "environment.yml" file supplied with PyFluxPro.  Conda virtual environments are explained at https://conda.io/docs/user-guide/tasks/manage-environments.html.  You can read the docs (always recommended!) or you can follow the steps below:
* 1. Open a command (or terminal) window and use "cd" to navigate to the PyFluxPro directory.
* 2. At the command prompt in the PyFluxPro directory, type "conda env create -f environment.yml" to create the virtual environment.  This process downloads and installs the packages required by PyFluxPro which may take several minutes.  The default name of the environment created is "pfp_env".
* 3. Once the environment has been created, you must activate the environment before running PyFluxPro using;
  * a) On Windows, type "activate pfp_env" at the command prompt in the PyFluxPro directory.
  * b) On Linux and Mac OSX, type "source activate pfp_env" at the command prompt in the PyFluxPro directory.
* 4. PyFluxPro should now be ready to use.

## Building the executable files for Linux and Mac OSX
This step is only required if you are using PyFuxPro on Linux or Mac OSX.  The executable files are downloaded when the PyFluxPro repository is cloned under the Windows operating system.  Building the executable files for use on Linux and Mac OSX requires the GNU Compiler Collection (C and C++) and the GNU make utility to be installed.  These are usually installed by default for Mac OSX and common Linux distributions.

The build process is controlled by the "make_nix" shell script file in the PyFluxPro directory.  To run the script file:
* 1. Use "cd" to navigate to the PyFluxPro directory.
* 2. Type "./make_nix" at the command prompt in the PyFluxPro to run the script file.
* 3. Check that the following files exist once the script has finished;
  * a) "sofm", "solo" and "seqsolo" in the PyFluxPro/solo/bin directory.
  * b) "ustar_mp" in the PyFluxPro/mpt/bin directory.
  * c) "gf_mds" in the PyFluxPro/mds/bin directory.

## Updating PyFluxPro
PyFluxPro is still being actively developed and there are frequent changes to fix bugs and add new features.  It is always a good idea to update your installation to the latest version every few days.  Updating PyFluxPro is easy when the installation was done using the "git" version control software.

To update a PyFluxPro installation done by "git", follow these steps:
* 1. Open a command line window or terminal session and use the "cd" command to navigate to the PyFluxPro directory created during the installation step above.  Note that while the install is done from the directory one level above the PyFluxPro directory, the update is done from the PyFluxPro directory.
* 2. Type "git pull origin master" at the command prompt in the PyFluxPro directory.  This will update the PyFluxPro installation.
* 3. It is a good idea to update the virtual environment when you update PyFluxPro.  To do this, type "conda env update -f environment.yml" at the command prompt in the PyFluxPro directory.  If you have difficulty with this, see https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html for instructions on removing and creating a virtual environment.

# Running PyFluxPro
The simplest way to run PyFluxPro is from the command line.

To run PyFluxPro, follow these steps:
* 1. Open a command line window or terminal session and use the "cd" command to navigate to the PyFluxPro directory.
* 2. Type "python PyFluxPro.py" at the command prompt in the PyFluxPro directory.  Alternatively;
  * a) On Windows, type "pfp".
  * b) On Linux and Mac OSX, type "./pfp".
* 3. After a short time, the PyFluxPro GUI will appear.  This can take a couple of minutes when the program is run for the first time.

# Using PyFluxPro
Coming to the Wiki soon ...
