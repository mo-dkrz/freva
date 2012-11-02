'''
Created on 20.09.2012

@author: estani
'''
import json
import glob
import os
import sys

class BaselineFile(object):
    BASELINE = [
        #baseline 0 data      
        {
         "root_dir":"/gpfs_750/projects/CMIP5/data",
         "parts_dir":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version/variable/file_name".split('/'),
         "parts_dataset":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble".split('/'),
         "parts_versioned_dataset":"project/product/institute/model/experiment/time_frequency/realm/cmor_table/ensemble/version".split('/'),
         "parts_file_name":"variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time":"start_time-end_time",
         "defaults" : {"project":"cmip5", "institute":"MPI-M", "model":"MPI-ESM-LR"}
        },
        #baseline 1 data
        {
         "root_dir":"/miklip/global/prod/archive",
         "parts_dir":"project/product/institute/model/experiment/time_frequency/realm/variable/ensemble/file_name".split('/'),
         "parts_dataset":"project.product.institute.model.experiment.time_frequency.realm.variable.ensemble".split('.'),
         "parts_file_name":"variable-cmor_table-model-experiment-ensemble-time".split('-'),
         "parts_time":"start_time-end_time",
         "defaults" : {"project":"baseline1", "product":"output", "institute":"MPI-M", "model":"MPI-ESM-LR"}
         }
                ]

    def __init__(self, file_dict=None, baseline_nr=0):
        self.baseline_nr = baseline_nr
        if not file_dict: file_dict = {} 
        self.dict = file_dict
        #trim the last slash if present in root_dir
        if 'root_dir' in self.dict and self.dict['root_dir'][-1] == '/':
            self.dict['root_dir'] = self.dict['root_dir'][:-1]
        
        
    def __repr__(self):
        """returns the json representation of this object that can be use to create a copy."""
        return self.to_json()
    
    def __str__(self):
        """The string representation is the absolute path to the file."""
        return self.to_path()
    
    def __cmp__(self, other):
        if isinstance(other, BaselineFile):
            return cmp(self.to_path(), other.to_path())
        return -1

    def to_json(self):
        return json.dumps(self.dict)
    
    def to_path(self):
        #TODO: check if construction is complete and therefore can succeed
        result = self.dict['root_dir']
        for key in self.get_baseline()['parts_dir']:
            result = os.path.join(result, self.dict['parts'][key])
        return result
    
    def to_dataset(self, versioned=False):
        """Extract the dataset name (DRS) from the path"""
        result = []
        if versioned:
            if not self.is_versioned():
                raise Exception('baseline %s is not versioned!' % self.baseline_nr)
            iter_parts = self.get_baseline()['parts_versioned_dataset']
        else:  
            iter_parts = self.get_baseline()['parts_dataset']
            
        for key in iter_parts:
            result.append(self.dict['parts'][key])
        return '.'.join(result)
    
    def is_versioned(self):
        """If this baseline versions files"""
        return 'parts_versioned_dataset' in self.get_baseline()
    
    def get_version(self):
        """Return the *dataset* version from which this file is part of.
        Returns None if the dataset is not versioned"""
        if 'version' in self.dict['parts']:
            return self.dict['parts']['version']
        else:
            return None
        
    
    @staticmethod
    def from_path(path, baseline_nr=0):
        path = os.path.realpath(path)
        bl = BaselineFile._get_baseline(baseline_nr)
    
        #trim root_dir
        if not path.startswith(bl['root_dir'] + '/'):
            raise Exception("This file does not correspond to baseline %s" % baseline_nr)                                                         
        
        parts = path[len(bl['root_dir'])+1:].split('/')
        
        #check the number of parts
        if len(parts) != len(bl['parts_dir']):
            raise Exception("Can't parse this path. Expected %d elements but got %d." % (len(bl['parts_dir']), len(parts)))
        
        #first the dir
        result = {}
        result['root_dir'] = bl['root_dir']
        result['parts'] = {}
        for i in range(len(bl['parts_dir'])):
            result['parts'][bl['parts_dir'][i]] = parts[i]
        
        #split file name
        ##(extract .nc before splitting)
        parts = result['parts']['file_name'][:-3].split('_')
        if len(parts) == len( bl['parts_file_name']) - 1 \
            and 'r0i0p0' in parts :
            #no time
            parts.append(None)
        for i in range(len(bl['parts_file_name'])):
            result['parts'][bl['parts_file_name'][i]] = parts[i]
        
        bl_file = BaselineFile(result, baseline_nr=baseline_nr)
        
        return bl_file
    
    def get_baseline(self):
        return BaselineFile._get_baseline(self.baseline_nr)
    
    @staticmethod
    def _get_baseline(baseline_nr):
        """Returns the Object representing the baseline given.
        Throws an exception if there's no such baseline implemented.
        (NOTE: baseline refers to the different states of data for comparison in the MiKlip project"""
        if baseline_nr < 0 or baseline_nr > len(BaselineFile.BASELINE) - 1:
            raise Exception("Baseline %s not implemented yet." % baseline_nr)
        return BaselineFile.BASELINE[baseline_nr]
    
    @staticmethod
    def from_dict(file_dict, baseline_nr=0):
        #need to check file_dict is as expected...
        #if 'baseline_nr' in file_dict:
        #    baseline_nr = file_dict['baseline_nr']
        #    del file_dict['baseline_nr']
        return BaselineFile(file_dict, baseline_nr=baseline_nr)
        
    @staticmethod
    def from_json(json_str, baseline_nr=0):
        return BaselineFile.from_dict(json.loads(json_str), baseline_nr=baseline_nr)
    
    @staticmethod
    def search(baseline_nr=0, latest_version=True, **partial_dict):
        """Search for files from the given parameters as part of the baseline names.
        returns := Generator returning matching Baseline files"""
        bl = BaselineFile._get_baseline(baseline_nr)
        search_dict = bl['defaults'].copy()
        search_dict.update(partial_dict)
        
        #only baseline 0 is versioned
        if latest_version and (baseline_nr > 0 or 'version' in partial_dict):
            latest_version = False
        
        local_path = bl['root_dir']
        for key in bl['parts_dir']:
            if key in search_dict:
                local_path = os.path.join(local_path, search_dict[key])
                del search_dict[key]    #remove it so we can see if all keys matched
            else:
                local_path = os.path.join(local_path, "*")
        
        if search_dict:
            #ok, there are typos or non existing constraints in the search.
            #just report them to stderr
            sys.stderr.write("WARNING: There where unused constraints: %s\n" % ','.join(search_dict))
            raise Exception("Unknown parameter(s) %s\nFor Baseline %s try one of: %s" % 
                            (','.join(search_dict), baseline_nr, ','.join(bl['parts_dir'])))
        #if the latest version is not required we may use a generator and yield a value as soon as it is found
        #If not we need to parse all until we can give the results out. We are not storing more than the latest
        #version, but if we could assure a certain order we return values as soon as we are done with a dataset
        datasets = {}
        for path in glob.iglob(local_path):
            blf = BaselineFile.from_path(path, baseline_nr)
            if not latest_version:
                yield blf
            else:
                #if not we need to check if the corresponding dataset version is recent
                ds = blf.to_dataset(versioned=False)
                if ds not in datasets or datasets[ds][0].get_version() < blf.get_version():
                    #if none or a newer version is found, reinit the dataset list
                    datasets[ds] = [blf]
                elif datasets[ds][0].get_version() == blf.get_version():
                    #if same version, add to previous (we are gathering multiple files per dataset) 
                    datasets[ds].append(blf)
                
        if latest_version:
            #then return the results stored in datasets
            for latest_version_file in [v for sub in datasets.values() for v in sub]:
                yield latest_version_file
        
        
