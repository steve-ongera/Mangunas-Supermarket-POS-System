from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Customer, Order, OrderItem, Payment, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "product_count", "created_at"]
    search_fields = ["name"]

    def product_count(self, obj):
        return obj.products.filter(is_active=True).count()
    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "barcode", "category", "price", "stock_quantity", "stock_status", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "barcode"]
    list_editable = ["price", "is_active"]

    def stock_status(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color:red;font-weight:bold;">Low Stock ({})</span>', obj.stock_quantity)
        return format_html('<span style="color:green;">{}</span>', obj.stock_quantity)
    stock_status.short_description = "Stock"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "loyalty_points", "created_at"]
    search_fields = ["name", "phone", "email"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["total_price"]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "customer", "cashier", "status", "total_amount", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["order_number", "customer__name"]
    readonly_fields = ["order_number", "subtotal", "tax_amount", "total_amount"]
    inlines = [OrderItemInline, PaymentInline]
    date_hierarchy = "created_at"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "method", "amount", "status", "mpesa_receipt_number", "created_at"]
    list_filter = ["method", "status"]
    search_fields = ["order__order_number", "mpesa_receipt_number", "mpesa_phone"]
    readonly_fields = ["mpesa_checkout_request_id", "mpesa_merchant_request_id"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["product", "movement_type", "quantity", "previous_stock", "new_stock", "reference", "created_at"]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["product__name", "reference"]
    readonly_fields = ["product", "movement_type", "quantity", "previous_stock", "new_stock", "reference", "created_by", "created_at"]

    def has_add_permission(self, request):
        return False  # Movements are created programmatically


# Customize admin site
admin.site.site_header = "Mangunas Supermarket POS"
admin.site.site_title = "Mangunas POS"
admin.site.index_title = "POS Administration"