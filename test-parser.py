import unittest
import dockerimpimp

class TestParsePortParams(unittest.TestCase):

    def test_string_param_normal(self):
        exp = {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}]}
        res = dockerimpimp.parse_port_params("80:80")

        self.assertDictContainsSubset(res, exp)

    def test_string_param_diff_ports(self):
        exp = {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]}
        res = dockerimpimp.parse_port_params("8080:80")

        self.assertDictContainsSubset(res, exp)

    def test_string_param_with_hostip(self):
        exp = {'80/tcp': [{'HostIp': '192.168.1.101', 'HostPort': '80'}]}
        res = dockerimpimp.parse_port_params("192.168.1.101:80:80")

        self.assertDictContainsSubset(res, exp)

    def test_string_param_with_prot(self):
        exp = {'80/udp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}]}
        res = dockerimpimp.parse_port_params("80:80/udp")

        self.assertDictContainsSubset(res, exp)

    def test_string_param_full(self):
        exp = {'80/udp': [{'HostIp': '192.168.1.101', 'HostPort': '80'}]}
        res = dockerimpimp.parse_port_params("192.168.1.101:80:80/udp")

        self.assertDictContainsSubset(res, exp)

    def test_list_param_two_normals(self):
        exp = {
                '80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}],
                '443/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '443'}]
        }
        res = dockerimpimp.parse_port_params(["80:80", "443:443"])

        self.assertDictContainsSubset(res, exp)

    def test_list_param_two_complex(self):
        exp = {
                '80/udp': [{'HostIp': '0.0.0.0', 'HostPort': '80'}],
                '443/tcp': [{'HostIp': '192.168.1.101', 'HostPort': '443'}]
        }
        res = dockerimpimp.parse_port_params(["80:80/udp", "192.168.1.101:443:443"])

        self.assertDictContainsSubset(res, exp)

if __name__ == "__main__":
    unittest.main()
