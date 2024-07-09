# bladeRF-2024
Doc and sources for work done with BladeRF 2.0 

Goal: use BladeRF 2.0 with GNU Radio

## Windows 11 x64
Success with BladeRF's installer
Success with Radioconda's installer

Version used:
- bladeRF-win-installer-2024.05.exe
- radioconda-2024.05.29-Windows-x86_64.exe


## OSX 11.7.10 Big Sur
Macbook Pro (Retina, 15-inch, Late 2013)

- Success with mac port "bladeRF +tecla" (20211028-5a146b2a)
- Success with Radioconda's installer
- FAIL with mac port "gnuradio"

Version used:
- mac port "bladeRF +tecla": 20211028-5a146b2a. See https://ports.macports.org/port/bladeRF/builds/
- radioconda-2024.05.29-MacOSX-x86_64.pkg: gnuradio-companion 3.10.10
** I needed to load the FPGA manually with bladeRF-cli. I used hostedxA4-latest.rbf (v0.15.3: 2023-08-09)
- I used the following example from NUAND:
https://github.com/Nuand/bladeRF/tree/2024.05/host/examples/gnuradio/rx_gui
