# Pyamoto

## Usage
Follow the guide on the wiki here: https://zenith.nsmbu.net/wiki/Miyamoto_Level_Editor

## Building
Please note that when building Miyamoto, you have to remove any instances of Cython usage in both Miyamoto and libyaz0. (pyximport)  
Alternatively, you can build the .pyx files and then remove any instances of pyximport in the code.

## Running from Source
1. Install the latest version of [Python 3](https://www.python.org/downloads/) (make sure you install pip and, on Windows, select the option to add Python to PATH):  
2. Clone the repository: `git clone https://github.com/Zenith-Team/Miyamoto.git`  
3. Install the dependencies: `python -m pip install PyQt5 Cython libyaz0 SarcLib`
4. Install C compiler for Cython:
   - Windows: [Microsoft Build Tools 2015](http://download.microsoft.com/download/5/F/7/5F7ACAEB-8363-451F-9425-68A90F98B238/visualcppbuildtools_full.exe)
   - Mac: `xcode-select --install`
   - Linux: Install GCC from your package manager, on Ubuntu it would be `sudo apt install build-essential`

## Credits
### Reggie! & Reggie! Next
* Treeki & Tempus - Creators of Reggie!
* RoadrunnerWMC - Creator of Reggie! Next
* Grop, Hiccup, Kinnay, MrRean and RoadrunnerWMC - Reggie! Next NSMBU
  
### Miyamoto
* AboodXD - Lead Coder, Icons & Graphics, Sprite Images & Coding
* Gota7 - Founder, Icons
* John10v10 - Quick Paint Tool
* mrbengtsson - Sprite Images & Coding
* Luminyx1 - Coding

### Level and Tileset Data Reverse-engineering
* AboodXD
* Kinnay
  
### Spritedata Reverse-engineering
* AboodXD
* mrbengtsson
* Kinnay
* Grop
  
### Others
* Gota7 - Spritedata, Testing on Linux
* Hiccup - Spritedata, Sprite Categories
* libtxc_dxtn - Original DXT5 (De)compressor in C
* Meorge - Testing on macOS
* NVIDIA - NVCOMPRESS
* reece stone - Spritedata
* RoadrunnerWMC - Stamps offset fixes
* Toms - Spritedata, Testing on macOS
* Wexos - Original BC3 Compressor in C#
* Wiimm - WSZST
