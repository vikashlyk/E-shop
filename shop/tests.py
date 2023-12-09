from decimal import Decimal
import unittest
import zoneinfo
# from backports import zoneinfo
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from shop.models import Product, Payment, OrderItem, Order
#python manage.py test shop.tests --failfast

class TestDataBase(TestCase):
    fixtures = [
        "shop/fixtures/data.json"
    ]

    # извлекаем пользователя
    def setUp(self):
        self.user = User.objects.get(username='root')
        self.p = Product.objects.all().first()

    # проверка существует ли суперпользователь
    def test_user_exists(self):
        users = User.objects.all()
        users_number = users.count()
        user = users.first()
        self.assertEqual(users_number, 1)
        self.assertEqual(user.username, 'root')
        self.assertTrue(user.is_superuser)

    #есть ли у пользователя указаный пароль
    def test_user_check_password(self):
        self.assertTrue(self.user.check_password('123'))

    #во всех моделях больше одного значения
    def test_all_data(self):
        self.assertGreater(Product.objects.all().count(), 0)
        self.assertGreater(Order.objects.all().count(), 0)
        self.assertGreater(OrderItem.objects.all().count(), 0)
        self.assertGreater(Payment.objects.all().count(), 0)

    #сервисная функция, для подсчета корзин, для конкретного пользователя
    def find_cart_number(self):
        cart_number = Order.objects.filter(user=self.user,
                                           status=Order.STATUS_CART
                                           ).count()
        return cart_number

    def test_function_get_cart(self):
        """Проверить число корзин
        1. Корзин нет
        2. Корзина создана
        3. Еще раз нужна корзина, проверяем что не создалась новая
        add @staticmethod order.ger_cart(user)
        """
        pass
        # Корзин нет
        self.assertEqual(self.find_cart_number(), 0)

        # Корзина создана
        Order.get_cart(self.user)
        self.assertEqual(self.find_cart_number(), 1)

        # Еще раз нужна корзина, проверяем что не создалась новая
        Order.get_cart(self.user)
        self.assertEqual(self.find_cart_number(), 1)

    def test_cart_older_7_days(self):
        """Существует ли корзина, которая старше 7 дней
        add @staticmethod order.ger_cart(user)
        """
        # получаем корзину
        cart = Order.get_cart(self.user)
        cart.creation_time = timezone.datetime(2000, 1, 1, tzinfo=zoneinfo.ZoneInfo('UTC'))
        cart.save()
        # старая корзина удаляется и создается новая
        cart = Order.get_cart(self.user)
        # сравниваем время
        self.assertEqual((timezone.now() - cart.creation_time).days, 0)

    def test_recalculate_order_amount_after_changing_orderitem(self):
        """Перерасчет суммы заказа при каждом изменении
        1. Получить сумму до любых изменений
        2. Получить сумму после добавления элементов
        3. Получить сумму после удаления элементов
        add add @staticmethod order.ger_cart(user)
        """

        # 1. до любых изменений
        cart = Order.get_cart(self.user)
        self.assertEqual(cart.amount, Decimal(0))

        # 2. после добавления элементов
        i = OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=2)
        i = OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=3)
        cart = Order.get_cart(self.user)
        self.assertEqual(cart.amount, Decimal(10))

        # после удаления элементов
        i.delete()
        cart = Order.get_cart(self.user)
        self.assertEqual(cart.amount, Decimal(4))

    def test_cart_status_changing_after_applying_make_order(self):
        """ Изменение статуса корзины, после применения метода Order.make_order()
        1. Изменение статуса для пустой корзины (он не должен поменяться)
        2. Изменение статуса заполненной корзины
        add order.make_order()
        """
        #  Изменение статуса для пустой корзины (он не должен поменяться)
        cart = Order.get_cart(self.user)
        cart.make_order()
        self.assertEqual(cart.status, Order.STATUS_CART)

        # Изменение статуса заполненной корзины
        OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=2)
        cart.make_order()
        self.assertEqual(cart.status, Order.STATUS_WAITING_FOR_PAYMENT)

    def test_method_get_amount_of_unpaid_orders(self):
        """Общая сумма неоплаченных заказов:
        1. Перед созданием новой корзины
        2. После создание корзины
        3. После того как корзину создали и применили cart.make_order()
        4. После оплаты заказы
        5. После удаления всех заказов
        ==================================
        Add Order.get_amount_of_unpaid_orders()
        """
        # Перед созданием новой корзины
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(13556))

        # После создание корзины
        cart = Order.get_cart(self.user)
        OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=2)
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(13556))

        # После того как корзину создали и применили cart.make_order()
        cart.make_order()
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(13560))

        # После оплаты заказы
        cart.status = Order.STATUS_PAID
        cart.save()
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(13556))

        # После удаления всех заказов
        Order.objects.all().delete()
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(0))

    def test_method_get_balance(self):
        """Позволяет получить баланс пользователя @staticmethod get_balance:
        1. Перед добавлением платежа
        2. После добавление платежа
        3. После добавления некоторых платежей
        4. Никаких плаиежей
        Add Payment.get_balance()
        """
        #  Перед добавлением платежа
        amount = Payment.get_balance(self.user)
        self.assertEqual(amount, Decimal(13000))

        # После добавление платежа
        Payment.objects.create(user=self.user, amount=100)
        amount = Payment.get_balance(self.user)
        self.assertEqual(amount, Decimal(13100))

        # После добавления некоторых платежей
        Payment.objects.create(user=self.user, amount=-50)
        amount = Payment.get_balance(self.user)
        self.assertEqual(amount, Decimal(13050))

        # Никаких платежей
        Payment.objects.all().delete()
        amount = Payment.get_balance(self.user)
        self.assertEqual(amount, Decimal(0))


    def test_auto_payment_after_apply_make_order_true(self):
        """Проверка автоматической оплаты после применения make_order()
        1. Требуемая сумма есть
        """
        Order.objects.all().delete()
        cart = Order.get_cart(self.user)
        OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=2)
        self.assertEqual(Payment.get_balance(self.user), Decimal(13000))
        cart.make_order()
        self.assertEqual(Payment.get_balance(self.user), Decimal(12996))

    def test_auto_payment_after_apply_make_order_false(self):
        """Проверка автоматической оплаты после применения make_order()
        2. Требуемой суммы нет
        """
        Order.objects.all().delete()
        cart = Order.get_cart(self.user)
        OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=50000)
        cart.make_order()
        self.assertEqual(Payment.get_balance(self.user), Decimal(13000))


    def test_auto_payment_after_add_required_payment(self):
        """Есть неоплаченный заказ =13556 и баланс =13000
        После применения платежа =556:
            - заказ должен изменить статус
            - баланс должен = 0
        """
        Payment.objects.create(user=self.user, amount=556)
        self.assertEqual(Payment.get_balance(self.user), Decimal(0))
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(0))

    def test_auto_payment_for_earlier_order(self):
        """Есть неоплаченный заказ =13556 и баланс =13000
       После создания нового заказа =1000  применение платежа=1000:
            - статус должен быть изменен только для более раннего заказа
            - и балан должен стать 13000+1000-13556
        """
        cart = Order.get_cart(self.user)
        OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=500)
        cart.make_order()
        Payment.objects.create(user=self.user, amount=1000)
        self.assertEqual(Payment.get_balance(self.user), Decimal(444))
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(1000))

    def test_auto_payment_for_all_orders(self):
        """Есть неоплаченный заказ =13556 и баланс =13000
        После создания нового заказа =1000  применение платежа=10000:
            - все заказы должны быть оплачены
        """
        cart = Order.get_cart(self.user)
        OrderItem.objects.create(order=cart, product=self.p, price=2, quantity=500)
        Payment.objects.create(user=self.user, amount=10000)
        self.assertEqual(Payment.get_balance(self.user), Decimal(9444))
        amount = Order.get_amount_of_unpaid_orders(self.user)
        self.assertEqual(amount, Decimal(0))

class TestStringMethods(unittest.TestCase):

  def test_upper(self):
      self.assertEqual('foo'.upper(), 'FOO')

  def test_isupper(self):
      self.assertTrue('FOO'.isupper())
      self.assertFalse('Foo'.isupper())

  def test_split(self):
      s = 'hello world'
      self.assertEqual(s.split(), ['hello', 'world'])

      with self.assertRaises(TypeError):
          s.split(2)