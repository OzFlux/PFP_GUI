@echo off
rem
rem Remember the good old days of DOS batch files ... ?
rem
call activate pfp_gui
python PyFluxPro.py
call deactivate
@echo on