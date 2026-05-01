# Pyamoto
A New Super Mario Bros. U level editor.

## Usage
Follow the guide on the wiki here: https://zenith.nsmbu.net/wiki/Miyamoto_Level_Editor

## Running from Source
1. Install the latest version of [Python 3](https://www.python.org/downloads/) (make sure you install pip and, on Windows, select the option to add Python to PATH):  
2. Clone the repository: `git clone https://github.com/Zenith-Team/Pyamoto.git --recursive`
3. Install the dependencies: `python -m pip install PyQt5 Cython SarcLib`
4. Install C compiler for Cython:
   - Windows: [Microsoft Build Tools 2015](https://download.microsoft.com/download/5/F/7/5F7ACAEB-8363-451F-9425-68A90F98B238/visualcppbuildtools_full.exe)
   - Mac: `xcode-select --install`
   - Linux: Install GCC from your package manager, on Ubuntu it would be `sudo apt install build-essential`
