# $HeadURL$
# $Id$
"""
  ILCJob : Job definition API for the ILC community
  
  Inherits from Job class in DIRAC.Interfaces.API.Job.py
  
  Add ILC specific application support

  See tutorial slides for usage, and this doc for full review of possibilities.

  @since: Feb 8, 2010

  @author: Stephane Poss and Przemyslaw Majewski
"""
from DIRAC.Core.Workflow.Parameter                  import *
from DIRAC.Core.Workflow.Module                     import *
from DIRAC.Core.Workflow.Step                       import *
from DIRAC.Core.Workflow.Workflow                   import *
from DIRAC.Core.Workflow.WorkflowReader             import *
from DIRAC.Interfaces.API.Job                       import Job
#from DIRAC.Core.Utilities.File                      import makeGuid
#from DIRAC.Core.Utilities.List                      import uniqueElements
from DIRAC                                          import gConfig, S_OK, S_ERROR

import os,types,string
 
 
COMPONENT_NAME='/WorkflowLib/API/ILCJob' 

class ILCJob(Job):
  """Main ILC job definition utility
  
  Each application is configured using specific interface
  
  The needed files are passed to the L{setInputSandbox} method
  
  Each application corresponds to a module that is called from the JobAgent, on the worker node. This module is defined below by modulename. 
  All available modules can be found in ILCDIRAC.Worflow.Modules.
  """
  def __init__(self,script=None,processlist=None):
    """Instantiates the Workflow object and some default parameters.
    """
    Job.__init__(self,script)
    self.importLocation = 'ILCDIRAC.Workflow.Modules'
    list = gConfig.getValue("/LocalSite/BannedSites",[])
    if len(list):
      self.setBannedSites(list)
    self.StepCount = 0
    self.ioDict = {}
    self.srms = ""
    self.processlist = None
    self.systemConfig = "x86_64-slc5-gcc43-opt"
    if processlist:
      self.processlist =processlist

  def setApplicationScript(self,appName,appVersion,script,arguments=None,log=None,logInOutputData=False):
    """ method needed by Ganga, and also for pyroot
    """
    if log:
      if not logInOutputData:
        self.addToOutputSandbox.append(log)
    
    self.addToInputSandbox.append(script)

    self.StepCount +=1
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %(appName,stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')
    
    # Create the GaudiApplication script module first
    moduleName = 'ApplicationScript'
    module = ModuleDefinition(moduleName)
    module.setDescription('An Application script module that can execute any provided script in the given project name and version environment')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with LHCb specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)
    name = stepDefn
    # Create Step definition
    step = StepDefinition(name)
    step.addModule(module)
    step.addModule(userData)    
    step.createModuleInstance('ApplicationScript',name)
    step.createModuleInstance('UserJobFinalization',name)    
        
    # Define step parameters
    step.addParameter(Parameter("applicationName","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the output file of the application"))
    step.addParameter(Parameter("arguments","","string","","",False,False,"arguments to pass to script"))
    step.addParameter(Parameter("script","","string","","",False,False,"Script name"))

    stepName = 'Run%sStep%s' %(appName,stepNumber)

    self.workflow.addStep(step)
    stepPrefix = '%s_' % stepName
    self.currentStepPrefix = stepPrefix

    # Define Step and its variables
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)

    stepInstance.setValue("applicationName",appName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("script",script)
    if arguments:
      stepInstance.setValue("arguments",arguments)
    if log: 
      stepInstance.setValue("applicationLog",log)

    
    currentApp = "%s.%s"%(appName.lower(),appVersion)
    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    return S_OK()          

  def getSRMFile(self,filedict=None):
    """ Helper function
        Retrieve file or list of files based on its SRM path. Must be first step in workflow.
        
        Example usage:
        
        >>> job = ILCJob()
        >>> fdict = {"file":"srm://srm-public.cern.ch/castor/cern.ch/grid/ilc/prod/clic/1tev/Z_uds/gen/0/nobeam_nobrem_0-200.stdhep","site":"CERN-SRM"}
        >>> fdict = str(fdict)
        >>> job.getSRMFile(fdict)
        
        If specified, possible to omit the input files in the next steps
        
        @param filedict: stringed Dictionary or list of stringed dictionaries 
        @type filedict: "{}" or ["{}"]
        @return: S_OK() or S_ERROR()
    """
    kwargs = {"filedict":filedict}
    if not type(filedict) == type("") and not type(filedict) == type([]):
      return self._reportError('Expected string or list of strings for filedict',__name__,**kwargs)
    
    self.StepCount +=1

    stepName = 'GetSRM'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('GetSRM',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')
    ##now define MokkaAnalysis
    moduleName = "GetSRMFile"
    module = ModuleDefinition(moduleName)
    module.setDescription('GetSRM module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.createModuleInstance('GetSRMFile',stepDefn)
    step.addParameter(Parameter("srmfiles","","string","","",False, False, "list of files to retrieve"))
    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)

    files = ""
    if type(filedict) == type(""):
      filedict = [str(filedict)]
    if type(filedict)==type([]):
      files = string.join(filedict,";")
    
    stepInstance.setValue('srmfiles',files) 
    self.srms = files
    self.ioDict["GetSRMStep"]=stepInstance.getName()
    
    return S_OK()

  def setWhizard(self,process=None,version=None,in_file=None,nbevts=0,lumi = 0,energy=None,randomseed=0,jobindex=None,outputFile=None,logFile=None,logInOutputData=False,debug=False):
    """Helper function
    
       Define Whizard step
       
       Two possibilities:
       
       1) process is specified 
       
       2) version and in_file are specified
       
       In the latter case, version is the whizard version to use and the in_file parameter is the path to the whizard.in to use.
       
       Example usage:

       >>> job = ILCJob()
       >>> job.setWhizard(process="ee_h_bb",nbevts=100)
       
       @param process: process id, if doers not exist, dirac prints out the known ones
       @type process: string
       @param version: version of whizard to use, e.g. SM or SUSY
       @type version: string
       @param in_file: path to whizard.in to use
       @type in_file: string
       @param energy: CM energy to use
       @type energy: int
       @param nbevts: number of event to generate
       @type nbevts: int
       @param lumi: luminosity to generate
       @type lumi: int
       @param randomseed: random seed to use. By default using current job ID
       @type randomseed: int
       @param jobindex: index to add to output file names so that several job can be stored in the same ouput directory
       @type jobindex: int
       @param logFile: log file name. Default is provided
       @type logFile: string
       @param logInOutputData: put the log file in the OutputData, default is False
       @type logInOutputData: bool
       @param debug: print all in stdout, default is False
       @type debug: bool
    """
    
    kwargs = {"process":process,"version":version,"in_file":in_file,"randomseed":randomseed,"energy":energy,"lumi":lumi,"nbevts":nbevts,
              "jobindex":jobindex,'logFile':logFile,"logInOutputData":logInOutputData,"debug":debug}
    if not self.processlist:
      return self._reportError('Process list was not passed, please define job = ILCJob(processlist=dirac.giveProcessList()).',__name__,**kwargs)
    if process:
      if not self.processlist.existsProcess(process)['Value']:
        self.log.error('Process %s does not exist in any whizard version, please contact responsible.'%process)
        self.log.info("Available processes are:")
        self.processlist.printProcesses()
        return self._reportError('Process %s does not exist in any whizard version.'%process,__name__,**kwargs)
      else:
        cspath = self.processlist.getCSPath(process)
        whiz_file = os.path.basename(cspath)
        version= whiz_file.replace(".tar.gz","").replace(".tgz","").replace("whizard","")
        self.log.info("Found process %s corresponding to whizard%s"%(process,version))
    if not version:
      return self._reportError("Version has to be defined somewhere",__name__,**kwargs)

    if not nbevts and not lumi:
      return self._reportError("Nb of evts has to be defined via nbevts or luminosity via lumi",__name__,**kwargs)
    if nbevts and lumi:
      self.log.info('Nb of evts and lumi have been specified, only lumi will be taken into account')
      
    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'Whizard_%s.log' %(version)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)
    if in_file:
      if in_file.lower().find("lfn:")>-1:
        self.addToInputSandbox.append(in_file)
      elif os.path.exists(in_file):
        self.addToInputSandbox.append(in_file)    
      else:
        return self._reportError('Specified input generator file %s does not exist' %(in_file),__name__,**kwargs)
        
    self.StepCount +=1
    stepName = 'RunWhizard'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('Whizard',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    moduleName = "WhizardAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('Whizard module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)    
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance('WhizardAnalysis',stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))    
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("InputFile","","string","","",False,False,"Name of the whizard.in file"))
    step.addParameter(Parameter("EvtType","","string","","",False,False,"Name of the whizard.in file"))
    if energy:
      step.addParameter(Parameter("Energy",0,"int","","",False,False,"Random seed to use"))
    if randomseed:
      step.addParameter(Parameter("RandomSeed",0,"int","","",False,False,"Random seed to use"))
    if jobindex:
      step.addParameter(Parameter("JobIndex",0,"int","","",False,False,"job index to add in final file name"))
    step.addParameter(Parameter("NbOfEvts",0,"int","","",False,False,"Nb of evts to generated per job"))
    step.addParameter(Parameter("Lumi",0,"int","","",False,False,"Luminosity to  generate per job"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Keep debug level as set in input file"))
    step.addParameter(Parameter("outputFile","","string","","",False,False,"Name of the output file of the application"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",version)
    stepInstance.setValue("applicationLog",logName)
    if in_file:
      stepInstance.setValue("InputFile",in_file)
    if process:
      stepInstance.setValue("EvtType",process)
    if energy:
      stepInstance.setValue("Energy",energy)
    if randomseed:
      stepInstance.setValue("RandomSeed",randomseed)
    if jobindex:
      stepInstance.setValue("JobIndex",jobindex)      
    stepInstance.setValue("NbOfEvts",nbevts)
    stepInstance.setValue("Lumi",lumi)
    stepInstance.setValue("debug",debug)
    if(outputFile):
      stepInstance.setValue('outputFile',outputFile)    
    currentApp = "whizard.%s"%version
    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["WhizardStep"]=stepInstance.getName()

    return S_OK()
     
  def setMokka(self,appVersion,steeringFile,inputGenfile=None,macFile = None,detectorModel='',nbOfEvents=None,startFrom=0,dbslice='',outputFile=None,logFile='',debug=False,logInOutputData=False):
    """Helper function.
       Define Mokka step
       
       steeringFile should be the path to the steering file.
       
       All options files are automatically appended to the job input sandbox.
       
       inputGenfile is the path to the generator file to read. Can be LFN:

       Example usage:

       >>> job = ILCJob()
       >>> job.setMokka('v00-01',steeringFile='clic01_ILD.steer',inputGenfile=['LFN:/ilc/some/data/somedata.stdhep'],nbOfEvents=100,logFile='mokka.log')

       If macFile is not specified, nbOfEvents must be.
       
       Modified drivers (.so files) should be put in a 'lib' directory and input as inputdata:
       
       >>> job.setInputData('lib')
       
       This 'lib' directory will be prepended to LD_LIBRARY_PATH

       @param appVersion: Mokka version
       @type appVersion: string
       @param steeringFile: Path to steering file
       @type steeringFile: string or list
       @param inputGenfile: Input generator file
       @type inputGenfile: string
       @param macFile: Input mac file
       @type macFile: string
       @param detectorModel: Mokka detector model to use (if different from steering file)
       @type detectorModel: string
       @param nbOfEvents: Number of events to process in Mokka
       @type nbOfEvents: int
       @param startFrom: Event number in the file to start reading from
       @type startFrom: int
       @param dbslice: MySQL database slice to use different geometry, needed if not standard
       @type dbslice: string
       @param logFile: Optional log file name
       @type logFile: string
       @param debug: By default, change printout level to least verbosity
       @type debug: bool
       @param logInOutputData: If set to False (default) then automatically appended to output sandbox, if True, manually add it to OutputData
       @type logInOutputData: bool
       @return: S_OK() or S_ERROR()
    """
    
    kwargs = {'appVersion':appVersion,'steeringFile':steeringFile,'inputGenfile':inputGenfile,'macFile':macFile,'DetectorModel':detectorModel,'NbOfEvents':nbOfEvents,'StartFrom':startFrom,'outputFile':outputFile,'DBSlice':dbslice,
              'logFile':logFile,'debug':debug,"logInOutputData":logInOutputData}
    if not type(appVersion) in types.StringTypes:
      return self._reportError('Expected string for version',__name__,**kwargs)
    if not type(steeringFile) in types.StringTypes:
      return self._reportError('Expected string for steering file',__name__,**kwargs)
    if inputGenfile:
      if not type(inputGenfile) in types.StringTypes:
        return self._reportError('Expected string for generator file',__name__,**kwargs)
    if macFile:
      if not type(macFile) in types.StringTypes:
        return self._reportError('Expected string for mac file',__name__,**kwargs)
    if not type(detectorModel) in types.StringTypes:
      return self._reportError('Expected string for detector model',__name__,**kwargs)
    if nbOfEvents:
      if not type(nbOfEvents) == types.IntType:
        return self._reportError('Expected int for NbOfEvents',__name__,**kwargs)
    if not type(startFrom) == types.IntType:
      return self._reportError('Expected int for StartFrom',__name__,**kwargs)
    if not type(dbslice) in types.StringTypes:
      return self._reportError('Expected string for DB slice name',__name__,**kwargs)
    if not type(debug) == types.BooleanType:
      return self._reportError('Expected bool for debug',__name__,**kwargs)
 
    self.StepCount +=1
    
    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'Mokka_%s.log' %(appVersion)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)
      
    if steeringFile:
      if os.path.exists(steeringFile):
        self.log.verbose('Found specified steering file %s'%steeringFile)
        self.addToInputSandbox.append(steeringFile)
      elif steeringFile.lower().find("lfn:")>-1:
        self.log.verbose('Found specified lfn to steering file %s'%steeringFile)
        self.addToInputSandbox.append(steeringFile)
      else:
        return self._reportError('Specified steering file %s does not exist' %(steeringFile),__name__,**kwargs)
    else:
      return self._reportError('Specified steering file %s does not exist' %(steeringFile),__name__,**kwargs)

    srmflag = False
    if(inputGenfile):
      if inputGenfile.lower().find("lfn:")>-1:
        self.addToInputSandbox.append(inputGenfile)
      elif inputGenfile.lower() == "srm":
        self.log.info("Found SRM flag, so will assume getSRMFile to have been called before")
        srmflag = True
      elif os.path.exists(inputGenfile):
        self.addToInputSandbox.append(inputGenfile)    
      else:
        return self._reportError('Specified input generator file %s does not exist' %(inputGenfile),__name__,**kwargs)
      
    if(macFile):
      if os.path.exists(macFile):
        self.addToInputSandbox.append(macFile)
      else:
        return self._reportError('Specified input mac file %s does not exist' %(macFile),__name__,**kwargs)
        
    if(dbslice):
      if dbslice.lower().find("lfn:")>-1:
        self.addToInputSandbox.append(dbslice)
      elif(os.path.exists(dbslice)):
        self.addToInputSandbox.append(dbslice)
      else:
        return self._reportError('Specified DB slice %s does not exist'%dbslice,__name__,**kwargs)

    #if not inputGenfile and not macFile:
    #  return self._reportError('No generator file nor mac file specified, please check what you want to run',__name__,**kwargs)

    if not macFile:
      if not nbOfEvents:
        return self._reportError("No nbOfEvents specified and no mac file given, please specify either one",__name__,**kwargs )

    stepName = 'RunMokka'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('Mokka',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    
    ##now define MokkaAnalysis
    moduleName = "MokkaAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('Mokka module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)    
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance('MokkaAnalysis',stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("steeringFile","","string","","",False,False,"Name of the steering file"))
    step.addParameter(Parameter("stdhepFile","","string","","",False,False,"Name of the stdhep file"))
    step.addParameter(Parameter("macFile","","string","","",False,False,"Name of the mac file"))
    step.addParameter(Parameter("detectorModel","","string","","",False,False,"Name of the detector model"))
    step.addParameter(Parameter("numberOfEvents",10000,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("startFrom",0,"int","","",False,False,"Event in Stdhep file to start from"))
    step.addParameter(Parameter("dbSlice","","string","","",False,False,"Name of the DB slice to use"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("outputFile","","string","","",False,False,"Name of the output file of the application"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Keep debug level as set in input file"))
    
    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("steeringFile",steeringFile)
    if inputGenfile:
      if not srmflag:
        stepInstance.setValue("stdhepFile",inputGenfile)
      else:
        if not self.ioDict.has_key("GetSRMStep"):
          return self._reportError("Could not find SRM step. Please check that getSRMFile is called before.",__name__,**kwargs)
        else:
          srms = self._sortSRM(self.srms)
          stepInstance.setValue("stdhepFile",srms[0])
    if macFile:
      stepInstance.setValue("macFile",macFile)
    if(detectorModel):
      stepInstance.setValue("detectorModel",detectorModel)
    if nbOfEvents:
      stepInstance.setValue("numberOfEvents",nbOfEvents)
    stepInstance.setValue("startFrom",startFrom)
    if(dbslice):
      stepInstance.setValue("dbSlice",dbslice)
    stepInstance.setValue("applicationLog",logName)
    if(outputFile):
      stepInstance.setValue('outputFile',outputFile)
    stepInstance.setValue('debug',debug)
    currentApp = "mokka.%s"%appVersion
    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["MokkaStep"]=stepInstance.getName()
    return S_OK()
    
  def setMarlin(self,appVersion,xmlfile,gearfile=None,inputslcio=None,evtstoprocess=None,logFile='',debug=False,logInOutputData=False):
    """ Define Marlin step
      Example usage:

      >>> job = ILCJob()
      >>> job.setMarlin("v00-17",xmlfile='myMarlin.xml',gearfile='GearFile.xml',inputslcio='input.slcio')
      
      If personal processors are needed, put them in a 'lib' directory, and do 
      
      >>> job.setInputData('lib')
      
      so that they get shipped to the grid site. All contents are prepended in MARLIN_DLL
      
      @param xmlfile: the marlin xml definition
      @type xmlfile: string
      @param gearfile: as the name suggests, not needed if Mokka is ran before
      @type gearfile: string
      @param inputslcio: path to input slcio, list of strings or string
      @type inputslcio: string or list
      @param evtstoprocess: number of events to process
      @type evtstoprocess: int or string
      @param debug: By default, change printout level to least verbosity
      @type debug: bool
      @param logInOutputData: If set to False (default) then automatically appended to output sandbox, if True, manually add it to OutputData
      @type logInOutputData: bool
      @return: S_OK() or S_ERROR()
    """
    kwargs = {'appVersion':appVersion,'XMLFile':xmlfile,'GEARFile':gearfile,'inputslcio':inputslcio,'evtstoprocess':evtstoprocess,'logFile':logFile,'debug':debug,"logInOutputData":logInOutputData}
    if not type(appVersion) in types.StringTypes:
      return self._reportError('Expected string for version',__name__,**kwargs)
    if not type(xmlfile) in types.StringTypes:
      return self._reportError('Expected string for xml file',__name__,**kwargs)
    if gearfile:
      if not type(gearfile) in types.StringTypes:
        return self._reportError('Expected string for gear file',__name__,**kwargs)
    if not type(debug) == types.BooleanType:
      return self._reportError('Expected bool for debug',__name__,**kwargs)
    
    self.StepCount +=1
     
    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'Marlin_%s.log' %(appVersion)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)

    if os.path.exists(xmlfile):
      self.log.verbose('Found specified XML file %s'%xmlfile)
      self.addToInputSandbox.append(xmlfile)
    elif xmlfile.lower().find("lfn:")>-1:
      self.log.verbose('Found specified lfn to XML file %s'%xmlfile)
      self.addToInputSandbox.append(xmlfile)      
    else:
      return self._reportError('Specified XML file %s does not exist' %(xmlfile),__name__,**kwargs)
    
    if gearfile:
      if os.path.exists(gearfile):
        self.log.verbose('Found specified GEAR file %s'%gearfile)
        self.addToInputSandbox.append(gearfile)
      elif gearfile.lower().count("lfn:")>0:
        self.log.verbose('Found specified LFN to GEAR file %s'%gearfile)
        self.addToInputSandbox.append(gearfile)
      else:
        return self._reportError('Specified GEAR file %s does not exist' %(gearfile),__name__,**kwargs)
    else:
      if self.ioDict.has_key("MokkaStep"):
        gearfile="GearOutput.xml"
      else:
        return self._reportError('As Mokka do not run before, you need to specify gearfile')

    inputslcioStr =''
    srmflag = False
    if(inputslcio):
      if type(inputslcio) in types.StringTypes:
        if inputslcio.lower()== "srm":
          self.log.verbose("Will assume SRM file was set in getSRMFile before.")
          srmflag = True
        else:
          inputslcio = [inputslcio]
      if not srmflag:
        if not type(inputslcio)==type([]):
          return self._reportError('Expected string or list of strings for input slcio file',__name__,**kwargs)
        #for i in xrange(len(inputslcio)):
        #  inputslcio[i] = inputslcio[i].replace('LFN:','')
        #inputslcio = map( lambda x: 'LFN:'+x, inputslcio)
        inputslcioStr = string.join(inputslcio,';')
        self.addToInputSandbox.append(inputslcioStr)


    stepName = 'RunMarlin'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('Marlin',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    
    ##now define MokkaAnalysis
    moduleName = "MarlinAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('Marlin module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)        
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance('MarlinAnalysis',stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("inputXML","","string","","",False,False,"Name of the input XML file"))
    step.addParameter(Parameter("inputGEAR","","string","","",False,False,"Name of the input GEAR file"))
    step.addParameter(Parameter("inputSlcio","","string","","",False,False,"Name of the input slcio file"))
    step.addParameter(Parameter("EvtsToProcess",-1,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Number of events to process"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("applicationLog",logName)
    if(inputslcioStr):
      stepInstance.setValue("inputSlcio",inputslcioStr)
    else:
      if not srmflag:
        if self.ioDict.has_key("MokkaStep"):
          stepInstance.setLink('inputSlcio',self.ioDict["MokkaStep"],'outputFile')
      else:
        if not self.ioDict.has_key("GetSRMStep"):
          return self._reportError("Could not find SRM step. Please check that getSRMFile is called before.",__name__,**kwargs)
        else:
          srms = self._sortSRM(self.srms)
          stepInstance.setValue("inputSlcio",string.join(srms,";"))
    stepInstance.setValue("inputXML",xmlfile)
    stepInstance.setValue("inputGEAR",gearfile)
    if(evtstoprocess):
      stepInstance.setValue("EvtsToProcess",evtstoprocess)
    else:
      if self.ioDict.has_key("MokkaStep"):
        stepInstance.setLink('EvtsToProcess',self.ioDict["MokkaStep"],'numberOfEvents')
      else :
        stepInstance.setValue("EvtsToProcess",-1)
    stepInstance.setValue("debug",debug)
        
    currentApp = "marlin.%s"%appVersion

    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["MarlinStep"]=stepInstance.getName()
    return S_OK()
    
  def setSLIC(self,appVersion,macFile,inputGenfile=None,detectorModel='',nbOfEvents=10000,startFrom=1,outputFile=None,logFile='',debug = False,logInOutputData=False):
    """Helper function.
       Define SLIC step
       
       macFile should be the path to the mac file
       
       All options files are automatically appended to the job input sandbox
       
       inputGenfile is the path to the generator file to read. Can be LFN:

       Example usage:

       >>> job = ILCJob()
       >>> job.setSLIC('v2r8p0',macFile='clic01_SiD.mac',inputGenfile=['LFN:/ilc/some/event/data/somedata.stdhep'],nbOfEvents=100,logFile='slic.log')

       @param appVersion: SLIC version
       @type appVersion: string
       @param macFile: Path to mac file
       @type macFile: string or list
       @param inputGenfile: Input generator file
       @type inputGenfile: string
       @param detectorModel: SLIC detector model to use (if different from mac file), must be base name of zip file found on http://lcsim.org/detectors
       @type detectorModel: string
       @param nbOfEvents: Number of events to process in SLIC
       @type nbOfEvents: int
       @param startFrom: Event number in the file to start reading from
       @type startFrom: int
       @param outputFile: Name of the expected output file produced, to be passed to LCSIM
       @type outputFile: string 
       @param logFile: Optional log file name
       @type logFile: string
       @param debug: not used yet
       @param logInOutputData: If set to False (default) then automatically appended to output sandbox, if True, manually add it to OutputData
       @type logInOutputData: bool
       @return: S_OK() or S_ERROR()
    """
    
    kwargs = {'appVersion':appVersion,'steeringFile':macFile,'inputGenfile':inputGenfile,'DetectorModel':detectorModel,'NbOfEvents':nbOfEvents,'StartFrom':startFrom,'outputFile':outputFile,'logFile':logFile,
              'debug':debug,"logInOutputData":logInOutputData}
    if not type(appVersion) in types.StringTypes:
      return self._reportError('Expected string for version',__name__,**kwargs)
    if macFile:
      if not type(macFile) in types.StringTypes:
        return self._reportError('Expected string for mac file',__name__,**kwargs)
    if inputGenfile:
      if not type(inputGenfile) in types.StringTypes:
        return self._reportError('Expected string for generator file',__name__,**kwargs)
    if not type(detectorModel) in types.StringTypes:
      return self._reportError('Expected string for detector model',__name__,**kwargs)
    if not type(nbOfEvents) == types.IntType:
      return self._reportError('Expected int for NbOfEvents',__name__,**kwargs)
    if not type(startFrom) == types.IntType:
      return self._reportError('Expected int for StartFrom',__name__,**kwargs)
    if not type(debug) == types.BooleanType:
      return self._reportError('Expected bool for debug',__name__,**kwargs)
     
    self.StepCount +=1
    
    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'SLIC_%s.log' %(appVersion)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)

    if macFile:  
      if os.path.exists(macFile):
        self.log.verbose('Found specified mac file %s'%macFile)
        self.addToInputSandbox.append(macFile)
      else:
        return self._reportError('Specified mac file %s does not exist' %(macFile),__name__,**kwargs)

    if(inputGenfile):
      if inputGenfile.lower().find("lfn:")>-1:
        self.addToInputSandbox.append(inputGenfile)    
      elif os.path.exists(inputGenfile):
        self.addToInputSandbox.append(inputGenfile)    
      else:
        return self._reportError("Input generator file %s cannot be found"%(inputGenfile),__name__,**kwargs )

    if not macFile and not inputGenfile:
      return self._reportError("No mac file nor generator file specified, cannot do anything",__name__,**kwargs )
    
    detectormodeltouse = os.path.basename(detectorModel).rstrip(".zip")
    if os.path.exists(detectorModel):
      self.addToInputSandbox.append(detectorModel)
      
    stepName = 'RunSLIC'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('SLIC',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    
    ##now define MokkaAnalysis
    moduleName = "SLICAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('SLIC module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance('SLICAnalysis',stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("inputmacFile","","string","","",False,False,"Name of the mac file"))
    step.addParameter(Parameter("stdhepFile","","string","","",False,False,"Name of the stdhep file"))
    step.addParameter(Parameter("detectorModel","","string","","",False,False,"Name of the detector model"))
    step.addParameter(Parameter("numberOfEvents",10000,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("startFrom",0,"int","","",False,False,"Event in Stdhep file to start from"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("outputFile","","string","","",False,False,"Name of the output file of the application"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Number of events to process"))
    
    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    if macFile:
      stepInstance.setValue("inputmacFile",macFile)
    if inputGenfile:
      stepInstance.setValue("stdhepFile",inputGenfile)
    if(detectorModel):
      stepInstance.setValue("detectorModel",detectormodeltouse)
    stepInstance.setValue("numberOfEvents",nbOfEvents)
    stepInstance.setValue("startFrom",startFrom)
    stepInstance.setValue("applicationLog",logName)
    stepInstance.setValue("debug",debug)
    if(outputFile):
      stepInstance.setValue('outputFile',outputFile)
    currentApp = "slic.%s"%appVersion
    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["SLICStep"]=stepInstance.getName()
    return S_OK()
  
  def setLCSIM(self,appVersion,xmlfile,inputslcio=None,evtstoprocess=None,aliasproperties = None, outputFile = "",logFile='', debug = False,logInOutputData=False):
    """Helper function.
       Define LCSIM step
       
       sourceDir should be the path to the source directory used, can be tar ball
       
       All options files are automatically appended to the job input sandbox
       
       Example usage:

       >>> job = ILCJob()
       >>> job.setLCSIM('',inputXML='mylcsim.lcsim',inputslcio=['LFN:/lcd/event/data/somedata.slcio'],logFile='lcsim.log')

       @param appVersion: LCSIM version
       @type appVersion: string
       @param xmlfile: Path to xml file
       @type xmlfile: string
       @param inputslcio: path to input slcio, list of strings or string
       @type inputslcio: string or list
       @param aliasproperties: Path to the alias.properties file name that will be used
       @type aliasproperties: string
       @param logFile: Optional log file name
       @type logFile: string
       @param debug: set to True to have verbosity set to 1
       @type debug: bool
       @param logInOutputData: If set to False (default) then automatically appended to output sandbox, if True, manually add it to OutputData
       @type logInOutputData: bool
       @return: S_OK() or S_ERROR()
    """
    kwargs = {'appVersion':appVersion,'xmlfile':xmlfile,'inputslcio':inputslcio,'evtstoprocess':evtstoprocess,"aliasproperties":aliasproperties,
              'logFile':logFile, "outputFile":outputFile,
              'debug':debug,"logInOutputData":logInOutputData}
    if not type(appVersion) in types.StringTypes:
      return self._reportError('Expected string for version',__name__,**kwargs)
    if not type(xmlfile) in types.StringTypes:
      return self._reportError('Expected string for XML file dir',__name__,**kwargs)
    inputslcioStr =''
    if(inputslcio):
      if type(inputslcio) in types.StringTypes:
        inputslcio = [inputslcio]
      if not type(inputslcio)==type([]):
        return self._reportError('Expected string or list of strings for input slcio file',__name__,**kwargs)
      #for i in xrange(len(inputslcio)):
      #  inputslcio[i] = inputslcio[i].replace('LFN:','')
      #inputslcio = map( lambda x: 'LFN:'+x, inputslcio)
      inputslcioStr = string.join(inputslcio,';')
      self.addToInputSandbox.append(inputslcioStr)         
    if not type(debug) == types.BooleanType:
      return self._reportError('Expected bool for debug',__name__,**kwargs)

    if aliasproperties:
      if not type(aliasproperties) in types.StringTypes:
        return self._reportError('Expected string for alias properties file',__name__,**kwargs)
      elif aliasproperties.lower().find("lfn:"):
        self.addToInputSandbox.append(aliasproperties)
      elif os.path.exists(aliasproperties):
        self.addToInputSandbox.append(aliasproperties)
      else:
        return self._reportError("Could not find alias properties files specified %s"%(aliasproperties), __name__,**kwargs)

    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'LCSIM_%s.log' %(appVersion)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)

    if os.path.exists(xmlfile):
      self.addToInputSandbox.append(xmlfile)
    else:
      return self._reportError("Cannot find specified input xml file %s, please fix !"%(xmlfile),__name__,**kwargs)
    
    self.StepCount +=1
    stepName = 'RunLCSIM'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('LCSIM',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    
    ##now define LCSIMAnalysis
    moduleName = "LCSIMAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('LCSIM module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)            
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance('LCSIMAnalysis',stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("inputXML","","string","","",False,False,"Name of the source directory to use"))
    step.addParameter(Parameter("inputSlcio","","string","","",False,False,"Name of the input slcio file"))
    step.addParameter(Parameter("aliasproperties","","string","","",False,False,"Name of the alias properties file"))
    step.addParameter(Parameter("EvtsToProcess",-1,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("outputFile","","string","","",False,False,"Name of the output file of the application"))

    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Number of events to process"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("applicationLog",logName)
    stepInstance.setValue("inputXML",xmlfile)
    stepInstance.setValue("debug",debug)
    if(outputFile):
      stepInstance.setValue('outputFile',outputFile)
      
    if aliasproperties:
      stepInstance.setValue("aliasproperties",aliasproperties)

    if(inputslcioStr):
      stepInstance.setValue("inputSlcio",inputslcioStr)
    else:
      if self.ioDict.has_key("SLICPandoraStep"):
        stepInstance.setLink('inputSlcio',self.ioDict["SLICPandoraStep"],'outputFile')
      elif self.ioDict.has_key("SLICStep"):
        stepInstance.setLink('inputSlcio',self.ioDict["SLICStep"],'outputFile')
      else:
        raise TypeError,'Expected previously defined SLIC step or SLICPandora step for input data'

    if(evtstoprocess):
      stepInstance.setValue("EvtsToProcess",evtstoprocess)
    else:
      if self.ioDict.has_key("SLICStep"):
        stepInstance.setLink('EvtsToProcess',self.ioDict["SLICStep"],'numberOfEvents')
      else :
        stepInstance.setValue("EvtsToProcess",-1)
      
    currentApp = "lcsim.%s"%appVersion

    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["LCSIMStep"]=stepInstance.getName()    
    return S_OK()
  
  def setSLICPandora(self,appVersion,detectorgeo = None,pandorasettings = None,inputslcio = None, nbevts= 0, outputFile = "",logFile='', debug = False,logInOutputData=False):
    """Helper function.
       Define SLICPandora step
              
       All options files are automatically appended to the job input sandbox
       
       Example usage:

       >>> job = ILCJob()
       >>> job.setSLICPandora('',detectorxml='mydetector.xml',inputslcio=['LFN:/lcd/event/data/somedata.slcio'])

       @param appVersion: SLICPandora version
       @type appVersion: string
       @param xmlfile: Path to detector xml file. Like SLIC step: will download the detector model if needed. Can be path to xml or detector model name
       @type xmlfile: string
       @param inputslcio: path to input slcio, list of strings or string
       @type inputslcio: string or list
       @param pandorasettings: Path to the pandora settings file name that will be used
       @type pandorasettings: string
       @param logFile: Optional log file name
       @type logFile: string
       @param debug: set to True to have verbosity set to 1
       @type debug: bool
       @param logInOutputData: If set to False (default) then automatically appended to output sandbox, if True, manually add it to OutputData
       @type logInOutputData: bool
       @return: S_OK() or S_ERROR()
    """
    kwargs = {'appVersion':appVersion,"detectorgeo":detectorgeo,"inputslcio":inputslcio,"nbevts":nbevts,"outputFile":outputFile,"logFile":logFile,
              "debug":debug,"logInOutputData":logInOutputData}
    if pandorasettings:
      if not type(pandorasettings) in types.StringTypes:
        return self._reportError('Expected string for PandoraSettings xml file',__name__,**kwargs)
      if pandorasettings.lower().count("lfn:"):
        self.addToInputSandbox.append(pandorasettings)
      elif os.path.exists(pandorasettings):
        self.addToInputSandbox.append(pandorasettings)
      else:
        return self._reportError("Could not find PandoraSettings xml files specified %s"%(pandorasettings), __name__,**kwargs)
    
    if detectorgeo:
      if not type(detectorgeo) in types.StringTypes:
        return self._reportError('Expected string for detector xml file',__name__,**kwargs)
      if detectorgeo.lower().count("lfn:"):
        self.addToInputSandbox.append(detectorgeo)
      elif os.path.exists(detectorgeo):
        self.addToInputSandbox.append(detectorgeo)
      else:
        return self._reportError("Could not find detector xml files specified %s"%(detectorgeo), __name__,**kwargs)

    if not type(debug) == types.BooleanType:
      return self._reportError('Expected bool for debug',__name__,**kwargs)

    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'SLICPandora_%s.log' %(appVersion)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)

    self.StepCount +=1
    stepName = 'RunSLICPandora'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('SLICPandora',stepNumber)
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    
    ##now define LCSIMAnalysis
    moduleName = "SLICPandoraAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('SLICPandora module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)            
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance('SLICPandoraAnalysis',stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("DetectorXML","","string","","",False,False,"Name of the detector xml to use"))
    step.addParameter(Parameter("inputSlcio","","string","","",False,False,"Name of the input slcio file"))
    step.addParameter(Parameter("PandoraSettings","","string","","",False,False,"Name of the PandoraSettings file"))
    step.addParameter(Parameter("EvtsToProcess",-1,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("outputFile","","string","","",False,False,"Name of the output file of the application"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("applicationLog",logName)
    if detectorgeo:
      stepInstance.setValue("DetectorXML",detectorgeo)
    elif self.ioDict.has_key("SLICStep"):
      stepInstance.setLink('DetectorXML',self.ioDict["SLICStep"],'detectorModel')
    stepInstance.setValue("debug",debug)
   
    if(pandorasettings):
      stepInstance.setValue("PandoraSettings",pandorasettings)
 
    if(inputslcio):
      stepInstance.setValue("inputSlcio",inputslcio)
    else:
      if not self.ioDict.has_key("LCSIMStep"):
        raise TypeError,'Expected previously defined LCSIM step for input data'
      stepInstance.setLink('inputSlcio',self.ioDict["LCSIMStep"],'outputFile')

    if(nbevts):
      stepInstance.setValue("EvtsToProcess",nbevts)
    elif self.ioDict.has_key("LCSIMStep"):
        stepInstance.setLink('EvtsToProcess',self.ioDict["LCSIMStep"],'EvtsToProcess')
    else :
      stepInstance.setValue("EvtsToProcess",-1)
    if(outputFile):
      stepInstance.setValue('outputFile',outputFile)
                
    currentApp = "slicpandora.%s"%appVersion

    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["SLICPandoraStep"]=stepInstance.getName()        
    return S_OK()
  
  
  def setRootAppli(self,appVersion, scriptpath,args=None,logFile='',logInOutputData=False):
    """Define root macro or executable execution
    
    Example usage:

    >>> job = ILCJob()
    >>> job.setRootAppli('v5.26',scriptpath="myscript.C",args="34,56,\\\\\\\"a_string\\\\\\\"}")
  
    Mind the escape characters \ so that the quotes are properly used. If not that many \ the  
    call
    
    root -b -q myscript.C\\(34,56,\\"a_string\\"\\)
    
    will fail

    @param appVersion: ROOT version to use
    @type appVersion: string
    @param scriptpath: path to macro file or executable
    @type scriptpath: string
    @param args: arguments to pass to the macro or executable
    @type args: string
    @return: S_OK,S_ERROR
    
    """
    kwargs = {'appVersion':appVersion,"macropath":scriptpath,"args":args,"logFile":logFile,"logInOutputData":logInOutputData}
    
    if not type(appVersion) in types.StringTypes:
      return self._reportError('Expected string for version',__name__,**kwargs)
    if not type(scriptpath) in types.StringTypes:
      return self._reportError('Expected string for macro path',__name__,**kwargs)
    if args:
      if not type(args) in types.StringTypes:
        return self._reportError('Expected string for arguments',__name__,**kwargs)

    if scriptpath.find("lfn:")>-1:
      self.addToInputSandbox.append(scriptpath)
    elif os.path.exists(scriptpath):
      self.addToInputSandbox.append(scriptpath)
    else:
      return self._reportError("Could not find specified macro %s"%scriptpath,__name__,**kwargs)
    
    if logFile:
      if type(logFile) in types.StringTypes:
        logName = logFile
      else:
        return self._reportError('Expected string for log file name',__name__,**kwargs)
    else:
      logName = 'ROOT_%s.log' %(appVersion)
    if not logInOutputData:
      self.addToOutputSandbox.append(logName)
    
    self.StepCount +=1
    stepName = 'RunRootMacro'
    stepNumber = self.StepCount
    stepDefn = '%sStep%s' %('RootMacro',stepNumber)    
    self._addParameter(self.workflow,'TotalSteps','String',self.StepCount,'Total number of steps')

    
    rootmoduleName = self._rootType(scriptpath)#"RootMacroAnalysis"
    module = ModuleDefinition(rootmoduleName)
    module.setDescription('Root Macro module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,rootmoduleName,rootmoduleName)
    module.setBody(body)
    #Add user job finalization module 
    moduleName = 'UserJobFinalization'
    userData = ModuleDefinition(moduleName)
    userData.setDescription('Uploads user output data files with ILC specific policies.')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)    
    userData.setBody(body)                
    step = StepDefinition(stepDefn)
    step.addModule(module)
    step.addModule(userData)
    step.createModuleInstance(rootmoduleName,stepDefn)
    step.createModuleInstance('UserJobFinalization',stepDefn)
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("script","","string","","",False,False,"Name of the source directory to use"))
    step.addParameter(Parameter("args","","string","","",False,False,"Name of the input slcio file"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance(stepDefn,stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("applicationLog",logName)
    stepInstance.setValue("script",scriptpath)
    if args:
      stepInstance.setValue("args",args)


      
    currentApp = "root.%s"%appVersion

    swPackages = 'SoftwarePackages'
    description='ILC Software Packages to be installed'
    if not self.workflow.findParameter(swPackages):
      self._addParameter(self.workflow,swPackages,'JDL',currentApp,description)
    else:
      apps = self.workflow.findParameter(swPackages).getValue()
      if not currentApp in string.split(apps,';'):
        apps += ';'+currentApp
      self._addParameter(self.workflow,swPackages,'JDL',apps,description)
    self.ioDict["RootStep"]=stepInstance.getName()    

    return S_OK() 
  #############################################################################
  def setOutputData(self,lfns,OutputSE=[],OutputPath=''):
    """Helper function, used in preference to Job.setOutputData() for ILC.

       For specifying output data to be registered in Grid storage.  If a list
       of OutputSEs are specified the job wrapper will try each in turn until
       successful.

       Example usage:

       >>> job = Job()
       >>> job.setOutputData(['Ntuple.root'])

       @param lfns: Output data file or files
       @type lfns: Single string or list of strings ['','']
       @param OutputSE: Optional parameter to specify the Storage
       @param OutputPath: Optional parameter to specify the Path in the Storage, postpented to /ilc/user/u/username/
       Element to store data or files, e.g. CERN-tape
       @type OutputSE: string or list
       @type OutputPath: string
    """
    kwargs = {'lfns':lfns,'OutputSE':OutputSE,'OutputPath':OutputPath}    
    if type(lfns)==list and len(lfns):
      outputDataStr = string.join(lfns,';')
      description = 'List of output data files'
      self._addParameter(self.workflow,'UserOutputData','JDL',outputDataStr,description)
    elif type(lfns)==type(" "):
      description = 'Output data file'
      self._addParameter(self.workflow,'UserOutputData','JDL',lfns,description)
    else:
      return self._reportError('Expected file name string or list of file names for output data',**kwargs) 
    
    if OutputSE:
      description = 'User specified Output SE'
      if type(OutputSE) in types.StringTypes:
        OutputSE = [OutputSE]
      elif type(OutputSE) != types.ListType:
        return self._reportError('Expected string or list for OutputSE',**kwargs)         
      OutputSE = ';'.join(OutputSE)
      self._addParameter(self.workflow,'UserOutputSE','JDL',OutputSE,description)

    if OutputPath:
      description = 'User specified Output Path'
      if not type(OutputPath) in types.StringTypes:
        return self._reportError('Expected string for OutputPath',**kwargs)
      # Remove leading "/" that might cause problems with os.path.join
      while OutputPath[0] == '/': OutputPath=OutputPath[1:]
      if OutputPath.count("ilc/user"):
        return self._reportError('Output path contains /ilc/user/ which is not what you want',**kwargs)
      self._addParameter(self.workflow,'UserOutputPath','JDL',OutputPath,description)

    return S_OK()
  def setBannedSites(self,sites):
    """Helper function.

       Can specify banned sites for job.  This can be useful
       for debugging purposes but often limits the possible candidate sites
       and overall system response time.

       Example usage:

       >>> job = ILCJob()
       >>> job.setBannedSites(['LCG.DESY.de','LCG.KEK.jp'])

       @param sites: single site string or list
       @type sites: string or list
    """
    bannedsites = []
    bannedsiteswp = self.workflow.findParameter("BannedSites")
    if bannedsiteswp:
      bannedsites = bannedsiteswp.getValue().split(";")
    if type(sites) == list and len(sites):
      bannedsites.extend(sites)
    elif type(sites)==type(" "):
      bannedsites.append(sites)
    else:
      kwargs = {'sites':sites} 
      return self._reportError('Expected site string or list of sites',**kwargs)
    description = 'Sites excluded by user'
    self._addParameter(self.workflow,'BannedSites','JDLReqt',string.join(bannedsites,';'),description)
    return S_OK()
    
  def _rootType(self,name):
    modname = ''
    if name.endswith((".C",".cc",".cxx",".c")): 
      modname = "RootMacroAnalysis"
    else:
      modname = "RootExecutableAnalysis"
    return modname
  
  def _sortSRM(self,srmfiles=""):
    list = []
    srmlist = srmfiles.split(";")
    for srmdict in srmlist:
      srm = eval(srmdict)['file']
      list.append(srm)
    return list
  
  