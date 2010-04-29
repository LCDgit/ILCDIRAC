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
import string
from DIRAC.Core.Workflow.Parameter                  import *
from DIRAC.Core.Workflow.Module                     import *
from DIRAC.Core.Workflow.Step                       import *
from DIRAC.Core.Workflow.Workflow                   import *
from DIRAC.Core.Workflow.WorkflowReader             import *
from DIRAC.Interfaces.API.Job                       import Job
#from DIRAC.Core.Utilities.File                      import makeGuid
#from DIRAC.Core.Utilities.List                      import uniqueElements
from DIRAC                                          import gConfig
 
COMPONENT_NAME='/WorkflowLib/API/ILCJob' 

class ILCJob(Job):
  """Main ILC job definition utility
  
  Each application is configured using specific interface
  
  The needed files are passed to the L{setInputSandbox} method
  
  Each application corresponds to a module that is called from the JobAgent, on the worker node. This module is defined below by modulename. 
  All available modules can be found in ILCDIRAC.Worflow.Modules.
  """
  def __init__(self,script=None):
    """Instantiates the Workflow object and some default parameters.
    """
    Job.__init__(self,script)
    self.importLocation = 'ILCDIRAC.Workflow.Modules'
    self.StepCount = 0
    self.ioDict = {}
  
  def setMokka(self,appVersion,steeringFile,inputGenfile=None,macFile = None,detectorModel='',nbOfEvents=None,startFrom=1,dbslice='',outputFile=None,logFile='',debug=False):
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
       @return: S_OK() or S_ERROR()
    """
    
    kwargs = {'appVersion':appVersion,'steeringFile':steeringFile,'inputGenfile':inputGenfile,'macFile':macFile,'DetectorModel':detectorModel,'NbOfEvents':nbOfEvents,'StartFrom':startFrom,'outputFile':outputFile,'DBSlice':dbslice,'logFile':logFile,'debug':debug}
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
    self.addToOutputSandbox.append(logName)
      
    if os.path.exists(steeringFile):
      self.log.verbose('Found specified steering file %s'%steeringFile)
      self.addToInputSandbox.append(steeringFile)
    else:
      return self._reportError('Specified steering file %s does not exist' %(steeringFile),__name__,**kwargs)

    if(inputGenfile):
      if os.path.exists(inputGenfile):
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
      else:
        if(os.path.exists(dbslice)):
          self.addToInputSandbox.append(dbslice)
        else:
          return self._reportError('Specified DB slice %s does not exist'%dbslice,__name__,**kwargs)

    if not inputGenfile and not macFile:
      return self._reportError('No generator file nor mac file specified, please check what you want to run',__name__,**kwargs)

    if not macFile:
      if not nbOfEvents:
        return self._reportError("No nbOfEvents specified and no mac file given, please specify either one",__name__,**kwargs )

    stepName = 'RunMokka'

    
    ##now define MokkaAnalysis
    moduleName = "MokkaAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('Mokka module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    step = StepDefinition('Mokka')
    step.addModule(module)
    moduleInstance = step.createModuleInstance('MokkaAnalysis','Mokka')
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
    stepInstance = self.workflow.createStepInstance('Mokka',stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("steeringFile",steeringFile)
    if inputGenfile:
      stepInstance.setValue("stdhepFile",inputGenfile)
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
    
  def setMarlin(self,appVersion,xmlfile,gearfile=None,inputslcio=None,evtstoprocess=None,logFile='',debug=False):
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
      @return: S_OK() or S_ERROR()
    """
    kwargs = {'appVersion':appVersion,'XMLFile':xmlfile,'GEARFile':gearfile,'inputslcio':inputslcio,'evtstoprocess':evtstoprocess,'logFile':logFile,'debug':debug}
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
    self.addToOutputSandbox.append(logName)

    if os.path.exists(xmlfile):
      self.log.verbose('Found specified XML file %s'%xmlfile)
      self.addToInputSandbox.append(xmlfile)
    else:
      return self._reportError('Specified XML file %s does not exist' %(xmlfile),__name__,**kwargs)
    if gearfile:
      if os.path.exists(gearfile):
        self.log.verbose('Found specified GEAR file %s'%gearfile)
        self.addToInputSandbox.append(gearfile)
      else:
        return self._reportError('Specified GEAR file %s does not exist' %(gearfile),__name__,**kwargs)
    else:
      if self.ioDict.has_key("MokkaStep"):
        gearfile="GearOutput.xml"
      else:
        return self._reportError('As Mokka do not run before, you need to specify gearfile')

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


    stepName = 'RunMarlin'

    
    ##now define MokkaAnalysis
    moduleName = "MarlinAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('Marlin module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    step = StepDefinition('Marlin')
    step.addModule(module)
    moduleInstance = step.createModuleInstance('MarlinAnalysis','Marlin')
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("inputXML","","string","","",False,False,"Name of the input XML file"))
    step.addParameter(Parameter("inputGEAR","","string","","",False,False,"Name of the input GEAR file"))
    step.addParameter(Parameter("inputSlcio","","string","","",False,False,"Name of the input slcio file"))
    step.addParameter(Parameter("EvtsToProcess",-1,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Number of events to process"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance('Marlin',stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("applicationLog",logName)
    if(inputslcioStr):
      stepInstance.setValue("inputSlcio",inputslcioStr)
    else:
      if not self.ioDict.has_key("MokkaStep"):
        raise TypeError,'Expected previously defined Mokka step for input data'
      stepInstance.setLink('inputSlcio',self.ioDict["MokkaStep"],'outputFile')
    stepInstance.setValue("inputXML",xmlfile)
    stepInstance.setValue("inputGEAR",gearfile)
    if(evtstoprocess):
      stepInstance.setValue("EvtsToProcess",evtstoprocess)
    else:
      if self.ioDict.has_key(self.StepCount-1):
        stepInstance.setLink('EvtsToProcess',self.ioDict[self.StepCount-1],'numberOfEvents')
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
    
  def setSLIC(self,appVersion,macFile,inputGenfile=None,detectorModel='',nbOfEvents=10000,startFrom=1,outputFile=None,logFile='',debug = False):
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
       @return: S_OK() or S_ERROR()
    """
    
    kwargs = {'appVersion':appVersion,'steeringFile':macFile,'inputGenfile':inputGenfile,'DetectorModel':detectorModel,'NbOfEvents':nbOfEvents,'StartFrom':startFrom,'outputFile':outputFile,'logFile':logFile,'debug':debug}
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
      else:
        if os.path.exists(inputGenfile):
          self.addToInputSandbox.append(inputGenfile)    
        else:
          return self._reportError("Input generator file %s cannot be found"%(inputGenfile),__name__,**kwargs )

    if not macFile and not inputGenfile:
      return self._reportError("No mac file nor generator file specified, cannot do anything",__name__,**kwargs )
    
    detectormodeltouse = os.path.basename(detectorModel).rstrip(".zip")
    if os.path.exists(detectorModel):
      self.addToInputSandbox(detectorModel)
      
    stepName = 'RunSLIC'

    
    ##now define MokkaAnalysis
    moduleName = "SLICAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('SLIC module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    step = StepDefinition('SLIC')
    step.addModule(module)
    moduleInstance = step.createModuleInstance('SLICAnalysis','SLIC')
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
    stepInstance = self.workflow.createStepInstance('SLIC',stepName)
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
  
  def setLCSIM(self,appVersion,xmlfile,inputslcio=None,evtstoprocess=None,aliasproperties = None, logFile='', debug = False):
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
       @return: S_OK() or S_ERROR()
    """
    kwargs = {'appVersion':appVersion,'xmlfile':xmlfile,'inputslcio':inputslcio,'evtstoprocess':evtstoprocess,"aliasproperties":aliasproperties,'logFile':logFile, 'debug':debug}
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
      else:
        if aliasproperties.lower().find("lfn:"):
          self.addToInputSandbox.append(aliasproperties)
        else:
          if os.path.exists(aliasproperties):
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
    self.addToOutputSandbox.append(logName)

    if os.path.exists(xmlfile):
      self.addToInputSandbox.append(xmlfile)
    else:
      return self._reportError("Cannot find specified input xml file %s, please fix !"%(xmlfile),__name__,**kwargs)
    
    self.StepCount +=1
    stepName = 'RunLCSIM'

    
    ##now define LCSIMAnalysis
    moduleName = "LCSIMAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('LCSIM module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    step = StepDefinition('LCSIM')
    step.addModule(module)
    moduleInstance = step.createModuleInstance('LCSIMAnalysis','LCSIM')
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("inputXML","","string","","",False,False,"Name of the source directory to use"))
    step.addParameter(Parameter("inputSlcio","","string","","",False,False,"Name of the input slcio file"))
    step.addParameter(Parameter("aliasproperties","","string","","",False,False,"Name of the alias properties file"))
    step.addParameter(Parameter("EvtsToProcess",-1,"int","","",False,False,"Number of events to process"))
    step.addParameter(Parameter("debug",False,"bool","","",False,False,"Number of events to process"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance('LCSIM',stepName)
    stepInstance.setValue("applicationVersion",appVersion)
    stepInstance.setValue("applicationLog",logName)
    stepInstance.setValue("inputXML",xmlfile)
    stepInstance.setValue("debug",debug)

    if aliasproperties:
      stepInstance.setValue("aliasproperties",aliasproperties)

    if(inputslcioStr):
      stepInstance.setValue("inputSlcio",inputslcioStr)
    else:
      if not self.ioDict.has_key("SLICStep"):
        raise TypeError,'Expected previously defined SLIC step for input data'
      stepInstance.setLink('inputSlcio',self.ioDict["SLICStep"],'outputFile')
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
  
  def setRootAppli(self,appVersion, scriptpath,args=None,logFile=''):
    """Define root macro or executable execution
    @param appVersion: ROOT version to use
    @type appVersion: string
    @param scriptpath: path to macro file or executable
    @type scriptpath: string
    @param args: arguments to pass to the macro or executable
    @type args: string
    @return: S_OK,S_ERROR
    
    """
    kwargs = {'appVersion':appVersion,"macropath":scriptpath,"args":args,"logFile":logFile}
    
    if not type(appVersion) in types.StringTypes:
      return self._reportError('Expected string for version',__name__,**kwargs)
    if not type(scriptpath) in types.StringTypes:
      return self._reportError('Expected string for macro path',__name__,**kwargs)
    if args:
      if not type(args) in types.StringTypes:
        return self._reportError('Expected string for arguments',__name__,**kwargs)

    if scriptpath.find("lfn:")>-1:
      self.addToInputSandbox.append(scriptpath)
    else:
      if os.path.exists(scriptpath):
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
    self.addToOutputSandbox.append(logName)
    
    self.StepCount +=1
    stepName = 'RunRootMacro'
    moduleName = self._rootType(scriptpath)#"RootMacroAnalysis"
    module = ModuleDefinition(moduleName)
    module.setDescription('Root Macro module definition')
    body = 'from %s.%s import %s\n' %(self.importLocation,moduleName,moduleName)
    module.setBody(body)
    step = StepDefinition('RootMacro')
    step.addModule(module)
    moduleInstance = step.createModuleInstance('RootMacroAnalysis','RootMacro')
    step.addParameter(Parameter("applicationVersion","","string","","",False, False, "Application Name"))
    step.addParameter(Parameter("applicationLog","","string","","",False,False,"Name of the log file of the application"))
    step.addParameter(Parameter("macro","","string","","",False,False,"Name of the source directory to use"))
    step.addParameter(Parameter("args","","string","","",False,False,"Name of the input slcio file"))

    self.workflow.addStep(step)
    stepInstance = self.workflow.createStepInstance('LCSIM',stepName)
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
  
  def _rootType(self,name):
    modname = ''
    
    if name.endswith((".C",".cc",".cxx",".c")): 
      modname = "RootMacroAnalysis"
    else:
      modname = "RootExecutableAnalysis"
    return modname
  