from tests.factories import ProductFactory, CustomerOrderFactory

def test_factories_smoke(db):
    assert ProductFactory().pk is not None
    assert CustomerOrderFactory().pk is not None