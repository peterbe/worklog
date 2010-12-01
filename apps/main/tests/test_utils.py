import unittest

class UtilsTestCase(unittest.TestCase):
    
    def test_parse_datetime(self):
        from utils import parse_datetime, DatetimeParseError
        
        r = parse_datetime('1285041600000')
        self.assertEqual(r.year, 2010)
        
        r = parse_datetime('1283140800')
        self.assertEqual(r.year, 2010)
        
        r = parse_datetime('1286744467.0')
        self.assertEqual(r.year, 2010)
        
        self.assertRaises(DatetimeParseError, parse_datetime, 'junk')
        
        
    def test_encrypt_password(self):
        from utils import encrypt_password
        
        p = encrypt_password('', log_rounds=1)
        p2 = encrypt_password('', log_rounds=1)
        self.assertNotEqual(p, p2)
        
        self.assertTrue(isinstance(p, unicode))
        self.assertTrue('$bcrypt$' in p)
        
        # simulate what the User class's check_password does
        import bcrypt
        p = 'secret'
        r = encrypt_password(p, log_rounds=2)
        hashed = r.split('$bcrypt$')[-1].encode('utf8')
        self.assertEqual(hashed, bcrypt.hashpw(p, hashed))
        
    def test_valid_email(self):
        from utils import valid_email
        self.assertTrue(valid_email('peterbe@gmail.com'))
        self.assertTrue(valid_email("peter'be@gmail.com"))
        
        self.assertTrue(not valid_email('peterbe @gmail.com'))
        self.assertTrue(not valid_email("peter'be@gmai"))
        
    def test_data_to_xml(self):
        from utils.datatoxml import dict_to_xml, list_to_xml
        peter = {'name':'Peter', 'straight': True, 'height':1.93, 'age':30}
        xml = dict_to_xml(peter, "Person")
        self.assertTrue('<Person' in xml)
        self.assertTrue('<age>30</age>' in xml)
        self.assertTrue('<straight>true</straight>' in xml)
        self.assertTrue('<name>Peter</name>' in xml)
        self.assertTrue('<height>1.93</height>' in xml)
        self.assertTrue('</Person>' in xml)
        
        wilson = {'name':u'Wilson', 'straight': False, 'height':1.73, 'age':None}
        xml = dict_to_xml(wilson, "Person")
        self.assertTrue('<age/>' in xml)
        self.assertTrue('<straight>false</straight>' in xml)
        self.assertTrue('<name>Wilson</name>' in xml)
        people = [peter, wilson]
        
        xml = list_to_xml(people, "person")
        self.assertEqual(xml.count('<person>'), 2)
        self.assertTrue('<height>1.93</height>' in xml)
        self.assertTrue('<height>1.73</height>' in xml)
        self.assertTrue('<age>30</age>' in xml)
        self.assertTrue('<age/>' in xml)
        
        xml = dict_to_xml(dict(people=people), "People")
        
        pig = {'legs': 4, 'color': 'pink', 'eggs': None}
        chicken = {'legs': 2, 'color':'white', 'eggs':2}
        animals = [pig, chicken]
        xml = dict_to_xml(dict(animals=animals), "Animals")
        self.assertTrue('</Animals>' in xml)
        self.assertTrue('<animals>' in xml)
        self.assertEqual(xml.count('<animal>'), 2)
        
    def test_random_string(self):
        from utils import random_string
        
        x = random_string(10)
        self.assertEqual(len(x), 10)
        y = random_string(10)
        self.assertEqual(len(y), 10)
        self.assertNotEqual(x, y)
        
        
        
