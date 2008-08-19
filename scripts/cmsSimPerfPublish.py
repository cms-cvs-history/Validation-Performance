#!/usr/bin/python
#G.Benelli Jan 22 2007, J. Nicolson 12 Aug 2008
#A little script to move Simulation Performance Suite
#relevant html and log files into our public area
#/afs/cern.ch/cms/sdt/web/performance/simulation/
#Set here the standard number of events (could become an option... or could be read from the log...)

###############################
#
# Warning!!! We should use copytree() instead of our self defined copytree4
#            However, copytree does not use ignore patterns (for filtering files)
#            before python v2.6, when we upgrade to python 2.6 we should use this
#            functionality.
import tempfile as tmp
import optparse as opt
import re, os, sys, time, glob, socket, fnmatch
from shutil import copy2, copystat
from stat   import *

PROG_NAME  = os.path.basename(sys.argv[0])
DEF_RELVAL = "/afs/cern.ch/cms/sdt/web/performance/RelVal"
DEF_SIMUL  = "/afs/cern.ch/cms/sdt/web/performance/simulation"
TMP_DIR    = ""
cpFileFilter = ( "*.root" ) # Unix pattern matching not regex
cpDirFilter  = (          ) # Unix pattern matching not regex

TimeSizeNumOfEvents = 100
IgProfNumOfEvents   = 5
ValgrindNumOfEvents = 1

DirName=( #These need to match the candle directory names ending (depending on the type of profiling)
          "TimeSize",
          "IgProf",
          "Valgrind"
          )
##################
#
# Small functions
#

def fail(errstr=""):
    print errstr
    delTmpDir()
    sys.exit()

def addtrailingslash(adir):
    trail = re.compile("/$")
    if os.path.isdir(adir) and not trail.search(adir):
        adir = adir + "/" 
    return adir

def getDate():
    return time.ctime()

def getcmdBasic(cmd):
    return os.popen4(cmd)[1].read().strip()

def getcmd(command):
    if _debug > 2:
        print command
    return os.popen4(command)[1].read().strip()

######################
#
# Main 
#
def main():
        
    def _copyReportsToStaging(repdir,LogFiles,cmsScimarkDir,stage):

        if _verbose:
            print "Copying the logfiles to %s/." % stage
            print "Copying the cmsScimark2 results to the %s/." % stage  

        syscp(LogFiles     , stage + "/")
        syscp(cmsScimarkDir, stage + "/")

    def _createLogFile(LogFile,date,LocalPath,ShowTagsResult):
        try:
            LOG = open(LogFile,"w")
            if _verbose:
                print "Writing Production Host, Location, Release and Tags information in %s" % LogFile 
            LOG.write("These performance tests were executed on host %s and published on %s" % (HOST,date))
            LOG.write("They were run in %s" % LocalPath)
            LOG.write("Results of showtags -r in the local release:\n%s" % ShowTagsResult)
            LOG.close()
        except IOError:
            print "Could not correct create the log file for some reason"

    # Print Program header
    print_header()

    # Get environment variables
    print "\n Getting Environment variables..."
    (LocalPath, ShowTagsResult) = get_environ()

    # Parse options
    (options,args) = optionparse()

    # Determine program parameters and input/staging locations
    print "\n Determining locations for input and staging..."
    (drive,path,remote,stage,port,repdir) = getStageRepDirs(options,args)

    print "\n Scan report directory..."
    # Retrieve some directories and information about them
    (ExecutionDate,LogFiles,date,cmsScimarkResults,cmsScimarkDir) = scanReportArea(repdir)

    print "\n Copy report files to staging directory..."
    # Copy reports to staging area 
    _copyReportsToStaging(repdir,LogFiles,cmsScimarkDir,stage)

    print "\n Creating log file..."
    # Produce a small logfile with basic info on the Production area
    _createLogFile("%s/ProductionLog.txt" % stage,date,repdir,ShowTagsResult)

    print "\n Creating HTML files..."
    # create HTML files
    createWebReports(stage,repdir,ExecutionDate,LogFiles,cmsScimarkResults,date)

    print "\n Copy profiling logs to staging directory..."
    # Copy over profiling logs...
    getDirnameDirs(repdir,stage)

    # Send files to remote location
    if remote:
        print "\n Uploading web report to remote location..."
        syncToRemoteLoc(stage,drive,path,port)
        print "\n Finished uploading! Now removing staging directory..."
        delTmpDir()

    print "\n Finished!!!"

##########################
#
# Get require environment variables
#
def get_environ():
    global CMSSW_VERSION, CMSSW_RELEASE_BASE, CMSSW_BASE, HOST, USER, BASE_PERFORMANCE, CMSSW_WORK
    global DEF_RELVAL, DEF_SIMUL
    
    try:
        CMSSW_VERSION=os.environ['CMSSW_VERSION']
        CMSSW_RELEASE_BASE=os.environ['CMSSW_RELEASE_BASE']
        CMSSW_BASE=os.environ['CMSSW_BASE']
        HOST=os.environ['HOST']
        USER=os.environ['USER']
        CMSSW_WORK = os.path.join(CMSSW_BASE,"work/Results")
    except KeyError:
        fail("ERROR: Could not retrieve some necessary environment variables. Have you ran scramv1 runtime -csh yet?")

    LocalPath=getcmdBasic("pwd")
    ShowTagsResult=getcmdBasic("showtags -r")

    #Adding a check for a local version of the packages
    PerformancePkg="%s/src/Validation/Performance"        % CMSSW_BASE
    if (os.path.exists(PerformancePkg)):
        BASE_PERFORMANCE=PerformancePkg
        print "**[cmsSimPerfPublish.pl]Using LOCAL version of Validation/Performance instead of the RELEASE version**"
    else:
        BASE_PERFORMANCE="%s/src/Validation/Performance"  % CMS_RELEASE_BASE

#   DEF_RELVAL = "%s"     % (DEF_RELVAL,CMSSW_VERSION)
#    DEF_SIMUL  = "%s%s"     % (DEF_SIMUL ,CMSSW_VERSION)

    return (LocalPath,ShowTagsResult)

###############
#Option parser
#
def optionparse():
    global PROG_NAME, _debug, _dryrun, _verbose

    parser = opt.OptionParser(usage=("""%s [HOST:]DEST_PATH [Options]

    Arguments:
        WEB_AREA - local, relval, covms or ...

    Examples:  
       Perform 
        ./%s 
       Perform 
        ./%s 
       Perform 
        ./%s 
       Perform 
        ./%s """
      % ( PROG_NAME, PROG_NAME,PROG_NAME,PROG_NAME,PROG_NAME)))
    
    devel  = opt.OptionGroup(parser, "Developer Options",
                                     "Caution: use these options at your own risk."
                                     "It is believed that some of them bite.\n")
    #parser.set_defaults(debug=False)

    parser.add_option(
        '--relval',
        action="store_true",
        dest='relval',
        help='Use the default simulation location',
        #metavar='<STEPS>',
        )

    parser.add_option(
        '-v',
        '--verbose',
        action="store_true",
        dest='verbose',
        help='output more information',
        #metavar='<STEPS>',
        )    

    parser.add_option(
        '--simul',
        action="store_true",
        dest='simulation',
        help='Use the default simulation location',
        #metavar='<STEPS>',
        )

    parser.add_option(
        '--report-in',
        type="string",
        dest='repdir',
        help='The location of the report files to be published',
        metavar='<DIR>'
        )

    parser.add_option(
        '-p',
        '--port',
        type='int',
        dest='port',
        help='Use a particular port number to rsync material to a remote server',
        metavar='<PORT>'
        )

    devel.add_option(
        '-d',
        '--debug',
        type='int',
        dest='debug',
        help='Show debug output',
        #metavar='DEBUG',
        )

    devel.add_option(
        '--dry-run',
        action="store_true",
        dest='dryrun',
        help='Do not send files to remote server, but run everything else',
        #metavar='DEBUG',
        )

    repdirdef = "./"
    parser.set_defaults(debug=0,simulation=False,relval=False,port=873,pretend=False,repdir=repdirdef,verbose=False)
    parser.add_option_group(devel)

    (options, args) = parser.parse_args()

    _debug   = options.debug
    _dryrun  = options.dryrun
    _verbose = options.verbose

    numofargs = len(args) 

    if (options.simulation and options.relval) or ((options.simulation or options.relval) and numofargs >= 1):
        parser.error("You can not specify simulation and relval together. Neither can you specify simulation or relval AND a path")
        sys.exit()

    return (options, args)

#####################
#
# Determine locations of staging and report dirs 
#
def getStageRepDirs(options,args):
    global TMP_DIR, IS_TMP, DEF_LOCAL
    DEF_LOCAL = CMSSW_WORK
    numofargs = len(args)

    repdir = os.path.abspath(options.repdir)
    repdir = addtrailingslash(repdir)

    if not os.path.exists(repdir):
        fail("ERROR: The specified report directory %s to retrieve report information from does not exist, exiting" % repdir)
    
    uri = ""
    defaultlocal = False
    if options.simulation:
        uri = DEF_SIMUL
    elif options.relval:
        uri = DEF_RELVAL
    elif numofargs >= 1:
        uri = args[0] # Add directory CMSSW_VERSION later in temp! Not now, otherwise we get into a mess if this is a remote dir
    else:
        defaultlocal = True
        uri = DEF_LOCAL

    ####
    #
    # Determine if location is remote
    #
    # Try not to re-arrange we don't want to assume that default locations are not remote
    #
    ####

    drive = ""
    path = ""
    if ":" in uri:
        drive, path = uri.split(":",1)
    else:
        path = uri
        
    if drive == "":
        path = os.path.abspath(path)
    remote = not drive == ""

    if remote:
        unResolved = True
        try:
            socket.getaddrinfo(drive,53)
            unResolved = False
        except socket.gaierror:
            unResolved = True

        # try see if it's an ipaddress
        if unResolved:
            try:
                socket.gethostbyaddr(drive)
                unResolved = False
            except socket.gaierror:
                unResolved = True
            if unResolved:
                print "ERROR: Can not determine your hostname or ipv{4,6} address %s" % drive
                if not (_dryrun or _test):
                    fail("exiting...")

    if (not remote) and (not options.port == 873) :
        print "WARNING: Can not use a port if not performing a remote copy, ignoring"
    port = options.port

    ###
    #
    # Determine Staging Area
    #

    StagingArea=""
    localExists = os.path.exists("%s/%s" % (CMSSW_WORK,CMSSW_VERSION))
    
    if remote:
        TMP_DIR=tmp.mkdtemp(prefix="/tmp/%s" % PROG_NAME)
        StagingArea = TMP_DIR
    #Local but dir already exists
    elif defaultlocal and localExists:
        TMP_DIR=tmp.mkdtemp(prefix="%s/%s" % (CMSSW_WORK,CMSSW_VERSION))
        StagingArea = TMP_DIR
        print "WARNING: %s already exists, creating a temporary staging area %s" % (CMSSW_WORK,TMP_DIR)
    #Local cases
    elif defaultlocal:
        StagingArea = CMSSW_WORK
        print "**User did not specify location of results, staging in default %s**" % StagingArea 
    else:
        print "**User chose to publish results in a local directory**" 
        StagingArea = path
        if not os.path.exists(path):
            os.system("mkdir -p %s" % path)

    IS_TMP = not TMP_DIR == ""
    ######
    #
    # create Version dir
    # This is why when we create a Tmp dir we get the version(tmpname)/version
    # structure. We should remove this if we don't want it but i dont think it matters
    StagingArea="%s/%s" % (StagingArea,CMSSW_VERSION)
    os.system("mkdir -p %s" % StagingArea)

    return (drive,path,remote,StagingArea,port,repdir)

####################
#
# Scan report area for required things
#
def scanReportArea(repdir):
    date=getDate()
    LogFiles  = glob.glob(repdir + "cms*.log")
    if _verbose:
        print "Found the following log files:"
        print LogFiles

    cmsScimarkDir = glob.glob(repdir + "cmsScimarkResults_*")
    if _verbose:
        print "Found the following cmsScimark2 results directories:"
        print cmsScimarkDir

    cmsScimarkResults = []
    for adir in cmsScimarkDir:
        htmlfiles = glob.glob(adir + "/*.html") #filter(htmlreg.search,dc.listdir(dir))
        #htmlfiles = map(lambda x : dir + "/" + x,htmlfiles)
        map(cmsScimarkResults.append,htmlfiles)

    ExecutionDate = ""
    ExecutionDateSec=0
    cmsreg = re.compile("^cmsCreateSimPerfTest")
    for logf in LogFiles:
        if cmsreg.search(logf):
            ExecutionDateLastSec = os.stat(logf)[ST_CTIME]
            ExecutionDateLast    = os.stat(logf)[ST_MTIME]
            if _verbose:
                print "Execution (completion) date for %s was: %s" % (logf,ExecutionDateLast)
            if (ExecutionDateLastSec > ExecutionDateSec):
                ExecutionDateSec = ExecutionDateLastSec
                ExecutionDate    = ExecutionDateLast

    return (ExecutionDate,LogFiles,date,cmsScimarkResults,cmsScimarkDir)

######################
#
# Create HTML pages for candles

def createCandlHTML(tmplfile,candlHTML,CurrentCandle,WebArea,repdir,ExecutionDate,LogFiles,cmsScimarkResults,date):
    def _getProfileReportLink(CurrentCandle,CurDir,step,CurrentProfile,Profiler):

        ProfileTemplate="%s_%s/*_%s_%s*/%s" % (CurrentCandle,CurDir,step,CurrentProfile,Profiler)
        #There was the issue of SIM vs sim (same for DIGI) between the previous RelVal based performance suite and the current.
        ProfileTemplateLowCaps="%s_%s/*_%s_%s*/%s" % (CurrentCandle,CurDir,step.lower(),CurrentProfile,Profiler)
        ProfileReportLink=getcmd("ls %s 2>/dev/null" % ProfileTemplate)
        if ( CurrentCandle not in ProfileReportLink) : #no match with caps try low caps
            ProfileReportLink=getcmd("ls %s 2>/dev/null" % ProfileTemplateLowCaps)
        return ProfileReportLink

    def _writeReportLink(INDEX,ProfileReportLink,CurrentProfile,step,NumOfEvents,Profiler=""):
        if Profiler == "":
            INDEX.write("<li><a href=\"%s\">%s %s (%s events)</a></li>\n" % (ProfileReportLink,CurrentProfile,step,NumOfEvents))
        else:
            INDEX.write("<li><a href=\"%s\">%s %s %s (%s events)</a></li>\n" % (ProfileReportLink,CurrentProfile,Profiler,step,NumOfEvents))
            
    NumOfEvents={ #These numbers are used in the index.html they are not automatically matched to the actual
                   #ones (one should automate this, by looking into the cmsCreateSimPerfTestPyRelVal.log logfile)
                DirName[0] : TimeSizeNumOfEvents,
                DirName[1] : IgProfNumOfEvents,
                DirName[2] : ValgrindNumOfEvents
                }

    Profile=( #These need to match the profile directory names ending within the candle directories
              "TimingReport",
              "TimeReport",
              "SimpleMemReport",
              "EdmSize",
              "IgProfperf",
              "IgProfMemTotal",
              "IgProfMemLive",
              "IgProfMemAnalyse",
              "valgrind",
              "memcheck_valgrind"
               )
    IgProfMemAnalyseOut=( #This is the special case of IgProfMemAnalyse
                          "doBeginJob_output.html",
                          "doEvent_output.html",
                          "mem_live.html",
                          "mem_total.html" 
                          )
    memcheck_valgrindOut=( #This is the special case of Valgrind MemCheck (published via Giovanni's script)
                           "beginjob.html",
                           "edproduce.html",
                           "esproduce.html"
                           )
    OutputHtml={ #These are the filenames to be linked in the index.html page for each profile
                 Profile[0] : "*TimingReport.html", #The wildcard spares the need to know the candle name
                 Profile[1] : "TimeReport.html", #This is always the same (for all candles)
                 Profile[2] : "*.html", #This is supposed to be *SimpleMemoryCheck.html, but there is a bug in cmsRelvalreport.py and it is called TimingReport.html!
                 Profile[3] : "objects_pp.html", #This is one of 4 objects_*.html files, it's indifferent which one to pick, just need consistency
                 Profile[4] : "overall.html", #This is always the same (for all candles)
                 Profile[5] : "overall.html", #This is always the same (for all candles)
                 Profile[6] : "overall.html", #This is always the same (for all candles)
                 Profile[7] : "doBeginJob_output.html", #This is complicated... there are 3 html to link... (see IgProf MemAnalyse below)
                 Profile[8] : "overall.html", #This is always the same (for all candles)
                 Profile[9] : "beginjob.html" #This is complicated there are 3 html to link here too... (see Valgrind MemCheck below)
                 }
    Step=(
           "GEN,SIM",
           "DIGI",
           "L1",
           "DIGI2RAW",
           "HLT",
           "RAW2DIGI",
           "RECO",
           "DIGI_PILEUP",
           "L1_PILEUP",
           "DIGI2RAW_PILEUP",
           "HLT_PILEUP",
           "RAW2DIGI_PILEUP",
           "RECO_PILEUP"
           )



    candnreg  = re.compile("CandleName")
    candhreg  = re.compile("CandlesHere")
    try:
        CAND = open(candlHTML,"w")
        for line in open(tmplfile):
            if candhreg.search(line):
                CAND.write("<table cellpadding=\"20px\" border=\"1\"><tr><td>\n")
                CAND.write("<h2>")
                CAND.write(CurrentCandle)
                CAND.write("</h2>\n")
                CAND.write("<div style=\"font-size: 13\"> \n")
                for CurDir in DirName:

                    LocalPath = "%s%s_%s" % (repdir,CurrentCandle,CurDir)
                    CandleLogFiles = getcmd("sh -c 'find %s -name \"*.log\" 2> /dev/null'" % LocalPath)
                    CandleLogFiles = filter("".__ne__,CandleLogFiles.strip().split("\n"))


                    if (len(CandleLogFiles)>0):
                        CAND.write("<p><strong>Logfiles for %s</strong></p>\n" % CurDir)
                        syscp(CandleLogFiles,WebArea + "/")
                        for cand in CandleLogFiles:
                            if _verbose:
                                print "Found %s in %s\n" % (cand,LocalPath)
                            CAND.write("<a href=\"%s\">%s </a>" % (cand,cand))
                            CAND.write("<br />\n")

                    PrintedOnce = False
                    for CurrentProfile in Profile:

                        for step in Step :

                            ProfileReportLink = _getProfileReportLink(CurrentCandle,
                                                                     CurDir,
                                                                     step,
                                                                     CurrentProfile,
                                                                     OutputHtml[CurrentProfile])

                            if (CurrentProfile in ProfileReportLink):
                                #It could also not be there

                                if (PrintedOnce==False): 
                                    #Making sure it's printed only once per directory (TimeSize, IgProf, Valgrind) each can have multiple profiles

                                    #This is the "title" of a series of profiles, (TimeSize, IgProf, Valgrind)
                                    CAND.write("<p><strong>%s</strong></p>\n" % CurDir)
                                    CAND.write("<ul>\n")
                                    PrintedOnce=True
                                #Special cases first (IgProf MemAnalyse and Valgrind MemCheck)
                                if (CurrentProfile == Profile[7]):
                                    for i in range(0,3,1):
                                        ProfileReportLink = _getProfileReportLink(CurrentCandle,
                                                                                 CurDir,
                                                                                 step,
                                                                                 CurrentProfile,
                                                                                 IgProfMemAnalyseOut[i])
                                        if (CurrentProfile in ProfileReportLink ) :#It could also not be there
                                            _writeReportLink(CAND,ProfileReportLink,CurrentProfile,step,NumOfEvents[CurDir],Profiler=IgProfMemAnalyseOut[i])


                                elif (CurrentProfile == Profile[9]):

                                    for i in range(0,3,1):
                                        ProfileReportLink = _getProfileReportLink(CurrentCandle,
                                                                                 CurDir,
                                                                                 step,
                                                                                 CurrentProfile,
                                                                                 memcheck_valgrindOut[i])
                                        if (CurrentProfile in ProfileReportLink) : #It could also not be there
                                            _writeReportLink(CAND,ProfileReportLink,CurrentProfile,step,NumOfEvents[CurDir],Profiler=memcheck_valgrindOut[i])

                                else:
                                    _writeReportLink(CAND,ProfileReportLink,CurrentProfile,step,NumOfEvents[CurDir])


                    if PrintedOnce:
                        CAND.write("</ul>\n")
                    PrintedOnce=False
                CAND.write("</div>\n")
                CAND.write("<hr />")
                CAND.write("<br />\n")
                CAND.write("</td></tr></table>\n")
            elif candnreg.search(line):
                CAND.write(CurrentCandle)
            else:
                CAND.write(line)

        CAND.close()
    except IOError:
        fail("ERROR: Could not write candle html %s" % os.path.basename(candlHTML))
        
#####################
#
# Create web report index and create  HTML file for each candle
#
def createWebReports(WebArea,repdir,ExecutionDate,LogFiles,cmsScimarkResults,date):

    #Some nomenclature

    Candle=( #These need to match the directory names in the work area
        "HiggsZZ4LM200",
        "MinBias",
        "SingleElectronE1000",
        "SingleMuMinusPt10",
        "SinglePiMinusE1000",
        "TTbar",
        "QCD_80_120"
        )
    CmsDriverCandle={ #These need to match the cmsDriver.py output filenames
        Candle[0] : "HZZLLLL_200",
        Candle[1] : "MINBIAS",
        Candle[2] : "E_1000",
        Candle[3] : "MU-_pt_10",
        Candle[4] : "PI-_1000",
        Candle[5] : "TTBAR",
        Candle[6] : "QCD_80_120"
        }

    #Produce a "small" index.html file to navigate the html reports/logs etc
    IndexFile="%s/index.html" % WebArea
    TemplateHtml="%s/doc/index.html" % BASE_PERFORMANCE

    cmsverreg = re.compile("CMSSW_VERSION")
    hostreg   = re.compile("HOST")
    lpathreg  = re.compile("LocalPath")
    proddreg  = re.compile("ProductionDate")
    logfreg   = re.compile("LogfileLinks")
    dirbreg   = re.compile("DirectoryBrowsing")
    pubdreg   = re.compile("PublicationDate")
    candhreg  = re.compile("CandlesHere")
    #Loop line by line to build our index.html based on the template one
    #TEMPLATE =  #||die "Couldn't open file $TemplateHtml - $!\n"
    #Copy the perf_style.css file from Validation/Performance/doc

    CandlTmpltHTML="%s/doc/candle.html" % BASE_PERFORMANCE
    if _verbose:
        print "Copying %s/doc/perf_style.css style file to %s/." % (BASE_PERFORMANCE,WebArea)    
        print "Template used: %s" % TemplateHtml

    syscp((BASE_PERFORMANCE + "/doc/perf_style.css"),WebArea + "/.")
    
    try:
        INDEX = open(IndexFile,"w") 
        for NewFileLine in open(TemplateHtml) :
            if cmsverreg.search(NewFileLine):
                INDEX.write(CMSSW_VERSION + "\n")
            elif hostreg.search(NewFileLine):
                INDEX.write(HOST + "\n")
            elif lpathreg.search(NewFileLine):
                INDEX.write(repdir + "\n")
            elif proddreg.search(NewFileLine):
                INDEX.write(ExecutionDate + "\n")
            elif logfreg.search(NewFileLine):
                INDEX.write("<br />\n")
                for log in LogFiles:
                    INDEX.write("<a href=\"%s\"> %s </a>" % (log,log))
                    INDEX.write("<br /><br />\n")
                #Add the cmsScimark results here:
                INDEX.write("Results for cmsScimark2 benchmark (running on the other cores) available at:\n")
                INDEX.write("<br /><br />\n")
                for cmssci in cmsScimarkResults:
                    INDEX.write("<a href=\"%s\"> %s </a>" % (cmssci,cmssci))
                    INDEX.write("<br /><br />\n")


            elif dirbreg.search(NewFileLine):
                #Create a subdirectory DirectoryBrowsing to circumvent the fact the dir is not browsable if there is an index.html in it.
                os.system("mkdir %s/DirectoryBrowsing" % WebArea)
                INDEX.write("Click <a href=\"./DirectoryBrowsing/\">here</a> to browse the directory containing all results (except the root files)\n")

            elif pubdreg.search(NewFileLine):
                INDEX.write(date + "\n")
            elif candhreg.search(NewFileLine):
                for acandle in Candle:
                    candlHTML = "%s.html" % acandle
                    INDEX.write("<a href=\"./%s\"> %s </a>" % (candlHTML,acandle))
                    INDEX.write("<br /><br />\n")
                    candlHTML="%s/%s" % (WebArea,candlHTML)
                    createCandlHTML(CandlTmpltHTML,candlHTML,acandle,WebArea,repdir,ExecutionDate,LogFiles,cmsScimarkResults,date)
            else:
                INDEX.write(NewFileLine)

        #End of while loop on template html file
        INDEX.close()
    except IOError:
        fail("Error: Could not create index Html file for some reason, check position")

########################
#
# Grab dirs that end in strings defined in DirName
#
def getDirnameDirs(repdir,WebArea):
    Dir = os.listdir(repdir)
    def _containsDirName(elem):
        return reduce(lambda x,y: x or y,map(lambda x: x in elem, DirName))
    def _print4Lambda(elem,WebArea):
        if _verbose:
            print "Copying %s to %s\n" %  (elem,WebArea)

    dirstocp = filter(lambda x: _containsDirName(x),map(lambda x: repdir + x,Dir))
    map(lambda x: _print4Lambda(x,WebArea),dirstocp)
    syscp(dirstocp,WebArea + "/")

#######################
#
# Upload stage to remote location
def syncToRemoteLoc(stage,drive,path,port):
    stage = addtrailingslash(stage)
    cmd = "rsync"
    # We must, MUST, do os.path.normpath otherwise rsync will dump the files in the directory
    # we specify on the remote server, rather than creating the CMS_VERSION directory
    args = "--port=%s %s %s:%s" % (port,os.path.normpath(stage),drive,path)
    retval = -1
    if _dryrun:
        print              cmd + " --dry-run " + args 
        retval = os.system(cmd + " --dry-run " + args )
    else:
        retval = os.system(cmd + " " + args)
    return retval

################
# 
# Delete tmp dir if we used it
def delTmpDir():
    if os.path.exists(TMP_DIR) and IS_TMP:
        os.system("rm -Rf " + TMP_DIR)

#####################
#
# Some functions used for copying

def getRelativeDir(parent,child,keepTop=True):
    def _walkpath(path):
        dirs = []
        while True:
            head , tail = os.path.split(path)
            if tail == "":
                break
            dirs.append(tail)
            path = head
        for i in range(len(dirs)-1,-1,-1):
            adir = dirs[i]
            yield adir
        return
    pwalk = _walkpath(parent)
    n = 0
    try:
        while True:
            pwalk.next()
            n += 1
    except StopIteration:
        pass

    if keepTop:
        n = n - 1

    cwalk = _walkpath(child)
    try:
        #prewalk
        for x in range(n):
            cwalk.next()
    except StopIteration:
        print "ERROR: Unable to determine relative dir"
        sys.exit()

    relpath = ""
    try:
        while True:
            relpath=os.path.join(relpath,cwalk.next())
    except StopIteration:
        pass
    return relpath

def copytree4(src,dest,keepTop=True):
    def _getNewLocation(source,child,dst,keepTop=keepTop):
        place = getRelativeDir(source,child,keepTop=keepTop)
        return os.path.join(dst,place)
    def _copyFilter(source,dst,curdir,fsnodes,filter,dirs=False):
        for node in fsnodes:
            dontFilter = True
            filterExist = not len(filter) == 0
            if filterExist:
                dontFilter = reduce(lambda x,y: x or y,map(lambda x: fnmatch.fnmatch(node,x),filter))
            if dontFilter:
                node = os.path.join(curdir,node) # convert to absolute path
                newnode = _getNewLocation(source,node,dst)
                if dirs:
                    os.mkdir(newnode)                
                else:
                    copy2(node,newnode)
    gen  = os.walk(src)
    newloc = _getNewLocation(src,src,dest)

    os.mkdir(newloc)

    try:
        while True:
            step   = gen.next()
            curdir = step[0]
            dirs   = step[1]
            files  = step[2]
            _copyFilter(src,dest,curdir,dirs,cpDirFilter,dirs=True)
            _copyFilter(src,dest,curdir,files,cpFileFilter)        

    except StopIteration:
        pass

def syscp(srcs,dest):
    if type(srcs) == type(""):
        if os.path.exists(srcs):
            if os.path.isdir(srcs):
                copytree4(srcs,dest)
            else:
                copy2(srcs,dest)
        else:
            print "ERROR: file to be copied %s does not exist" % foo            
    else:
        for src in srcs:
            if os.path.exists(src):
                if os.path.isdir(src):
                #copy tree
                    copytree4(src,dest)
                else:
                    copy2(src,dest)
            else:
                print "ERROR: file to be copied %s does not exist" % foo
            
def print_header():
    print """
  *****************************************
   
     %s CMS-CMG Group
     CERN 2008
   
  *****************************************\n""" % PROG_NAME

if __name__ == "__main__":
    main()
