#!/usr/bin/perl
#GBenelli Nov 7 2007
#This script is designed to run on a local directory 
#after the user has created a local CMSSW release,
#initialized its environment variables by executing
#in the release /src directory:
#eval `scramv1 runtime -csh`
#project CMSSW
#The script will read the cfgs for 7 standard candles
#in $CMSSW_RELEASE_BASE/src/Configuration/ReleaseValidation/data
#manipulate them to create for each of them a _sim.cfg
#in the local directory,
#To create an _digi.cfg to run on the previous _sim.cfg
#output.


#Input arguments are three:
#1-Number of events to put in the cfg files
#2-Name of the candle(s) to process (either AllCandles, or NameOfTheCandle)
#3-Whether or not to inlcude the dumping of G4 output messages in the cfg files
#4-Profiles to run (with code below)
#E.g.: ./SimulationCandles.pl 50 AllCandles G4yes 12

if ($#ARGV != 3) {
	print "Usage: cmsSimulationCandles.pl NumberOfEventsPerCfgFile Candles G4DumpOrNot Profile
Candles codes:
AllCandles
 HiggsZZ4LM190
 MinBias
 SingleElectronE1000
 SingleMuMinusPt1000
 SinglePiMinusPt1000
 TTbar
 ZPrimeJJM700
Profile codes (multiple codes can be used):
 0-TimingReport
 1-TimeReport
 2-SimpleMemoryCheck
 3-EdmSize
 4-IgProfPerf
 5-IgProfMemTotal
 6-IgProfMemLive
 7-IgProfAnalyse
 8-ValgrindFCE
 9-ValgrindMemCheck
 9-SimpleMemoryCheck
E.g: cmsSimulationCandles.pl 10 AllCandles G4yes 1 OR cmsSimulationCandles.pl 50 HiggsZZ4LM190 G4no 012\n";
	exit;
}
$NumberOfEvents=$ARGV[0];
$WhichCandles=$ARGV[1];
$DumpG4Messages=$ARGV[2];
$ProfileCode=$ARGV[3];


if ($DumpG4Messages eq "G4yes")
{
    $DumpG4=1;
    print "\*\*An extra set of _sim_G4 cfg files \*\*WILL\*\* be created that include G4cout and G4cerr outputs\*\*\n";
}
elsif ($DumpG4Messages eq "G4no")
{
    $DumpG4=0;
    print "\*\*G4cout and G4cerr outputs \*WILL NOT\* be included in the cfg files created\*\*\n";
}
else
{
    print "Usage: cmsSimulationCandles.pl NumberOfEventsPerCfgFile Candles G4DumpOrNot Profile\nE.g: ./SimulationCandles.pl 10 G4yes OR ./SimulationCandles.pl 50 G4no 0123\n";
	exit;
}

#Getting some important environment variables:
$CMSSW_RELEASE_BASE=$ENV{'CMSSW_RELEASE_BASE'};
$CMSSW_VERSION=$ENV{'CMSSW_VERSION'};

#List of standard candles (valid from 1_7_0_pre10):
#it will need to be updated if they change names in later releases

if ($WhichCandles eq "AllCandles")
{
    @Candle=("HiggsZZ4LM190",
	  "MinBias",
	  "SingleElectronE1000",
	  "SingleMuMinusPt1000",
	  "SinglePiMinusPt1000",
	  "TTbar",
	  "ZPrimeJJM700");
    print "ALL standard simulation candles will be PROCESSED:\n@Candle\n";
}
else
{
   
    @Candle=($WhichCandles);
    print "ONLY @Candle will be PROCESSED\n";
}
#Creating and opening the ASCII input file for the relvalreport script:
$SimCandlesFile= "SimulationCandles"."_".$CMSSW_VERSION.".txt";
open(SIMCANDLES,">$SimCandlesFile")||die "Couldn't open $SinCandlesFile to save - $!\n";
print SIMCANDLES "#Candles file automatically generated by SimulationCandles.pl for $CMSSW_VERSION\n\n";

#First task: create _sim _sim_G4 and digi clones of RelVal candles
foreach (@Candle) 
{
    $Candle=$_;
    $RelValCfg=$CMSSW_RELEASE_BASE."/src/Configuration/ReleaseValidation/data/".$Candle.".cfg";
    if (-e $RelValCfg)
    {
	#Opening original RelVal cfg
	open(RELVALCFG,"<$RelValCfg")||die "Couldn't open file $RelValCfg - $!\n";
	#Opening new _sim.cfg file
	$SimFile=$_."_sim.cfg";
	open(SIMCFG,">$SimFile")||die "Couldn't open $SimFile to save - $!\n";
	print SIMCFG "#File automatically generated by SimulationCandles.pl\n";
	#Opening the optional sim_G4 file
	if ($DumpG4)
	{
	    $GOutSimFile=$_."_sim_G4.cfg";
	    open(GSIMCFG,">$GOutSimFile")||die "Couldn't open $SimFile to save - $!\n";
	    print GSIMCFG "#File automatically generated by SimulationCandles.pl\n";
	}
	#Create digi file for each candle
	$DigiFile=$Candle."_digi.cfg";
	open(DIGICFG,">$DigiFile")||die "Couldn't open $DigiFile to save - $!\n";
	print DIGICFG "#File automatically generated by SimulationCandles.pl\n";
	#Loop line by line of the RelVal cfg
	while (<RELVALCFG>)
	{
	    $NewFileLine=$_;
	    #Process the cfg file (line by line) to change:
	    #0-Change the name of the process from Rec to GenSim and Digi
	    if ($_=~/process/)
	    {
		print SIMCFG "process GenSim =\n";
		if ($DumpG4)
		{		
		    print GSIMCFG "process GenSim =\n";
		}
		print DIGICFG "process Digi =\n";
		next;
	    }
	    #1-Number of events
	    if ($_=~/\w maxEvents\b/)
	    {
		$NewFileLine="  untracked PSet maxEvents = \{untracked int32 input = $NumberOfEvents\}\n";
	    }
	    #2-Add G4cout/cerr messages (right after MessageLogger.cfi include)
	    if ($_=~/include \"FWCore\/MessageService\/data\/MessageLogger.cfi\"/)
	    {
		#Could add some comment here to mark the script addition
		print SIMCFG $_;
		#2.1-Later addition of SimpleMemoryCheck in the output:
		    print SIMCFG "  service = SimpleMemoryCheck\n";
		    print SIMCFG "  {\n";
		    print SIMCFG "     untracked int32 ignoreTotal = 1 \# default is one\n";
		    print SIMCFG "     untracked bool oncePerEventMode = true \# default is false, so it only reports increases\n";
		    print SIMCFG "  }\n";
		#2.2-Latest addition of Timing service in the output:
		    print SIMCFG "  service = Timing{}\n";
		if ($DumpG4)    
		{
		    print GSIMCFG $_;
		    #Ugly code... cut and paste...
		    #2.1-Later addition of SimpleMemoryCheck in the output:
		    print GSIMCFG "  service = SimpleMemoryCheck\n";
		    print GSIMCFG "  {\n";
		    print GSIMCFG "     untracked int32 ignoreTotal = 1 \# default is one\n";
		    print GSIMCFG "     untracked bool oncePerEventMode = true \# default is false, so it only reports increases\n";
		    print GSIMCFG "  }\n";
		    #2.2-Latest addition of Timing service in the output:
                    print GSIMCFG "  service = Timing{}\n";
		}
		print DIGICFG $_;
		#Ugly code... cut and paste... again!
		#2.1-Later addition of SimpleMemoryCheck in the output:
		print DIGICFG "  service = SimpleMemoryCheck\n";
		print DIGICFG "  {\n";
		print DIGICFG "     untracked int32 ignoreTotal = 1 \# default is one\n";
		print DIGICFG "     untracked bool oncePerEventMode = true \# default is false, so it only reports increases\n";
		print DIGICFG "  }\n";
		#2.2-Latest addition of Timing service in the output:
		print DIGICFG "  service = Timing{}\n";
		if ($DumpG4)
		{
		    print GSIMCFG "  replace MessageLogger.categories = \{ \"FwkJob\", \"FwkReport\", \"FwkSummary\", \"Root_NoDictionary\", \"G4cout\", \"G4cerr\" \}\n";
		    print GSIMCFG "  replace MessageLogger.cerr.noTimeStamps = true\n";
		    print GSIMCFG "  replace MessageLogger.cout \= \{ untracked bool noTimeStamps = true\n";
		    print GSIMCFG "                                untracked string threshold = \"INFO\"\n";
		    print GSIMCFG "                                untracked PSet INFO = \{ untracked int32 limit = 0  \}\n";
		    print GSIMCFG "                                untracked PSet G4cout = \{ untracked int32 limit = -1 \}\n";
		    print GSIMCFG "                                untracked PSet G4cerr = \{ untracked int32 limit = -1 \}\n";
		    print GSIMCFG "                              }\n";
		}
		next;
	    }
	    #3.1-Implement here the matching of PythiaSource block (count the "{")
	    if ($_=~/source = /)
	    {
		print SIMCFG $_;
		if ($DumpG4)
		{
		    print GSIMCFG $_;
		}
		$CurlyCounter=0;
		while (<RELVALCFG>)
		{
		    print SIMCFG $_;
		    print GSIMCFG $_;
		    if (/\{/)
		    {
			$CurlyCounter++;
		    }
		    if (/\}/)
		    {
			$CurlyCounter--;
		    }
		    if ($CurlyCounter==0)
		    {
			last;
		    }
		}
		print DIGICFG "  source = PoolSource \{\n";
		print DIGICFG "    untracked vstring fileNames = \{\'file:".$Candle."_sim.root\'\}\n";
		print DIGICFG "    untracked string catalog = \'PoolFileCatalog.xml\'\n";
		print DIGICFG "  \}\n\n";
		next; #To avoid writing $$NewFileLine = "";
	    }
	    #3.2-Special case of ZPrimeJJ that does not have a source statement but an include of a cff:
	    if ($_=~/include \"Configuration\/JetMET\/data\/calorimetry-gen-Zprime_Dijets_700.cff\"/)
	    {
		print SIMCFG $_;
		if ($DumpG4)
		{
		    print GSIMCFG $_;
		}
		print DIGICFG "  source = PoolSource \{\n";
		print DIGICFG "    untracked vstring fileNames = \{\'file:".$Candle."_sim.root\'\}\n";
		print DIGICFG "    untracked string catalog = \'PoolFileCatalog.xml\'\n";
		print DIGICFG "  \}\n\n";
		next;  #To avoid writing $$NewFileLine = "";
	    }
	    #3.3-Adding this correction since RelVal are no more maintained and still using VtxGauss:
	    if ($_=~/include \"Configuration\/StandardSequences\/data\/VtxSmearedGauss.cff\"/)
	    {
		print SIMCFG "\#".$_;
		print SIMCFG " include \"Configuration\/StandardSequences\/data\/VtxSmearedBetafuncEarlyCollision.cff\"\n";
		if ($DumpG4)
		{
		    print GSIMCFG "\#".$_;
		    print GSIMCFG " include \"Configuration\/StandardSequences\/data\/VtxSmearedBetafuncEarlyCollision.cff\"\n";
		}
		next;
	    }
	    #4-Comment out steps p0,p1,p2,p3,p4 depending on the step:
	    if (($_=~/path p0 = \{pgen\}/)||($_=~/path p1 = \{psim\}/)) 
	    {
		print SIMCFG $_;
		if ($DumpG4)
		{
		    print GSIMCFG $_;
		}
		print DIGICFG "\#".$_;
		next;
	    }
	    if ($_=~/path p2 = \{pdigi\}/)
	    {
		print SIMCFG "\#".$_;
		if ($DumpG4)
		{
		    print GSIMCFG "\#".$_;
		}
		print DIGICFG $_;
		next;
		$NewFileLine = ""; #Since we always print $NewFileLine at the end of the if's
	    }
	    if (($_=~/path p3 = \{reconstruction_plusRS_plus_GSF\}/)||($_=~/path p4 = \{L1Emulator\}/))
	    {
		$NewFileLine = "\#".$_;
	    }
	    #5-Change output filename to _sim.root _sim_G4.root digi.root
	    if ($_=~/untracked string fileName = "(\w+).root"/)
	    {
		#print "Interpolated filename is $1\n";
		print SIMCFG "    untracked string fileName = \"".$1."_sim.root\"\n";
		if ($DumpG4)
		{
		    print GSIMCFG "    untracked string fileName = \"".$1."_sim.root\"\n";
		}
		print DIGICFG "    untracked string fileName = \"".$1."_digi.root\"\n";
		next;
	    }
	    #6-Change dataTier from "GEN-SIM-DIGI-RECO" to "GEN-SIM"
	    if ($_=~/untracked string dataTier = \"GEN-SIM-DIGI-RECO\"/)
	    {
		print SIMCFG "      untracked string dataTier = \"GEN-SIM\"\n";
		if ($DumpG4)
		{
		    print GSIMCFG "      untracked string dataTier = \"GEN-SIM\"\n";
		}
		print DIGICFG "      untracked string dataTier = \"DIGI\"\n";
		next;
	    }
	    #7-Change schedule from {p0,p1,p2,p3,p4,outpath} to {p0,p1,outpath} for sim
	    #  to {p1,outpath} for digi
	    if ($_=~/  schedule = \{p0,p1/)
	    {
		print SIMCFG "  schedule = {p0,p1,outpath}\n";
		if ($DumpG4)
		{
		    print GSIMCFG "  schedule = {p0,p1,outpath}\n";
		}
		print DIGICFG "  schedule = {p2,outpath}\n";
		next;
		#$NewFileLine=""; #Since we always print $NewFileLine at the end of the if's		    
	    }
	    print SIMCFG $NewFileLine;
	    if ($DumpG4)
	    {
		print GSIMCFG $NewFileLine;
	    }
	    print DIGICFG $NewFileLine;
	}
	close (RELVALCFG);
	close (SIMCFG);
	if ($DumpG4)
	{
	    close (GSIMCFG);
	}
	close (DIGICFG);
    } #end of cloning _sim clones of RelVal candles
    else
    {
	print "File $Candle.cfg **NOT** found in ".$CMSSW_RELEASE_BASE."/src/Configuration/ReleaseValidation/data/\n";
	print "Exiting!\n";
	exit;
    }
#Third task: create SimulationCandles.txt ASCII file input to relvalreport script
    #Use parameters to set which one to dump.... to be implemented
    #The candle file is opened before the candle loop, since for each candle we will append lines to it.
    print SIMCANDLES "\n\#".$Candle."\n\n";
    print SIMCANDLES "\#GEN+SIM step\n";
    if ($ProfileCode=~/0/)
    {
	print "Preparing $Candle for TimingReport profile\n";
	if  ($DumpG4)
	{
	    print SIMCANDLES "cmsRun $GOutSimFile \@\@\@ Timing_Parser \@\@\@ ".$Candle."_sim_TimingReport";
	    if (($ProfileCode=~/1/)||($ProfileCode=~/2/)||($ProfileCode=~/3/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
	}
	else
	{
	    print SIMCANDLES "cmsRun $SimFile \@\@\@ Timing_Parser \@\@\@ ".$Candle."_sim_TimingReport";
	    if (($ProfileCode=~/1/)||($ProfileCode=~/2/)||($ProfileCode=~/3/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
	}
    }
    if ($ProfileCode=~/1/)
    {
	print "Preparing $Candle for TimeReport profile\n";
	if  ($DumpG4)
	{
	    print SIMCANDLES "cmsRun $GOutSimFile \@\@\@ Timereport_Parser \@\@\@ ".$Candle."_sim_TimeReport";
	    if (($ProfileCode=~/2/)||($ProfileCode=~/3/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
	}
	else
	{
	    print SIMCANDLES "cmsRun $SimFile \@\@\@ Timereport_Parser \@\@\@ ".$Candle."_sim_TimeReport";
	    if (($ProfileCode=~/2/)||($ProfileCode=~/3/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
	}
    }
    if ($ProfileCode=~/2/)
    {
	print "Preparing $Candle for SimpleMemoryCheck profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ SimpleMem_Parser \@\@\@ ".$Candle."_sim_SimpleMemReport\n";
    }
    if ($ProfileCode=~/3/)
    {
	print "Preparing $Candle for EdmSize profile\n";
	print SIMCANDLES $Candle."_sim.root \@\@\@ Edm_Size \@\@\@ ".$Candle."_sim_EdmSize\n";
    }
    if ($ProfileCode=~/4/)
    {
	print "Preparing $Candle for IgProfPerf profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ IgProf_perf.PERF_TICKS \@\@\@ ".$Candle."_sim_IgProfperf\n";
    }
    if ($ProfileCode=~/5/)
    {
	print "Preparing $Candle for IgProfMem (MEM_TOTAL) profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ IgProf_mem.MEM_TOTAL \@\@\@ ".$Candle."_sim_IgProfMemTotal";
	if (($ProfileCode=~/6/)||($ProfileCode=~/7/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
    }
    if ($ProfileCode=~/6/)
    {
	print "Preparing $Candle for IgProfMem (MEM_LIVE) profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ IgProf_mem.MEM_LIVE \@\@\@ ".$Candle."_sim_IgProfMemLive";
	if (($ProfileCode=~/7/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
    }
    if ($ProfileCode=~/7/)
    {
	print "Preparing $Candle for IgProfMem (MEM_ANALYSE) profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ IgProf_mem.ANALYSE \@\@\@ ".$Candle."_sim_IgProfMemAnalyse\n";
    }
    if ($ProfileCode=~/8/)
    {
	print "Preparing $Candle for Valgrind callgrind FCE profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ ValgrindFCE \@\@\@ ".$Candle."_sim_valgrind\n";
    }
    if ($ProfileCode=~/9/)
    {
	print "Preparing $Candle for Valgrind memcheck profile\n";
	print SIMCANDLES "cmsRun $SimFile \@\@\@ Memcheck_Valgrind \@\@\@ ".$Candle."_sim_memcheck_valgrind\n";
    }
    print SIMCANDLES "\n\#DIGI step\n";
    if ($ProfileCode=~/0/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ Timing_Parser \@\@\@ ".$Candle."_digi_TimingReport";
	if (($ProfileCode=~/1/)||($ProfileCode=~/2/)||($ProfileCode=~/3/))
	    {
		print SIMCANDLES " \@\@\@ reuse\n";
	    }
	    else
	    {
		print SIMCANDLES "\n";
	    }
    }
    if ($ProfileCode=~/1/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ Timereport_Parser \@\@\@ ".$Candle."_digi_TimeReport";
	if (($ProfileCode=~/2/)||($ProfileCode=~/3/))
	{
	    print SIMCANDLES " \@\@\@ reuse\n";
	}
	else
	{
	    print SIMCANDLES "\n";
	}
    }
    if ($ProfileCode=~/2/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ SimpleMem_Parser \@\@\@ ".$Candle."_digi_SimpleMemReport\n";
    }
    if ($ProfileCode=~/3/)
    {
	print SIMCANDLES $Candle."_digi.root \@\@\@ Edm_Size \@\@\@ ".$Candle."_digi_EdmSize\n";
    }
    if ($ProfileCode=~/4/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ IgProf_perf.PERF_TICKS \@\@\@ ".$Candle."_digi_IgProfperf\n";
    }
    if ($ProfileCode=~/5/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ IgProf_mem.MEM_TOTAL \@\@\@ ".$Candle."_digi_IgProfMemTotal";
	if (($ProfileCode=~/6/)||($ProfileCode=~/7/))
	{
	    print SIMCANDLES " \@\@\@ reuse\n";
	}
	else
	{
	    print SIMCANDLES "\n";
	}
    }
    if ($ProfileCode=~/6/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ IgProf_mem.MEM_LIVE \@\@\@ ".$Candle."_digi_IgProfMemLive";
	if (($ProfileCode=~/7/))
	{
	    print SIMCANDLES " \@\@\@ reuse\n";
	}
	else
	{
	    print SIMCANDLES "\n";
	}
    }
     if ($ProfileCode=~/7/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ IgProf_mem.ANALYSE \@\@\@ ".$Candle."_digi_IgProfMemAnalyse\n";
    }   
    if ($ProfileCode=~/8/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ ValgrindFCE \@\@\@ ".$Candle."_digi_valgrind\n";
    }
    if ($ProfileCode=~/9/)
    {
	print SIMCANDLES "cmsRun $DigiFile \@\@\@ Memcheck_Valgrind \@\@\@ ".$Candle."_digi_memcheck_valgrind\n\n";
    }

} #end of candles loop
close (SIMCANDLES);
exit