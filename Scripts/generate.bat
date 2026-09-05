@echo off
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%"

echo Generating default KiCad libraries...
python "Scripts\generate.py" %*
if errorlevel 1 goto :fail

echo Done.
popd
exit /b 0

:fail
echo Generation failed.
popd
exit /b 1
