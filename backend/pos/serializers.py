from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Product, Customer, Order, OrderItem, Payment, StockMovement


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "description", "product_count", "created_at"]

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "barcode", "category", "category_name",
            "price", "cost_price", "stock_quantity", "low_stock_threshold",
            "is_active", "is_low_stock", "image", "image_url",
            "created_at", "updated_at"
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email", "loyalty_points", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "unit_price", "discount", "total_price"]


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "unit_price", "discount"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "order", "method", "amount", "status",
            "mpesa_phone", "mpesa_checkout_request_id", "mpesa_receipt_number",
            "mpesa_transaction_date", "cash_tendered", "change_given",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "mpesa_checkout_request_id", "mpesa_merchant_request_id",
            "mpesa_receipt_number", "mpesa_transaction_date"
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "customer_name",
            "cashier", "cashier_name", "status",
            "subtotal", "discount_amount", "tax_amount", "total_amount",
            "notes", "items", "payments", "created_at", "updated_at"
        ]
        read_only_fields = ["order_number", "cashier", "subtotal", "tax_amount", "total_amount"]


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ["customer", "discount_amount", "notes", "items"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        request = self.context.get("request")
        order = Order.objects.create(cashier=request.user, **validated_data)

        for item_data in items_data:
            product = item_data["product"]
            quantity = item_data["quantity"]
            OrderItem.objects.create(order=order, **item_data)
            # Deduct stock
            prev_stock = product.stock_quantity
            product.stock_quantity -= quantity
            product.save(update_fields=["stock_quantity"])
            StockMovement.objects.create(
                product=product,
                movement_type=StockMovement.MovementType.SALE,
                quantity=-quantity,
                previous_stock=prev_stock,
                new_stock=product.stock_quantity,
                reference=order.order_number,
                created_by=request.user,
            )

        order.calculate_totals()
        return order


class MpesaSTKPushSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    phone_number = serializers.CharField(max_length=15)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id", "product", "product_name", "movement_type",
            "quantity", "previous_stock", "new_stock",
            "reference", "created_by_name", "created_at"
        ]


class StockAdjustmentSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    reason = serializers.CharField(max_length=200)