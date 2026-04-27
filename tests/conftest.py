"""
Mocks carregados antes de qualquer import do app.
prometheus_client e prometheus_fastapi_instrumentator bloqueiam neste ambiente.
"""
import sys
from unittest.mock import MagicMock

_prom_client = MagicMock()
_prom_client.Counter = MagicMock(return_value=MagicMock())
_prom_client.Histogram = MagicMock(return_value=MagicMock())
_prom_client.Gauge = MagicMock(return_value=MagicMock())
sys.modules["prometheus_client"] = _prom_client

_mock_inst = MagicMock()
_mock_inst.instrument.return_value = _mock_inst
_mock_inst.expose.return_value = _mock_inst
_mock_pfi = MagicMock()
_mock_pfi.Instrumentator.return_value = _mock_inst
sys.modules["prometheus_fastapi_instrumentator"] = _mock_pfi
