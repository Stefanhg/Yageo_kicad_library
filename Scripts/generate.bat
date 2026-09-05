@echo off
setlocal

set "ROOT=%~dp0.."
set "LIB=%ROOT%\Libraries\Kicad"
pushd "%ROOT%"

echo Generating default KiCad libraries...
python "Scripts\Resistors\kicad\kicad_resistor_generator.py" --preset E24 --series RC0603FR --output "%LIB%\RC0603FR.kicad_sym" --no-values-output
if errorlevel 1 goto :fail

python "Scripts\Capacitors\kicad\kicad_capacitor_generator.py" --preset verified_baseline --series CC0402 --output "%LIB%\CC0402.kicad_sym" --no-csv-output
if errorlevel 1 goto :fail

python "Scripts\Capacitors\kicad\kicad_capacitor_generator.py" --preset verified_baseline --series CC0603 --output "%LIB%\CC0603.kicad_sym" --no-csv-output
if errorlevel 1 goto :fail

python "Scripts\Capacitors\kicad\kicad_capacitor_generator.py" --preset verified_baseline --series CC0805 --output "%LIB%\CC0805.kicad_sym" --no-csv-output
if errorlevel 1 goto :fail

python "Scripts\Capacitors\kicad\kicad_capacitor_generator.py" --preset verified_baseline --series CC1206 --output "%LIB%\CC1206.kicad_sym" --no-csv-output
if errorlevel 1 goto :fail

echo Done.
popd
exit /b 0

:fail
echo Generation failed.
popd
exit /b 1