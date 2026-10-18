import pytest
from src.capacity import capacity


@pytest.mark.parametrize("replicas,size,expected", [(3, 25, 75), (0, 25, 0)])
def test_capacity(replicas, size, expected):
    assert capacity(replicas, size) == expected
