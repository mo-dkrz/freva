'''
Created on 04.10.2012

@author: estani
'''
import pwd
import os
import sys
from ConfigParser import SafeConfigParser as Config

class User(object):
    '''
    This Class encapsulates a user (configurations, etc)
    '''
    
    BASE_DIR = 'evaluation_system'
    CONFIG_DIR = 'config'
    CACHE_DIR = 'cache'
    OUTPUT_DIR = 'output'
    PLOTS_DIR = 'plots'
    
    EVAL_SYS_CONFIG = os.path.join(CONFIG_DIR,'evaluation_system.config')
    EVAL_SYS_DEFAULT_CONFIG = os.path.normpath(os.path.dirname(sys.modules[__name__].__file__)+'/../../etc/system_default.config')
    


    def __init__(self, uid = None):
        '''
        Constructor for the current user.
        '''
        if uid is None: uid = os.getuid()
        self._userdata = pwd.getpwuid(uid)
        self._userconfig = Config()
        #try to load teh configuration from the very first time.
        self._userconfig.read([User.EVAL_SYS_DEFAULT_CONFIG, os.path.join(self._userdata.pw_dir, User.EVAL_SYS_CONFIG)])
    
    def getUserConfig(self):
        """Returns user configuration object (ConfigParser)"""
        return self._userconfig
        
    def reloadConfig(self):
        """Reloads user configuration from disk"""
        self._userconfig = Config()
        self._userconfig.read([User.EVAL_SYS_DEFAULT_CONFIG, os.path.join(self.getUserBaseDir(), User.EVAL_SYS_CONFIG)])
        return self._userconfig
    
    def writeConfig(self):
        """Writes user configuration to disk according to User.EVAL_SYS_CONFIG"""
        
        fp = open(os.path.join(self.getUserBaseDir(), User.EVAL_SYS_CONFIG), 'w')
        self._userconfig.write(fp)
        fp.close()
        
    def getName(self):  return self._userdata.pw_name
    def getUserID(self):  return self._userdata.pw_uid
    def getUserHome(self):  return self._userdata.pw_dir
    def getUserBaseDir(self): return os.path.join(self.getUserHome(), User.BASE_DIR)
    def _getUserDir(self, dir_type, tool = None):
        base_dir = dict(config=User.CONFIG_DIR, cache=User.CACHE_DIR, output=User.OUTPUT_DIR, plots=User.PLOTS_DIR)
        if tool is None:
            #return the directory where the tool configuration files are stored
            return os.path.join(self.getUserBaseDir(), base_dir[dir_type])
        else:
            #return the specific directory for the given tool            
            return os.path.join(self.getUserBaseDir(), base_dir[dir_type], tool)
        
    def getUserConfigDir(self, tool = None):
        """Return directory where all configurations for this user are stored"""
        return self._getUserDir('config', tool)
    
    def getUserCacheDir(self, tool = None):
        """Return directory where cache files for this user (might not be "only" for this user though)"""
        return self._getUserDir('cache', tool)
    
    def getUserOutputDir(self, tool = None):
        """Return directory where output data for this user is stored"""
        return self._getUserDir('output', tool)
    
    def getUserPlotsDir(self, tool = None):
        """Return directory where all plots for this user are stored"""
        return self._getUserDir('plots', tool)
    
    def prepareDir(self):
        """Prepares the configuration directory for this user if it's not already been done."""
        if os.path.isdir(self.getUserBaseDir()):
            #we assume preparation was succesfull... but we might to be sure though... 
            return
        
        if not os.path.isdir(self.getUserHome()):
            raise Exception("Can't create configuration, user HOME doesn't exist (%s)" % self.getUserHome())
        
        #create directory for the framework
        os.mkdir(self.getUserBaseDir())
        
        #create all required subdirectories
        required_dirs = [self.getUserConfigDir(), self.getUserCacheDir(), self.getUserOutputDir(), self.getUserPlotsDir()]
        for directory in required_dirs:
            if not os.path.isdir(directory):
                os.mkdir(directory)
        
