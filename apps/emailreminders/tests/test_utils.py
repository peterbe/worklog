import unittest
from apps.emailreminders import reminder_utils as utils
class UtilsTestCase(unittest.TestCase):
    
    def test_parse_time(self):
        text = "3pm something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (15, 0))
        
        text = "3am something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (3, 0))

        text = "0am something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (0, 0))
        
        text = "3.20pm something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (15, 20))

        text = "3.50am something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (3, 50))

        text = "10.50pm something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (22, 50))
        
        text = "Not first 3pm something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "Not first 3pm something 10.30")
        self.assertEqual(time, None)
        
        text = "9.15 something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (9, 15))
        
        text = "9:15 something 10.30"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "something 10.30")
        self.assertEqual(time, (9, 15))
        
        text = "9.1500 precision"
        text, time = utils.parse_time(text)
        self.assertEqual(text, "9.1500 precision")
        self.assertEqual(time, None)

    def test_parse_time_failing(self):
        self.assertRaises(utils.ParseEventError, 
                          utils.parse_time, '20pm something')

        self.assertRaises(utils.ParseEventError,
                          utils.parse_time, '10:70pm something')

        
    def test_duration(self):
        text = "60min something"
        text, duration = utils.parse_duration(text)
        self.assertEqual(duration, 60)
        self.assertEqual(text, "something")

        text = "1 day something"
        text, duration = utils.parse_duration(text)
        self.assertEqual(duration, 60 * 24)
        self.assertEqual(text, "something")
        
        text = "1.5 days something"
        text, duration = utils.parse_duration(text)
        self.assertEqual(duration, 60 * 24 + 60 * 12)
        self.assertEqual(text, "something")
        
        text = "2.5 minutes something"
        text, duration = utils.parse_duration(text)
        self.assertEqual(duration, 2.5)
        self.assertEqual(text, "something")
        
        text = "2.5h something"
        text, duration = utils.parse_duration(text)
        self.assertEqual(duration, 2.5 * 60)
        self.assertEqual(text, "something")
        
        
        

    
