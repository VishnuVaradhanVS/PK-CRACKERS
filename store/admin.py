from django.contrib import admin
from .models import Product, Order, OrderItem, StorePaymentSettings

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cost", "stock", "is_active", "updated_at")
    list_filter = ("is_active",)
    exclude = ("video_url",)
    search_fields = ("name", "description")
    list_editable = ("cost", "stock", "is_active")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "line_total")
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "contact", "total_amount", "status", "payment_status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("username", "contact", "id")
    list_editable = ("status", "payment_status")
    readonly_fields = ("user", "username", "contact", "address", "total_amount", "created_at")
    inlines = [OrderItemInline]


@admin.register(StorePaymentSettings)
class StorePaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "updated_at")

    def has_add_permission(self, request):
        return not StorePaymentSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
