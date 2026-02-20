import requests
import base64
import json
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count
from django.contrib.auth.models import User

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category, Product, Customer, Order, OrderItem, Payment, StockMovement
from .serializers import (
    CategorySerializer, ProductSerializer, CustomerSerializer,
    OrderSerializer, OrderCreateSerializer, PaymentSerializer,
    MpesaSTKPushSerializer, StockMovementSerializer, StockAdjustmentSerializer,
    UserSerializer
)


# ─── Auth ──────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# ─── Category ──────────────────────────────────────────────────────────────────

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


# ─── Product ───────────────────────────────────────────────────────────────────

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        barcode = self.request.query_params.get("barcode")
        low_stock = self.request.query_params.get("low_stock")

        if search:
            qs = qs.filter(name__icontains=search)
        if category:
            qs = qs.filter(category_id=category)
        if barcode:
            qs = qs.filter(barcode=barcode)
        if low_stock == "true":
            from django.db.models import F
            qs = qs.filter(stock_quantity__lte=F("low_stock_threshold"))
        return qs

    @action(detail=False, methods=["post"])
    def adjust_stock(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            product = Product.objects.get(id=data["product_id"])
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

        prev = product.stock_quantity
        product.stock_quantity += data["quantity"]
        product.save(update_fields=["stock_quantity"])

        StockMovement.objects.create(
            product=product,
            movement_type=StockMovement.MovementType.ADJUSTMENT if data["quantity"] != 0 else StockMovement.MovementType.RESTOCK,
            quantity=data["quantity"],
            previous_stock=prev,
            new_stock=product.stock_quantity,
            reference=data["reason"],
            created_by=request.user,
        )
        return Response(ProductSerializer(product).data)


# ─── Customer ──────────────────────────────────────────────────────────────────

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        phone = self.request.query_params.get("phone")
        if search:
            qs = qs.filter(name__icontains=search)
        if phone:
            qs = qs.filter(phone=phone)
        return qs


# ─── Order ─────────────────────────────────────────────────────────────────────

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("customer", "cashier").prefetch_related("items", "payments")
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == Order.StatusChoices.COMPLETED:
            return Response({"error": "Cannot cancel a completed order"}, status=400)
        order.status = Order.StatusChoices.CANCELLED
        order.save()
        # Restore stock
        for item in order.items.all():
            prev = item.product.stock_quantity
            item.product.stock_quantity += item.quantity
            item.product.save(update_fields=["stock_quantity"])
            StockMovement.objects.create(
                product=item.product,
                movement_type=StockMovement.MovementType.RETURN,
                quantity=item.quantity,
                previous_stock=prev,
                new_stock=item.product.stock_quantity,
                reference=order.order_number,
                created_by=request.user,
            )
        return Response(OrderSerializer(order).data)


# ─── M-Pesa ────────────────────────────────────────────────────────────────────

def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    if not settings.MPESA_ENVIRONMENT == "sandbox":
        url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    response = requests.get(url, headers={"Authorization": f"Basic {encoded}"})
    return response.json().get("access_token")


def generate_password(shortcode, passkey, timestamp):
    data = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(data.encode()).decode()


class MpesaSTKPushView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MpesaSTKPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order = Order.objects.get(id=data["order_id"])
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        phone = str(data["phone_number"]).strip()
        # Normalize: 07xx -> 2547xx
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif phone.startswith("+"):
            phone = phone[1:]

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        shortcode = settings.MPESA_SHORTCODE
        passkey = settings.MPESA_PASSKEY
        password = generate_password(shortcode, passkey, timestamp)

        amount = int(data["amount"])
        callback_url = settings.MPESA_CALLBACK_URL

        base_url = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENVIRONMENT == "sandbox" else "https://api.safaricom.co.ke"

        try:
            access_token = get_mpesa_access_token()
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": phone,
                "PartyB": shortcode,
                "PhoneNumber": phone,
                "CallBackURL": callback_url,
                "AccountReference": order.order_number,
                "TransactionDesc": f"Payment for {order.order_number}",
            }
            response = requests.post(
                f"{base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            res_data = response.json()

            if res_data.get("ResponseCode") == "0":
                payment = Payment.objects.create(
                    order=order,
                    method=Payment.MethodChoices.MPESA,
                    amount=data["amount"],
                    status=Payment.StatusChoices.PENDING,
                    mpesa_phone=phone,
                    mpesa_checkout_request_id=res_data.get("CheckoutRequestID"),
                    mpesa_merchant_request_id=res_data.get("MerchantRequestID"),
                )
                return Response({
                    "message": "STK push sent successfully",
                    "checkout_request_id": res_data.get("CheckoutRequestID"),
                    "payment_id": payment.id,
                })
            else:
                return Response({"error": res_data.get("errorMessage", "STK push failed")}, status=400)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class MpesaCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        try:
            result = data["Body"]["stkCallback"]
            result_code = result["ResultCode"]
            checkout_request_id = result["CheckoutRequestID"]

            payment = Payment.objects.get(mpesa_checkout_request_id=checkout_request_id)

            if result_code == 0:
                metadata = {item["Name"]: item["Value"] for item in result["CallbackMetadata"]["Item"]}
                payment.status = Payment.StatusChoices.COMPLETED
                payment.mpesa_receipt_number = metadata.get("MpesaReceiptNumber")
                payment.mpesa_transaction_date = timezone.now()
                payment.save()

                # Mark order complete if fully paid
                order = payment.order
                total_paid = order.payments.filter(
                    status=Payment.StatusChoices.COMPLETED
                ).aggregate(Sum("amount"))["amount__sum"] or 0
                if total_paid >= order.total_amount:
                    order.status = Order.StatusChoices.COMPLETED
                    order.save()
            else:
                payment.status = Payment.StatusChoices.FAILED
                payment.save()

        except Exception:
            pass

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaQueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, checkout_request_id):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        shortcode = settings.MPESA_SHORTCODE
        password = generate_password(shortcode, settings.MPESA_PASSKEY, timestamp)
        base_url = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENVIRONMENT == "sandbox" else "https://api.safaricom.co.ke"

        try:
            access_token = get_mpesa_access_token()
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id,
            }
            response = requests.post(
                f"{base_url}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return Response(response.json())
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# ─── Cash Payment ──────────────────────────────────────────────────────────────

class CashPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        cash_tendered = Decimal(str(request.data.get("cash_tendered", 0)))

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        change = cash_tendered - order.total_amount
        payment = Payment.objects.create(
            order=order,
            method=Payment.MethodChoices.CASH,
            amount=order.total_amount,
            status=Payment.StatusChoices.COMPLETED,
            cash_tendered=cash_tendered,
            change_given=max(change, Decimal("0")),
        )
        order.status = Order.StatusChoices.COMPLETED
        order.save()

        return Response({
            "payment": PaymentSerializer(payment).data,
            "change": float(max(change, Decimal("0"))),
            "order": OrderSerializer(order).data,
        })


# ─── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        today_orders = Order.objects.filter(created_at__date=today, status=Order.StatusChoices.COMPLETED)
        today_sales = today_orders.aggregate(total=Sum("total_amount"))["total"] or 0
        today_count = today_orders.count()

        low_stock = Product.objects.filter(is_active=True).extra(
            where=["stock_quantity <= low_stock_threshold"]
        ).count()

        recent_orders = Order.objects.select_related("customer", "cashier").order_by("-created_at")[:10]

        return Response({
            "today_sales": float(today_sales),
            "today_orders": today_count,
            "low_stock_count": low_stock,
            "total_products": Product.objects.filter(is_active=True).count(),
            "recent_orders": OrderSerializer(recent_orders, many=True).data,
        })


# ─── Stock Movements ───────────────────────────────────────────────────────────

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("product", "created_by").order_by("-created_at")
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs