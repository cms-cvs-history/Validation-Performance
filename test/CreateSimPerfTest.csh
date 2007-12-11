#!/bin/csh
set verbose
foreach i (HiggsZZ4LM190 MinBias SingleElectronE1000 SingleMuMinusPt1000 SinglePiMinusPt1000 TTbar ZPrimeJJM700)
mkdir ${i}_TimeSize
cd ${i}_TimeSize
${CMSSW_BASE}/src/Validation/Performance/test/SimulationCandles.pl 50 $i G4no 0123
${CMSSW_BASE}/src/Configuration/PyReleaseValidation/test/relvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ${i}.log
cd ..
end
mkdir ZPrimeJJM700_IgProf
cd ZPrimeJJM700_IgProf
${CMSSW_BASE}/src/Validation/Performance/test/SimulationCandles.pl 5 ZPrimeJJM700 G4no 4567
${CMSSW_BASE}/src/Configuration/PyReleaseValidation/test/relvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ZPrimeJJM700.log
cd ..
mkdir ZPrimeJJM700_Valgrind
cd ZPrimeJJM700_Valgrind
${CMSSW_BASE}/src/Validation/Performance/test/SimulationCandles.pl 1 ZPrimeJJM700 G4no 89
grep -v sim SimulationCandles_${CMSSW_VERSION}.txt >tmp; mv tmp SimulationCandles_${CMSSW_VERSION}.txt
cmsRun ZPrimeJJM700_sim.cfg >& ZPrimeJJM700_sim.log
${CMSSW_BASE}/src/Configuration/PyReleaseValidation/test/relvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ZPrimeJJM700_digi.log
cd ..
foreach i (SingleMuMinusPt1000)
mkdir ${i}_Valgrind
cd ${i}_Valgrind
${CMSSW_BASE}/src/Validation/Performance/test/SimulationCandles.pl 1 $i G4no 89
grep -v digi SimulationCandles_${CMSSW_VERSION}.txt >tmp; mv tmp SimulationCandles_${CMSSW_VERSION}.txt
${CMSSW_BASE}/src/Configuration/PyReleaseValidation/test/relvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ${i}.log
cd ..
end

