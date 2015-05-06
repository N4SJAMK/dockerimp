import unittest
import dockerimpimp

class TestParsePortParams(unittest.TestCase):

    def test_string_param_normal(self):
        exp = {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}]}
        res = dockerimpimp.parse_port_params("80:80")

        self.assertItemsEqual(res, exp)

    def test_string_param_with_hostip(self):
        exp = {'80/tcp': [{'HostIp': '192.168.1.101', 'HostPort': '80'}]}
        res = dockerimpimp.parse_port_params("192.168.1.101:80:80")

        self.assertDictContainsSubset(res, exp)

if __name__ == "__main__":
    unittest.main()
