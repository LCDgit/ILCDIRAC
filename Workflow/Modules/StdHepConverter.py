#####################################################
# $HeadURL$
#####################################################

__RCSID__ = "$Id$"


from DIRAC.Core.Utilities.Subprocess                      import shellCall
from ILCDIRAC.Workflow.Modules.ModuleBase                 import ModuleBase
from ILCDIRAC.Core.Utilities.CombinedSoftwareInstallation import LocalArea,SharedArea
from DIRAC                                                import S_OK, S_ERROR, gLogger
from ILCDIRAC.Core.Utilities.PrepareLibs                  import removeLibc

import DIRAC
import os
import sys

class StdHepConverter(ModuleBase):

    def __init__(self):

        ModuleBase.__init__(self)

        self.STEP_NUMBER = ''
        self.log         = gLogger.getSubLogger( "StdHepConverter" )
        self.args        = ''
        #self.result      = S_ERROR()
        self.jobID       = None

        # Step parameters
        self.applicationName = 'StdhepConverter'
        self.applicationVersion = None
        self.applicationLog     = None

        #

        if os.environ.has_key('JOBID'):
            self.jobID = os.environ['JOBID']

        #

        print "%s initialized" % ( self.__str__() )

    def execute(self):

        # Get input variables

        result = self.resolveInputVariables()

        if not result['OK']:
            return result

        # Checks

        if not self.systemConfig:
            result = S_ERROR( 'No ILC platform selected' )

        if not os.environ.has_key("LCIO"):
            self.log.error("Environment variable LCIO was not defined, cannot do anything")
            return S_ERROR("Environment variable LCIO was not defined, cannot do anything")

        # removeLibc

        removeLibc( os.path.join( os.environ["LCIO"], "lib" ) )

        # Setting up script

        LD_LIBRARY_PATH = os.path.join( "$LCIO", "lib" )
        if os.environ.has_key('LD_LIBRARY_PATH'):
            LD_LIBRARY_PATH += ":" + os.environ['LD_LIBRARY_PATH']

        PATH = "$LCIO/bin"
        if os.environ.has_key('PATH'):
            PATH += ":" + os.environ['PATH']

        scriptContent = """
#!/bin/sh

################################################################################
# Dynamically generated script by StdHepConverter module                       #
################################################################################

declare -x LD_LIBRARY_PATH=%s
declare -x PATH=%s

for STDHEPFILE in *.stdhep; do
    stdhepjob $STDHEPFILE ${STDHEPFILE/.stdhep/.slcio} -1
done

exit $?

""" %(
    LD_LIBRARY_PATH,
    PATH
)

        # Write script to file

        scriptPath = 'StdHepConverter_%s_Run_%s.sh' %( self.applicationVersion, self.STEP_NUMBER )

        if os.path.exists(scriptPath):
            os.remove(scriptPath)

        script = open( scriptPath, 'w' )
        script.write( scriptContent )
        script.close()

        # Setup log file for application stdout

        if os.path.exists(self.applicationLog):
            os.remove(self.applicationLog)

        # Run code

        os.chmod( scriptPath, 0755 )

        command = 'sh -c "./%s"' %( scriptPath )

        self.setApplicationStatus( 'StdHepConverter %s step %s' %( self.applicationVersion, self.STEP_NUMBER ) )
        self.stdError = ''

        self.result = shellCall(
            0,
            command,
            callbackFunction = self.redirectLogOutput,
            bufferLimit = 20971520
        )

        # Check results

        resultTuple = self.result['Value']
        status      = resultTuple[0]

        return self.finalStatusReport(status)


    def applicationSpecificInputs(self):

        if not self.applicationLog:
            self.applicationLog = 'StdHepConverter_%s_Run_%s.log' %( self.applicationVersion, self.STEP_NUMBER )


        return S_OK('Parameters resolved')
