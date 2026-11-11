import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from ledger import services
from ledger.models import Customer, Profile, Role
from ledger.services import Item

PASSWORD = "Correct-Horse-Battery-9"


def make_user(email, role):
    User = get_user_model()
    user = User.objects.create_user(username=email, email=email, password=PASSWORD, first_name=role.title())
    Profile.objects.create(user=user, role=role)
    return user


@pytest.fixture
def owner(db):
    return make_user("owner@example.com", Role.OWNER)


@pytest.fixture
def staff(db):
    return make_user("staff@example.com", Role.STAFF)


def logged_in(user) -> Client:
    c = Client()
    r = c.post("/api/ledger/auth/login/", {"email": user.email, "password": PASSWORD}, content_type="application/json")
    assert r.status_code == 200, r.content
    return c


@pytest.fixture
def owner_client(owner):
    return logged_in(owner)


@pytest.fixture
def staff_client(staff):
    return logged_in(staff)


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Acme Ltd", phone="+254712345678", email="acme@example.com")


@pytest.fixture
def tab_customer(db):
    return Customer.objects.create(name="Tab Co", billing=Customer.Billing.TAB, email="tab@example.com")


@pytest.fixture
def paper(owner):
    return services.add_product(owner, opening_qty=20, name="A4 paper ream", price=650, cost_price=500, reorder_level=5)


@pytest.fixture
def books(owner):
    return services.add_product(owner, opening_qty=100, name="Exercise book", price=45, cost_price=30, vat_exempt=True)


def item(product, qty, price=None):
    return Item(product.name, qty, product.price if price is None else price, product.vat_exempt, product)


def custom(desc, qty, price, exempt=False):
    return Item(desc, qty, price, exempt)
