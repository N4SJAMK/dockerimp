import unittest
import dockerimpimp

class TestParsePortParams(unittest.TestCase):

    def test_none_param(self):
        res, err = dockerimpimp.parse_port_params(None)

        self.assertIsNone(res)
        self.assertIsNone(err)

    def test_invalid_param_long(self):
        res, err = dockerimpimp.parse_port_params("1.2.3.4:80:80:1234")

        self.assertIsNone(res)
        self.assertIsNotNone(err)

    def test_string_simple_expose(self):
        exp = {'80/tcp': None}
        res, err = dockerimpimp.parse_port_params("80")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_string_prot_expose(self):
        exp = {'80/udp': None}
        res, err = dockerimpimp.parse_port_params("80/udp")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_list_expose(self):
        exp = {'80/tcp': None, '443/tcp': None}
        res, err = dockerimpimp.parse_port_params(["80", "443"])

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_string_param_normal(self):
        exp = {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}]}
        res, err = dockerimpimp.parse_port_params("80:80")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_string_param_diff_ports(self):
        exp = {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]}
        res, err = dockerimpimp.parse_port_params("8080:80")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_string_param_with_hostip(self):
        exp = {'80/tcp': [{'HostIp': '192.168.1.101', 'HostPort': '80'}]}
        res, err = dockerimpimp.parse_port_params("192.168.1.101:80:80")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_string_param_with_prot(self):
        exp = {'80/udp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}]}
        res, err = dockerimpimp.parse_port_params("80:80/udp")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_string_param_full(self):
        exp = {'80/udp': [{'HostIp': '192.168.1.101', 'HostPort': '80'}]}
        res, err = dockerimpimp.parse_port_params("192.168.1.101:80:80/udp")

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_list_param_two_normals(self):
        exp = {
                '80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}],
                '443/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '443'}]
        }
        res, err = dockerimpimp.parse_port_params(["80:80", "443:443"])

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

    def test_list_param_two_complex(self):
        exp = {
                '80/udp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}],
                '443/tcp': [{'HostIp': '192.168.1.101', 'HostPort': '443'}]
        }
        res, err = dockerimpimp.parse_port_params(["80:80/udp", "192.168.1.101:443:443"])

        self.assertDictContainsSubset(res, exp)
        self.assertIsNone(err)

if __name__ == "__main__":
    unittest.main()
