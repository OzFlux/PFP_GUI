@echo off
rem
rem Remember the good old days of DOS batch files ... ?
rem
call conda activate pfp_env
python PyFluxPro.py
call conda deactivate
@echo on