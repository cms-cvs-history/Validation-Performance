#!/bin/csh
set verbose
foreach i (HiggsZZ4LM190 MinBias SingleElectronE1000 SingleMuMinusPt1000 SinglePiMinusPt1000 TTbar ZPrimeJJM700)
mkdir ${i}_TimeSize
cd ${i}_TimeSize
cmsSimulationCandles.pl 50 $i G4no 0123
cmsRelvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ${i}.log
cd ..
end
mkdir ZPrimeJJM700_IgProf
cd ZPrimeJJM700_IgProf
cmsSimulationCandles.pl 5 ZPrimeJJM700 G4no 4567
cmsRelvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ZPrimeJJM700.log
cd ..
mkdir ZPrimeJJM700_Valgrind
cd ZPrimeJJM700_Valgrind
cmsSimulationCandles.pl 1 ZPrimeJJM700 G4no 89
grep -v sim SimulationCandles_${CMSSW_VERSION}.txt >tmp; mv tmp SimulationCandles_${CMSSW_VERSION}.txt
cmsRun ZPrimeJJM700_sim.cfg >& ZPrimeJJM700_sim.log
cmsRelvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ZPrimeJJM700_digi.log
cd ..
foreach i (SingleMuMinusPt1000)
mkdir ${i}_Valgrind
cd ${i}_Valgrind
cmsSimulationCandles.pl 1 $i G4no 89
grep -v digi SimulationCandles_${CMSSW_VERSION}.txt >tmp; mv tmp SimulationCandles_${CMSSW_VERSION}.txt
cmsRelvalreport_v2.py -i SimulationCandles_${CMSSW_VERSION}.txt -t perfreport_tmp -R -P >& ${i}.log
cd ..
end

