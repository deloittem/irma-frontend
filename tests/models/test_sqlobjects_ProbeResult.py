from unittest import TestCase
from mock import MagicMock, patch
from frontend.models.sqlobjects import ProbeResult


class TestProbeResult(TestCase):

    def setUp(self):
        self.type = "type"
        self.name = "name"
        self.doc = MagicMock()
        self.status = 1
        self.file_web = MagicMock()
        self.proberesult = ProbeResult(self.type, self.name, self.doc,
                                       self.status, self.file_web)

    def tearDown(self):
        del self.proberesult

    @patch("frontend.models.sqlobjects.IrmaFormatter")
    def test001_get_details_formatted(self, m_IrmaFormatter):
        self.proberesult.get_details()
        m_IrmaFormatter.format.assert_called_once()
        self.assertEqual(m_IrmaFormatter.format.call_args[0][0],
                         self.name)

    @patch("frontend.models.sqlobjects.IrmaFormatter")
    def test002_get_details_not_formatted(self, m_IrmaFormatter):
        self.proberesult.get_details(formatted=False)
        m_IrmaFormatter.format.assert_not_called()
