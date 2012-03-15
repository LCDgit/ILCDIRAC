'''
Created on Oct 25, 2010

@author: sposs
'''
import os, urllib, zipfile, shutil, string,sys

from DIRAC.Core.Utilities.Subprocess                      import shellCall

from ILCDIRAC.Workflow.Modules.ModuleBase                    import ModuleBase
from ILCDIRAC.Core.Utilities.CombinedSoftwareInstallation import LocalArea,SharedArea
from ILCDIRAC.Core.Utilities.ResolveDependencies          import resolveDepsTar
from ILCDIRAC.Core.Utilities.resolveIFpaths               import resolveIFpaths
from ILCDIRAC.Core.Utilities.InputFilesUtilities import getNumberOfevents
from ILCDIRAC.Core.Utilities.PrepareOptionFiles           import GetNewLDLibs,GetNewPATH
from ILCDIRAC.Core.Utilities.PrepareLibs import removeLibc

from DIRAC                                                import S_OK, S_ERROR, gLogger, gConfig

class SLICPandoraAnalysis (ModuleBase):
  def __init__(self):
    ModuleBase.__init__(self)
    self.result = S_ERROR()
    self.applicationName = 'SLICPandora'
    self.pandorasettings = ""
    self.detectorxml = ""
    self.inputSLCIO = ""
    self.numberOfEvents = 0
    self.startFrom = 0
    self.eventstring = ''
      
  def applicationSpecificInputs(self):

    if self.step_commons.has_key("PandoraSettings"):
      self.pandorasettings = self.step_commons["PandoraSettings"]

    if self.step_commons.has_key("DetectorXML"):
      self.detectorxml = self.step_commons["DetectorXML"]

    if self.step_commons.has_key("inputSlcio"):
      self.inputSLCIO = self.step_commons["inputSlcio"]         

    if self.InputData:
      if not self.workflow_commons.has_key("Luminosity") or not self.workflow_commons.has_key("NbOfEvents"):
        res = getNumberOfevents(self.InputData)
        if res.has_key("nbevts") and not self.workflow_commons.has_key("Luminosity") :
          self.workflow_commons["NbOfEvents"]=res["nbevts"]
        if res.has_key("lumi") and not self.workflow_commons.has_key("NbOfEvents"):
          self.workflow_commons["Luminosity"]=res["lumi"]
        
    if self.step_commons.has_key('EvtsToProcess'):
        self.numberOfEvents = self.step_commons['EvtsToProcess']
          
    if self.step_commons.has_key('startFrom'):
      self.startFrom = self.step_commons['startFrom']
      
    if len(self.inputSLCIO)==0 and not len(self.InputData)==0:
      inputfiles = self.InputData.split(";")
      for files in inputfiles:
        if files.lower().find(".slcio")>-1:
          self.inputSLCIO += files+";"
      self.inputSLCIO = self.inputSLCIO.rstrip(";")
           
    return S_OK('Parameters resolved')
  
  def unzip_file_into_dir(self,file, dir):
    """Used to unzip the downloaded detector model
    """
    zfobj = zipfile.ZipFile(file)
    for name in zfobj.namelist():
      if name.endswith('/'):
        os.mkdir(os.path.join(dir, name))
      else:
        outfile = open(os.path.join(dir, name), 'wb')
        outfile.write(zfobj.read(name))
        outfile.close()
  
  
  def execute(self):
    self.result =self.resolveInputVariables()
    if not self.systemConfig:
      self.result = S_ERROR( 'No ILC platform selected' )
    elif not self.applicationLog:
      self.result = S_ERROR( 'No Log file provided' )
    if not self.result['OK']:
      return self.result

    if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
      self.log.verbose('Workflow status = %s, step status = %s' %(self.workflowStatus['OK'],self.stepStatus['OK']))
      return S_OK('SLIC Pandora should not proceed as previous step did not end properly')
    
    slicPandoraDir = gConfig.getValue('/Operations/AvailableTarBalls/%s/%s/%s/TarBall'%(self.systemConfig,"slicpandora",self.applicationVersion),'')
    slicPandoraDir = slicPandoraDir.replace(".tgz","").replace(".tar.gz","")
    mySoftwareRoot = ''
    localArea = LocalArea()
    sharedArea = SharedArea()
    if os.path.exists('%s%s%s' %(localArea,os.sep,slicPandoraDir)):
      mySoftwareRoot = localArea
    elif os.path.exists('%s%s%s' %(sharedArea,os.sep,slicPandoraDir)):
      mySoftwareRoot = sharedArea
    else:
      self.setApplicationStatus('SLICPandora: Could not find neither local area not shared area install')
      return S_ERROR('Missing installation of SLICPandora!')
    myslicPandoraDir = os.path.join(mySoftwareRoot,slicPandoraDir)

    ##Remove libc lib
    removeLibc(myslicPandoraDir+"/LDLibs")

    ##Need to fetch the new LD_LIBRARY_PATH
    new_ld_lib_path= GetNewLDLibs(self.systemConfig,"slicpandora",self.applicationVersion,mySoftwareRoot)

    new_path = GetNewPATH(self.systemConfig,"slicpandora",self.applicationVersion,mySoftwareRoot)

    inputfilelist = self.inputSLCIO.split(";")    
    res = resolveIFpaths(inputfilelist)
    if not res['OK']:
      self.setApplicationStatus('SLICPandora: missing slcio file')
      return S_ERROR('Missing slcio file!')
    runonslcio = res['Value'][0]
    
    if not self.detectorxml.count(".xml") or not os.path.exists(os.path.basename(self.detectorxml)):
      detmodel = self.detectorxml.replace("_pandora.xml","")
      if not os.path.exists(detmodel+".zip"):
        #retrieve detector model from web
        detector_urls = gConfig.getValue('/Operations/SLICweb/SLICDetectorModels',[''])
        if len(detector_urls[0])<1:
          self.log.error('Could not find in CS the URL for detector model')
          return S_ERROR('Could not find in CS the URL for detector model')

        for detector_url in detector_urls:
          try:
            detModel,headers = urllib.urlretrieve("%s%s"%(detector_url,detmodel+".zip"),detmodel+".zip")
          except:
            self.log.error("Download of detector model failed")
            continue
          try:
            self.unzip_file_into_dir(open(detmodel+".zip"),os.getcwd())
            break
          except:
            os.unlink(detmodel+".zip")
            continue
      #if os.path.exists(detmodel): #and os.path.isdir(detmodel):
      self.detectorxml = os.path.join(os.getcwd(),self.detectorxml)
      self.detectorxml = self.detectorxml+"_pandora.xml"
    
    if not os.path.exists(self.detectorxml):
      self.log.error('Detector model xml %s was not found, exiting'%self.detectorxml)
      return S_ERROR('Detector model xml %s was not found, exiting'%self.detectorxml)
    
    if not os.path.exists(os.path.basename(self.pandorasettings)):
      self.pandorasettings  = "PandoraSettings.xml"
      if os.path.exists(os.path.join(mySoftwareRoot,slicPandoraDir,'Settings',self.pandorasettings)):
        try:
          shutil.copy(os.path.join(mySoftwareRoot,slicPandoraDir,'Settings',self.pandorasettings),os.path.join(os.getcwd(),self.pandorasettings))
        except Exception,x:
          self.log.error('Could not copy PandoraSettings.xml, exception: %s'%x)
          return S_ERROR('Could not find PandoraSettings file')
    
    scriptName = 'SLICPandora_%s_Run_%s.sh' %(self.applicationVersion,self.STEP_NUMBER)
    if os.path.exists(scriptName): os.remove(scriptName)
    script = open(scriptName,'w')
    script.write('#!/bin/sh \n')
    script.write('#####################################################################\n')
    script.write('# Dynamically generated script to run a production or analysis job. #\n')
    script.write('#####################################################################\n')
    script.write('declare -x PATH=%s:$PATH\n'%new_path)
    script.write('echo =============================\n')
    script.write('echo PATH is \n')
    script.write('echo $PATH | tr ":" "\n"  \n')
    script.write('echo ==============\n')
    script.write('which ls\n')
    script.write('declare -x ROOTSYS=%s/ROOT\n'%(myslicPandoraDir))

    if os.environ.has_key('LD_LIBRARY_PATH'):
      script.write('declare -x LD_LIBRARY_PATH=$ROOTSYS/lib:%s/LDLibs:%s\n'%(myslicPandoraDir,new_ld_lib_path))
    else:
      script.write('declare -x LD_LIBRARY_PATH=$ROOTSYS/lib:%s/LDLibs\n'%(myslicPandoraDir))

    if os.path.exists("./lib"):
      script.write('declare -x LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH\n')
    script.write('echo =============================\n')
    script.write('echo LD_LIBRARY_PATH is \n')
    script.write('echo $LD_LIBRARY_PATH | tr ":" "\n"\n')
    script.write('echo ============================= \n')
    script.write('env | sort >> localEnv.log\n')
    prefixpath = ""
    if os.path.exists("PandoraFrontend"):
      prefixpath = "."
    elif (os.path.exists("%s/Executable/PandoraFrontend"%myslicPandoraDir)):
      prefixpath ="%s/Executable"%myslicPandoraDir
    if prefixpath:
      comm = '%s/PandoraFrontend %s %s %s %s %s\n'%(prefixpath,self.detectorxml,self.pandorasettings,runonslcio,self.outputFile,str(self.numberOfEvents))
      self.log.info("Will run %s"%comm)
      script.write(comm)
    else:
      script.close()
      self.log.error("PandoraFrontend executable is missing, something is wrong with the installation!")
      return S_ERROR("PandoraFrontend executable is missing")
    
    script.write('declare -x appstatus=$?\n')
    #script.write('where\n')
    #script.write('quit\n')
    #script.write('EOF\n')
    script.write('exit $appstatus\n')

    script.close()
    if os.path.exists(self.applicationLog): os.remove(self.applicationLog)

    os.chmod(scriptName,0755)
    comm = 'sh -c "./%s"' %(scriptName)
    self.setApplicationStatus('SLICPandora %s step %s' %(self.applicationVersion,self.STEP_NUMBER))
    self.stdError = ''
    self.result = shellCall(0,comm,callbackFunction=self.redirectLogOutput,
                            bufferLimit=20971520)
    #self.result = {'OK':True,'Value':(0,'Disabled Execution','')}
    resultTuple = self.result['Value']
    if not os.path.exists(self.applicationLog):
      self.log.error("Something went terribly wrong, the log file is not present")
      self.setApplicationStatus('%s failed terribly, you are doomed!' %(self.applicationName))
      if not self.ignoreapperrors:
        return S_ERROR('%s did not produce the expected log' %(self.applicationName))
    status = resultTuple[0]
    # stdOutput = resultTuple[1]
    # stdError = resultTuple[2]
    self.log.info( "Status after the application execution is %s" % str( status ) )

    return self.finalStatusReport(status)
    #############################################################################

  
  
  
      