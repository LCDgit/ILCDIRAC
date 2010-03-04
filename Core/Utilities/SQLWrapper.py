# $HeadURL$
# $Id$
'''
Wrapper script to run mokka with a local database setup 
Based on Jan Engels bash script

Created on Feb 1, 2010

@author: pmajewsk
'''

from DIRAC import S_OK, S_ERROR, gLogger, gConfig, List
from DIRAC.Core.Utilities.Subprocess import shellCall
import DIRAC
import os,sys,re, tempfile

class SQLWrapper:
  def __init__(self,dumpfile='CLICMokkaDB.sql',softwareDir='./'):
    """Set initial variables"""
    if(len(dumpfile)<1):
      dumpfile='CLICMokkaDB.sql'
    self.MokkaDumpFile = os.path.basename(dumpfile)
    
    self.MokkaTMPDir = ''
    self.softDir = softwareDir
        
    """create tmp dir and track it"""
    try:
        self.MokkaTMPDir = tempfile.mkdtemp('','TMP',os.getcwd())
    except IOError, (errno,strerror):
        DIRAC.gLogger.exception("I/O error({0}): {1}".format(errno, strerror))   
        
    self.applicationLog = 'mysql.log'
         
    self.stdError = 'mysql_err.log'
        
    self.log = gLogger.getSubLogger( "SQL-wrapper" )
        
    self.mysqlInstalDir = ''           
                       
  def mysqlSetup(self):
    """Setup mysql locally in local tmp dir """
    DIRAC.gLogger.verbose('setup local mokka database')
    if os.environ.has_key('LD_LIBRARY_PATH'):
      os.environ['LD_LIBRARY_PATH']='%s/mysql4grid/lib64/mysql:%s'%(self.softDir,os.environ['LD_LIBRARY_PATH'])
    else:
      os.environ['LD_LIBRARY_PATH']='%s/mysql4grid/lib64/mysql'%self.softDir
    os.environ['PATH']='%s/mysql4grid/bin:%s'%(self.softDir,os.environ['PATH'])
    comm = self.softDir+'/mokkadbscripts/mysql-local-db-setup.sh -p ' + self.MokkaTMPDir + ' -d ' + self.MokkaDumpFile
    self.result = shellCall(0,comm,callbackFunction=self.redirectLogOutput,bufferLimit=20971520)
        
    resultTuple = self.result['Value']

    status = resultTuple[0]
    self.log.info( "Status after the application execution is %s" % str( status ) )
    failed = False
    if status != 0:
      self.log.error( "mokka-wrapper execution completed with errors:" )
      failed = True
    else:
      self.log.info( "mokka-wrapper execution completed successfully")

    if failed==True:
      self.log.error( "==================================\n StdError:\n" )
      self.log.error( self.stdError )
      #self.setApplicationStatus('%s Exited With Status %s' %(self.applicationName,status))
      self.log.error('mokka-wrapper Exited With Status %s' %(status))
      return S_ERROR('mokka-wrapper Exited With Status %s' %(status))
    # Still have to set the application status e.g. user job case.
    #self.setApplicationStatus('mokka-wrapper %s Successful' %(self.applicationVersion))
    #return S_OK('mokka-wrapper %s Successful' %(self.applicationVersion))

    if str(os.environ.get('UID_TMP')) == 'None':
      DIRAC.gLogger.error('No UID_TMP known')
      self.UID_TMP = ''
    else:
      self.UID_TMP = str(os.environ.get('UID_TMP'))
    
        
    if not self.MokkaTMPDir[-1] == '/':
      self.MokkaTMPDir += '/'
                
    self.mysqlInstalDir = self.MokkaTMPDir + self.UID_TMP 
        
    #init db
    DIRAC.gLogger.verbose('add all privilages for user consult')
    #mysql command:
    MySQLcomm = 'mysql'
    MySQLparams = ' --socket ' + self.mysqlInstalDir + '/' + '/mysql.sock' + ' -e "GRANT ALL PRIVILEGES ON *.* TO \'consult\'@\'localhost\' IDENTIFIED BY \'consult\';"'
                
    self.result = shellCall(0,MySQLcomm + MySQLparams,callbackFunction=self.redirectLogOutput,bufferLimit=20971520)
        
    resultTuple = self.result['Value']

    status = resultTuple[0]
    self.log.info( "Status after the application execution is %s" % str( status ) )
    failed = False
    if status != 0:
      self.log.error( "mysql execution completed with errors:" )
      failed = True
    else:
      self.log.info( "mysql execution completed successfully")

    if failed:
      self.log.error( "==================================\n StdError:\n" )
      self.log.error( self.stdError )
      #self.setApplicationStatus('%s Exited With Status %s' %(self.applicationName,status))
      self.log.error('mysql Exited With Status %s' %(status))
      return S_ERROR('mysql Exited With Status %s' %(status))
    # Still have to set the application status e.g. user job case.
    #self.setApplicationStatus('mokka-wrapper %s Successful' %(self.applicationVersion))
        
    #test query
    DIRAC.gLogger.verbose('test query to mysql')
    MySQLcomm = 'mysql'
    MySQLparams = ' --socket ' + self.mysqlInstalDir + '/' + '/mysql.sock' + ' -uconsult -pconsult -e "show databases;"'
        
    self.result = shellCall(0,MySQLcomm + MySQLparams,callbackFunction=self.redirectLogOutput,bufferLimit=20971520)
        
    resultTuple = self.result['Value']

    status = resultTuple[0]
    self.log.info( "Status after the application execution is %s" % str( status ) )
    failed = False
    if status != 0:
      self.log.error( "mysql client execution completed with errors:" )
      failed = True
    else:
      self.log.info( "mysql client execution completed successfully")

    if failed:
      self.log.error( "==================================\n StdError:\n" )
      self.log.error( self.stdError )
      #self.setApplicationStatus('%s Exited With Status %s' %(self.applicationName,status))
      self.log.error('mysql Exited With Status %s' %(status))
      return S_ERROR('mysql Exited With Status %s' %(status))
    # Still have to set the application status e.g. user job case.
    #self.setApplicationStatus('mysql client %s Successful' %(self.applicationVersion))
        
    #return S_OK('Mokka-wrapper %s Successful' %(self.applicationVersion))
    return S_OK('OK')
    
    #############################################################################
  def mysqlCleanUp(self):
    """Does mysql cleanup command. Remove socket and tmpdir with mysql db."""
        
    DIRAC.gLogger.verbose('clean up db')
    #for now:
    MySQLcleanUpComm = self.MokkaTMPDir + self.UID_TMP + '/mysql-cleanup.sh'
            
    self.result = shellCall(0,MySQLcleanUpComm,callbackFunction=self.redirectLogOutput,bufferLimit=20971520)
        
    resultTuple = self.result['Value']

    status = resultTuple[0]
    self.log.info( "Status after the application execution is %s" % str( status ) )
    failed = False
    if status != 0:
      self.log.error( "mysql-cleanup execution completed with errors:" )
      failed = True
    else:
      self.log.info( "mysql-cleanup execution completed successfully")

    if failed==True:
      self.log.error( "==================================\n StdError:\n" )
      self.log.error( self.stdError )
      #self.setApplicationStatus('%s Exited With Status %s' %(self.applicationName,status))
      self.log.error('mysql-cleanup Exited With Status %s' %(status))
      return S_ERROR('mysql-cleanup Exited With Status %s' %(status))

    #cleanup script also removes tmp
    if (os.path.exists(self.MokkaTMPDir)):
      try:
        DIRAC.gLogger.verbose('Removing tmp dir')
        os.rmdir(self.MokkaTMPDir)
      except IOError, (errno,strerror):
        DIRAC.gLogger.exception("I/O error({0}): {1}".format(errno, strerror))
        return S_ERROR('Removing tmp dir failed')
      return S_OK('OK')
    #############################################################################
        
    #############################################################################
  def redirectLogOutput(self, fd, message):
    """Redirecting logging output to file specified."""
    sys.stdout.flush()
    if message:
      if re.search('INFO Evt',message): print message
    if self.applicationLog:
      log = open(self.applicationLog,'a')
      log.write(message+'\n')
      log.close()
    else:
      self.log.error("Application Log file not defined")
    if fd == 1:
      self.stdError += message
    #############################################################################

