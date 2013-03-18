'''
Created on 15.03.2013

@author: estani
'''
import unittest
from evaluation_system.api.plugin_types import ParameterType, String, Float, Long, Integer

class Test(unittest.TestCase):


    def testInferType(self):
        self.assertEquals(ParameterType.infer_type(1).__class__, Integer)
        self.assertEquals(ParameterType.infer_type(1.0).__class__, Float) 
        self.assertEquals(ParameterType.infer_type(1L).__class__, Long)  
        self.assertEquals(ParameterType.infer_type('str').__class__, String)  

    def testParsing(self):
        test_cases = [(String(), 
                            [('asd', 'asd'), (None, 'None'), (1, '1'), (True, 'True')],
                            []),
                      (Integer(),
                            [('123',123),('0', 0),('-1',-1), (True, 1)],    #Do we really want this?!
                            ['+-0', 'not a number!!', None]),
                      (Float(),
                            [('123',123.0),('0', 0.0),('-1.3',-1.3), ('-1e+2',-100.0), ('+2E-2', 0.02), (False, 0.0)],
                            ['+-0', 'not a number!!', None]),
                      (Long(),
                            [('123',123L),('0', 0L),('-1',-1L), (True, 1L)],    #Do we really want this?!
                            ['+-0', 'not a number!!', None]),
                      
                      ]
        for case_type, positive_cases, negative_cases in test_cases:
            for expected, result in positive_cases:
                parsed_value = case_type.parse(expected)
                self.assertEquals(type(parsed_value), case_type.base_type)
                self.assertEquals(parsed_value, result)
            for unparseable in negative_cases:
                try:
                    self.failUnlessRaises(TypeError, case_type.parse, unparseable)
                except:
                    self.failUnlessRaises(ValueError, case_type.parse, unparseable)
            

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testInferType']
    unittest.main()