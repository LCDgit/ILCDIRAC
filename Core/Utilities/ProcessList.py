'''
Interface to the processlist.whiz that contains all the processes known to WHIZARD.

@author: S. Poss
@since: Sep 21, 2010
'''
from DIRAC                    import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities.CFG import CFG
from pprint                   import pprint
import os, tempfile, shutil

class ProcessList(object):
  """ The ProcessList uses internally the CFG utility to store the processes and their properties.
  """
  def __init__(self, location):
    self.cfg = CFG()
    self.location = location
    self.OK = True
    if os.path.exists(self.location):
      self.cfg.loadFromFile(self.location)
      if not self.cfg.existsKey('Processes'):
        self.cfg.createNewSection('Processes')
    else:
      self.OK = False  
    #written = self._writeProcessList(self.location)
    #if not written:
    #  self.OK = False
      
  def _writeProcessList(self, path):
    """ Write to text
    """
    handle, tmpName = tempfile.mkstemp()
    written = self.cfg.writeToFile(tmpName)
    os.close(handle)
    if not written:
      if os.path.exists(tmpName):
        os.remove(tmpName)
      return written
    if os.path.exists(path):
      gLogger.debug("Replacing %s" % path)
    try:
      shutil.move(tmpName, path)
      return True
    except Exception, x:
      gLogger.error("Failed to overwrite process list.", x)
      gLogger.info("If your process list is corrupted a backup can be found %s" % tmpName)
      return False
    
  def isOK(self):
    """ Check if the content is OK
    """
    return self.OK
  
  def updateProcessList(self, processes):
    """ Adds a new entry or updates an existing one.
    @param processes: dictionary of processes to treat
    """
    for process, mydict in processes.items():
      if not self._existsProcess(process):
        self._addEntry(process, mydict)
        #return res
      else:
        gLogger.info("Process %s already defined in ProcessList, will replace it" % process)
        self.cfg.deleteKey("Processes/%s" % process)
        self._addEntry(process, mydict)
        #return res
    return S_OK()
    
  def _addEntry(self, process, processdic):
    """ Adds a new entry.
    """
    if not self.cfg.isSection("Processes/%s" % process):
      self.cfg.createNewSection("Processes/%s" % process)
    self.cfg.setOption("Processes/%s/TarBallCSPath" % process, processdic['TarBallCSPath'])
    self.cfg.setOption("Processes/%s/Detail" % process, processdic['Detail'])
    self.cfg.setOption("Processes/%s/Generator" % process, processdic['Generator'])
    self.cfg.setOption("Processes/%s/Model" % process, processdic['Model'])
    self.cfg.setOption("Processes/%s/Restrictions" % process, processdic['Restrictions'])
    self.cfg.setOption("Processes/%s/InFile" % process, processdic['InFile'])
    cross_section = 0
    if processdic.has_key("CrossSection"):
      cross_section = processdic["CrossSection"]
    self.cfg.setOption("Processes/%s/CrossSection" % process, cross_section)
    return S_OK()
  
  def getCSPath(self, process):
    """ Return the path to the TarBall (for install)
    @param process: process to look for
    """
    return self.cfg.getOption("Processes/%s/TarBallCSPath" % process, None)

  def getInFile(self, process):
    """ Get the associated whizard.in file to the process
    """
    return self.cfg.getOption("Processes/%s/InFile" % process, None)

  def getProcesses(self):
    """ Return the list of all processes available
    """
    processesdict = self.cfg.getAsDict("Processes")
    processes = processesdict.keys()
    return processes
  
  def getProcessesDict(self):
    """ Return all processes as a dictionary {'process':{'TarBall':Path, etc. etc.}}
    """
    return self.cfg.getAsDict("Processes")
    
  
  def existsProcess(self, process):
    """ Check if the specified process exists
    """
    return S_OK(self._existsProcess(process))

  def _existsProcess(self, process):
    """ Check that the process exists
    """
    return self.cfg.isSection('Processes/%s' % process)

  def writeProcessList(self, alternativePath = None):
    """ Write the process list
    """
    destination = self.location
    if alternativePath:
      destination = alternativePath
    written = self._writeProcessList(destination)
    if not written:
      return S_ERROR("Failed to write repository")
    return S_OK(destination) 
  
  def printProcesses(self):
    """ Dump to screen the content of the process list.
    """
    processesdict = self.cfg.getAsDict("Processes")
    #for key,value in processesdict.items():
    #  print "%s: [%s], generated with '%s' with the model '%s' using diagram restrictions %s"%(key,value['Detail'],value['Generator'],value['Model'],value['Restrictions'])
    pprint(processesdict)
  