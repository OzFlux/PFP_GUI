@echo off
rem
rem Remember the good old days of DOS batch files ... ?
rem
call conda activate pfp_env
if "%1"=="" goto :interactive
if "%1"=="batch" goto :batch
goto :end

:interactive
python PyFluxPro.py
goto :end

:batch
if "%2"=="" call :batch_nocf
python pfp_batch.py %2
goto :end

:batch_nocf
python pfp_batch.py
goto :end

:end
call conda deactivate
@echo on