from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    CategoryViewSet,
    ProductViewSet,
    CustomerViewSet,
    OrderViewSet,
    StockMovementViewSet,
    MpesaSTKPushView,
    MpesaCallbackView,
    MpesaQueryView,
    CashPaymentView,
    DashboardView,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet)
router.register(r"products", ProductViewSet)
router.register(r"customers", CustomerViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"stock-movements", StockMovementViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # Auth
    path("auth/login/", LoginView.as_view(), name="login"),
    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # Payments
    path("payments/cash/", CashPaymentView.as_view(), name="cash-payment"),
    path("payments/mpesa/stk-push/", MpesaSTKPushView.as_view(), name="mpesa-stk-push"),
    path("payments/mpesa/callback/", MpesaCallbackView.as_view(), name="mpesa-callback"),
    path("payments/mpesa/query/<str:checkout_request_id>/", MpesaQueryView.as_view(), name="mpesa-query"),
]