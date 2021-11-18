import os
import unittest

from srmdecode import Decoder


class SrmDecodeTestCase(unittest.TestCase):
    def test_srmx_export_data(self):
        with open(self._resource('srmx-exported-case1.csv'), 'r') as f:
            csv = f.read()
        with open(self._resource('pc7-case1.srm'), 'rb') as f:
            d = Decoder()
            records = d.decode(f)

        decoded = ('Time,Speed [km/h],Power [watt],Cadence,Heartrate,'
                   'Temperature [℃],Altitude [m],latitude,longitude'
                   "\n")
        for r in records:
            decoded += (f'{r.timestamp.strftime("%H:%M:%S")},'
                        f'{r.kph:.1f},{r.watts:.1f},{r.cadence:.1f},'
                        f'{r.heartrate:.1f},{r.temperature:.1f},'
                        f'{r.altitude:.1f},{r.latitude},{r.longitude}\n')
        self.assertEqual(csv, decoded)

    def _resource(self, name) -> str:
        return os.path.join(os.path.dirname(__file__), 'files', name)

