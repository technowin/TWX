"""
URL configuration for TWX project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('',home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.views import defaults as default_views
from django.views.generic import TemplateView 
from Account.views import *
from ChatModal.views import *
from Dashboard.views import *
from Masters.views import *
from Form.views import *
from Reports.views import *
from MenuManager.views import *
from Workflow.views import *
from BOM.views import *
from MaterialPlan.views import *
from BookMetadata.views import *
from PLM.views import *

from Checklist.views import *
from Inventory.views import *
from LMS.views import *
from SalesPurchase.views import *
# from ChatBot.views import *
urlpatterns = [
    
    # Django Admin, use {% url 'admin:index' %}

#     path('admin/', admin.site.urls),
    # User management
    # path("users/", include("bootstrap.users.urls", namespace="users")),
    # Your stuff: custom urls includes go here
    path("apps/", include("bootstrap.apps.urls", namespace="apps")),
    path("apps/crm/", include("bootstrap.crm.urls", namespace="crm")),
    path("apps/ecommerce/", include("bootstrap.ecommerce.urls", namespace="ecommerce")),
    path("pages/", include("bootstrap.pages.urls", namespace="pages")),
    path("ui/", include("bootstrap.ui.urls", namespace="ui")),
    path("extended/", include("bootstrap.extended.urls", namespace="extended")),
    path("icons/", include("bootstrap.icons.urls", namespace="icons")),
    path("charts/", include("bootstrap.charts.urls", namespace="charts")),
    path("forms/", include("bootstrap.form.urls", namespace="form")),
    path("tables/", include("bootstrap.tables.urls", namespace="tables")),
    path("maps/", include("bootstrap.maps.urls", namespace="maps")),
    path("layouts/", include("bootstrap.layouts.urls", namespace="layouts")),
    path("dashboard/", include("bootstrap.dashboard.urls", namespace="dashboard")),
    path("landing", view=TemplateView.as_view(template_name="bootstrap/landing.html"), name="landing"),
    # path("", view=TemplateView.as_view(template_name="bootstrap/landing.html"), name="landing"),

    # OCR File Upload
    path('upload/', upload_document, name='upload_document'),
    path('document_detail1/<int:pk>/', document_detail1, name='document_detail1'),
    path('search/', search_documents, name='document_search'),
    path('document/<int:document_id>/', document_detail, name='document_detail'),
    path('ks/<int:document_id>/', ks, name='ks'),
    path('ocr_files', ocr_files, name='ocr_files'),

    # Dashboard
    path('bom/dashboard',DashboardView.as_view(), name='dashboard'),
    path('bom/dashboard2/', bom_dashboard, name='bom_dashboard'),

    path('inventory/low-stock/', inventory_low_stock, name='inventory_low_stock'),
    path('inventory/report/', inventory_report, name='inventory_report'),
    path('bom/approvals/', bom_approvals, name='bom_approvals'),
    path('bom/approve/<int:approval_id>/', approve_bom, name='approve_bom'),
    path('bom/reject/<int:approval_id>/', reject_bom, name='reject_bom'),

    # BOM Management
    path('boms/',BOMListView.as_view(), name='bom_list'),
    path('boms/new/',BOMCreateView.as_view(), name='bom_create'),
    path('boms/<int:pk>/',BOMDetailView.as_view(), name='bom_detail'),
    path('boms/<int:pk>/edit/',BOMUpdateView.as_view(), name='bom_update'),
    path('boms/<int:pk>/delete/',BOMDeleteView.as_view(), name='bom_delete'),

    path('boms/<int:pk>/compare/',BOMCompareView.as_view(), name='bom_compare'),
    
    # Component Management
    path('components/',ComponentListView.as_view(), name='component_list'),
    path('components/<int:pk>/',ComponentDetailView.as_view(), name='component_detail'),
    
    # AJAX endpoints
    # path('api/add-bom-item/',AddBOMItemView.as_view(), name='add_bom_item'),
    path('api/update-bom-item/',UpdateBOMItemView.as_view(), name='update_bom_item'),
    path('api/remove-bom-item/',RemoveBOMItemView.as_view(), name='remove_bom_item'),
    # path('api/request-approval/',RequestBOMApprovalView.as_view(), name='request_bom_approval'),
    # path('api/approve-bom/',ApproveBOMView.as_view(), name='approve_bom'),
    path('approvals/<int:pk>/approve/',ApproveBOMView.as_view(), name='approve_bom'),
    path('approvals/<int:pk>/reject/',RejectBOMView.as_view(), name='reject_bom'),
    # path('api/add-comment/',AddCommentView.as_view(), name='add_comment'),
    
    # API endpoints
    path('api/components/<int:pk>/',ComponentAPIView.as_view(), name='component_api'),
    path('components/new/',ComponentCreateView.as_view(), name='component_create'),
    path('components/<int:pk>/edit/',ComponentUpdateView.as_view(), name='component_update'),
    path('components/<int:pk>/add-supplier/',AddComponentSupplierView.as_view(), name='add_component_supplier'),
    path("suppliers/<int:pk>/edit/", EditComponentSupplierView.as_view(), name="edit_component_supplier"),
    path('boms/<int:pk>/request-approval/',RequestBOMApprovalView.as_view(), name='request_bom_approval'),

    # path('<int:pk>/',BOMDetailView.as_view(), name='bom_detail'),
    path('item/<int:item_id>/',BOMItemDetailView.as_view(), name='bom_item_detail'),

    path('<int:bom_id>/add-item/',AddBOMItemView.as_view(), name='add_bom_item'),
    path('item/<int:item_id>/edit/',EditBOMItemView.as_view(), name='edit_bom_item'),
    path('item/<int:item_id>/delete/',DeleteBOMItemView.as_view(), name='delete_bom_item'),
    path('<int:bom_id>/add-comment/',AddCommentView1.as_view(), name='add_bom_comment'),
    path('api/add-comment/',AddCommentView.as_view(), name='add_comment'),

    path('<int:bom_id>/create-revision/',CreateRevisionView.as_view(), name='create_revision'),
    # path('<int:bom_id>/export/',ExportBOMView.as_view(), name='export_bom'),
    # path('<int:bom_id>/request-approval/',RequestApprovalView.as_view(), name='request_approval'),
    path('api/items/<int:item_id>/',bom_item_details, name='bom_item_details'),

    # Material Planning

    # Dashboard and list views
    path('mtp/dashboard/',MaterialPlanDashboardView.as_view(), name='dashboard'),
    path('mtp/dashboard2/', mtp_dashboard, name='mtp_dashboard'),
    path('mtp/dashboard3/', mtp_dashboar3, name='mtp_dashboard3'),

    path('plans/',MaterialPlanListView.as_view(), name='plan_list'),
    
    # Material Plan CRUD
    path('plans/create/',MaterialPlanCreateView.as_view(), name='plan_create'),
    path('plans/<int:pk>/',MaterialPlanDetailView.as_view(), name='plan_detail'),
    path('plan_detail/',MaterialPlanDetailViewIndex.as_view(), name='plan_detail_index'),
    path('plans/<int:pk>/update/',MaterialPlanUpdateView.as_view(), name='plan_update'),
    
    # Plan items
    path('items/<int:pk>/update/',MaterialPlanItemUpdateView.as_view(), name='item_update'),
    
    # Purchase Requisitions
    path('plans/<int:plan_id>/items/<int:item_id>/requisition/create/',
         PurchaseRequisitionCreateView.as_view(), name='requisition_create'),
    path('requisitions/<int:pk>/submit/',
         PurchaseRequisitionSubmitView.as_view(), name='requisition_submit'),
    
    # Inventory actions
    path('plans/<int:plan_id>/items/<int:item_id>/reserve/',
         InventoryReservationView.as_view(), name='inventory_reserve'),
    
    # Shortage alerts
    path('alerts/<int:alert_id>/resolve/',
         MaterialShortageResolutionView.as_view(), name='shortage_resolve'),
    path('shortages/', shortage_list, name='shortage_list'),
    path('shortages/<int:pk>/', shortage_detail, name='shortage_detail'),
    # Production Orders
    path('production-orders/create/',ProductionOrderCreateView.as_view(), name='production_order_create'),
    path('production-orders/<int:pk>/',ProductionOrderDetailView.as_view(), name='production_order_detail'),

    # Book Metadata
    path('book_list/', BookListView.as_view(), name='book_list'),
    path('book_create/', BookCreateView.as_view(), name='book_create'),
    path('<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('<int:pk>/edit/', BookUpdateView.as_view(), name='book_update'),
    path('book_upload/', BookUploadView.as_view(), name='book_upload'),
    path("test-vertex-ai/", test_vertex_ai, name="test_vertex_ai"),
    # path("copy_users_mysql_to_mssql/", copy_users_mysql_to_mssql, name="copy_users_mysql_to_mssql"),

    
    # compliance checklist
    # path('compliance-checklist/', compliance_checklist, name='compliance_checklist'),
    # Checklist URLs
    path('checklist_list/', ChecklistListView.as_view(), name='checklist_list'),
    path('checklist_type/<str:checklist_type>/', checklist_documents_view, name='checklist_detail'),
    path('checklist_add/', ChecklistCreateView.as_view(), name='checklist_add'),
    path('<int:pk>/checklist_edit/', ChecklistUpdateView.as_view(), name='checklist_edit'),
    path('<int:pk>/checklist_delete/', ChecklistDeleteView.as_view(), name='checklist_delete'),
    # Document URLs
    path('documents/add/', DocumentCreateView.as_view(), name='document_add'),
    path('documents/<int:pk>/edit/', DocumentUpdateView.as_view(), name='document_edit'),
    path('documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
    path('documents/<int:pk>/download/', download_document, name='document_download'),
    path('download-checklist-template/', download_checklist_template, name='download_checklist_template'),

    # Bulk Upload URLs
    path('bulk-upload-checklist/', bulk_upload_checklist, name='bulk_upload_checklist'),
    path('bulk-upload-documents/', bulk_upload_documents, name='bulk_upload_documents'),
    path('get_observ/', get_observ, name='get_observ'),

    # Inventory and Warehouse Management
    path('inventory_dashboard/', inventory_dashboard, name='inventory-dashboard'),
    # Product Management
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/add/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product-update'),
    
    # Warehouse Management
    path('warehouses/', WarehouseListView.as_view(), name='warehouse-list'),
    path('warehouses/add/', WarehouseCreateView.as_view(), name='warehouse-create'),
    path('warehouses/<int:pk>/', WarehouseDetailView.as_view(), name='warehouse-detail'),
    path('warehouses/<int:pk>/edit/', WarehouseUpdateView.as_view(), name='warehouse-update'),
    
     # Storage Location Management
    path('locations/add/<int:warehouse_pk>/', StorageLocationCreateView.as_view(), name='storage-location-create'),
    path('locations/<int:pk>/', StorageLocationDetailView.as_view(), name='storage-location-detail'),
    path('locations/<int:pk>/edit/', StorageLocationUpdateView.as_view(), name='storage-location-update'),

    # Stock Management
    path('stock/entries/add/', StockEntryCreateView.as_view(), name='stockentry-create'),
    path('stock/movements/add/', StockMovementCreateView.as_view(), name='stockmovement-create'),
    path('stock/movements/<int:pk>/confirm/', StockMovementConfirmView.as_view(), name='stockmovement-confirm'),
    path('stock-movements/', stock_movement_list, name='stock-movement-list'),

    # AJAX Views
    path('ajax/get-locations/', get_locations_for_warehouse, name='get-locations'),
    path('ajax/get-product-details/', get_product_details, name='get-product-details'),

    # Alert Management
    path('alerts/', InventoryAlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/acknowledge/', AcknowledgeAlertView.as_view(), name='acknowledge-alert'),
    
    # Barcode Management
    path('barcodes/', BarcodeListView.as_view(), name='barcode-list'),
    path('barcodes/add/', BarcodeCreateView.as_view(), name='barcode-create'),
    path('barcodes/<int:pk>/set-primary/', SetPrimaryBarcodeView.as_view(), name='set-primary-barcode'),
    
    # AJAX Views
    path('ajax/get-product-variants/', get_product_variants, name='get-product-variants'),

     # Category Management
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/add/', CategoryCreateView.as_view(), name='category-create'),
    path('categories/<slug:slug>/edit/', CategoryUpdateView.as_view(), name='category-update'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),

    # Learning Management System (LMS)
    # Dashboards

    path('user-dashboard/', UserDashboardView.as_view(), name='user_dashboard'),
    path('admin/dashboard1/', AdminDashboardView.as_view(), name='admin_dashboard'),

    # User Management System
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('profile/', profile_view, name='profile'),
    path('logout/', logout_view, name='logout'),

    # Course Management
    path('courses/create/', CourseCreateView.as_view(), name='course_create'),
    path('courses/<slug:slug>/', CourseDetailView.as_view(), name='course_detail'),
    path('courses/', CourseListView.as_view(), name='course_list'),
    path('courses/<slug:slug>/update/', CourseUpdateView.as_view(), name='course_update'),
    path('courses/<slug:slug>/modules/create/', ModuleCreateView.as_view(), name='module_create'),
    path('courses/<slug:slug>/modules/<int:module_id>/lessons/create/',LessonCreateView.as_view(), name='lesson_create'),
    path('courses/<slug:slug>/resources/create/',ResourceCreateView.as_view(), name='resource_create'),

    # Enrollment & Access Control
    path('courses/<slug:slug>/enroll/', enroll_course, name='enroll_course'),
    path('learning/<slug:slug>/', course_learning, name='course_learning'),
    path('learning/<slug:slug>/modules/<int:module_id>/lessons/<int:lesson_id>/',lesson_detail, name='lesson_detail'),
    path('corporate/enrollment-requests/', corporate_enrollment_requests, name='corporate_enrollment_requests'),
    path('corporate/enrollment-requests/<int:request_id>/',process_corporate_request, name='process_corporate_request'),

    # Payment & Subscription
    path('cart/', cart_view, name='cart'),
    path('cart/add/<slug:slug>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<slug:slug>/', remove_from_cart, name='remove_from_cart'),
    path('cart/apply-coupon/', apply_coupon, name='apply_coupon'),
    path('cart/remove-coupon/', remove_coupon, name='remove_coupon'),
    path('checkout/', checkout, name='checkout'),
    path('razorpay/callback/', razorpay_callback, name='razorpay_callback'),
    path('payment/success/<str:order_id>/', payment_success, name='payment_success'),
    path('payment/failed/', payment_failed, name='payment_failed'),

    # Learning Experience
    path('certificate/<int:enrollment_id>/', generate_certificate, name='generate_certificate'),
    path('certificate/verify/<str:certificate_id>/', verify_certificate, name='verify_certificate'),
    
    path('lessons/<int:lesson_id>/notes/add/', add_note, name='add_note'),
    path('lessons/<int:lesson_id>/bookmark/', toggle_bookmark, name='toggle_bookmark'),
    path('bookmarks/<int:bookmark_id>/update/', update_bookmark, name='update_bookmark'),
    path('lessons/<int:lesson_id>/discussion/add/', add_discussion, name='add_discussion'),
    path('discussions/<int:discussion_id>/reply/', reply_discussion, name='reply_discussion'),
    path('discussions/<int:discussion_id>/vote/<str:vote_type>/', vote_discussion, name='vote_discussion'),
    path('discussions/<int:discussion_id>/resolve/', mark_resolved, name='mark_resolved'),
    path('admin/lessons/add/<int:module_id>/', LessonCreateView.as_view(), name='admin_add_lesson'),

    # Admin Interface
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/users/', UserManagementView.as_view(), name='admin_user_management'),
    path('admin/users/<int:user_id>/', user_detail, name='admin_user_detail'),
    path('courses/create/', CourseCreateView.as_view(), name='admin_add_course'),
    path('admin/courses/', CourseManagementView.as_view(), name='admin_course_management'),
    path('admin/courses/edit/<int:pk>/', CourseUpdateView.as_view(), name='admin_edit_course'),
    path('admin/courses/delete/<int:pk>/', CourseDeleteView.as_view(), name='admin_delete_course'),
    path('admin/modules/create/<slug:slug>/', ModuleCreateView.as_view(), name='admin_add_module'),
    path('admin/modules/edit/<int:pk>/', ModuleUpdateView.as_view(), name='admin_edit_module'),
    path('admin/modules/delete/<int:pk>/', ModuleDeleteView.as_view(), name='admin_delete_module'),

    path('admin/enrollments/', enrollment_management, name='admin_enrollment_management'),
    path('admin/enrollments/<int:enrollment_id>/update/', update_enrollment, name='admin_update_enrollment'),
    path('admin/corporate/', corporate_management, name='admin_corporate_management'),
    path('admin/companies/<int:company_id>/', company_detail, name='admin_company_detail'),
    path('admin/corporate/enrollment-requests/', corporate_enrollment_requests, name='admin_corporate_enrollment_requests'),
    path('admin/process_corporate_request/<int:request_id>/',process_corporate_request, name='admin_process_corporate_request'),

    path('admin/reports/', reports, name='admin_reports'),
    path('admin/notifications/', notifications_view, name='admin_notifications'),
    path('admin/notifications/mark-read/', mark_notification_read, name='notifications'),

    path('admin/feedback/<int:enrollment_id>/', submit_feedback, name='admin_submit_feedback'), 
    path('wishlist/add/<slug:slug>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<slug:slug>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/', wishlist_view, name='wishlist'),

    # Sales & Purchase

    # Dashboard
    path('sp_dashboard/', dashboard, name='sp_dashboard'),

    # Dashboard URLs
    path('sales-dashboard/', sales_dashboard, name='sales_dashboard'),
    path('purchase-dashboard/', purchase_dashboard, name='purchase_dashboard'),

    # Customer URLs
    path('customers/', customer_list, name='customer_list'),
    path('customers/create/', customer_create, name='customer_create'),
    path('customers/<int:pk>/edit/', customer_edit, name='customer_edit'),
    path('customers/<int:pk>/', customer_detail, name='customer_detail'),
    
     # Customer Pricing URLs
    path('customers/<int:customer_id>/pricing/', customer_pricing_list, name='customer_pricing_list'),
    path('customers/<int:customer_id>/pricing/create/', customer_pricing_create, name='customer_pricing_create'),
    path('customer-pricing/<int:pk>/edit/', customer_pricing_edit, name='customer_pricing_edit'),

    # RFQ URLs
    path('rfqs/', rfq_list, name='rfq_list'),
    path('rfqs/create/', rfq_create, name='rfq_create'),
    path('rfqs/<int:pk>/edit/', rfq_edit, name='rfq_edit'),
    path('rfqs/<int:pk>/', rfq_detail, name='rfq_detail'),
    path('rfqs/<int:pk>/clone/', rfq_clone, name='rfq_clone'),
    
    # Quotation URLs
    path('quotations/', quotation_list, name='quotation_list'),
    path('quotations/create/', quotation_create, name='quotation_create'),
    path('quotations/create-from-rfq/<int:rfq_id>/', quotation_from_rfq, name='quotation_from_rfq'),
    path('quotations/<int:pk>/edit/', quotation_edit, name='quotation_edit'),
    path('quotations/<int:pk>/', quotation_detail, name='quotation_detail'),
    path('quotations/<int:pk>/pdf/', quotation_pdf, name='quotation_pdf'),
    path('calculate-price/', calculate_price, name='calculate_price'),

    # BOM URLs
    path('bom/<int:bom_id>/clone/', bom_clone, name='bom_clone'),
    path('bom/<int:bom_id>/calculate-cost/', calculate_bom_cost_ajax, name='calculate_bom_cost_ajax'),

    # Quotation with Variant BOM
    path('rfqs/<int:rfq_id>/quotation-with-variant-bom/', quotation_with_variant_bom, name='quotation_with_variant_bom'),
    path('api/bom/<int:bom_id>/details/', bom_details_api, name='bom_details_api'),
    # Sales Order URLs
    path('sales-orders/', sales_order_list, name='sales_order_list'),
    path('sales-orders/create/', sales_order_create, name='sales_order_create'),
    path('sales-orders/create-from-quotation/<int:quotation_id>/', sales_order_from_quotation, name='sales_order_from_quotation'),
    path('sales-orders/<int:pk>/edit/', sales_order_edit, name='sales_order_edit'),
    path('sales-orders/<int:pk>/', sales_order_detail, name='sales_order_detail'),
    
    # Invoice URLs
    path('invoices/', invoice_list, name='invoice_list'),
    path('invoices/create/', invoice_create, name='invoice_create'),
    path('invoices/create-from-sales-order/<int:order_id>/', invoice_from_sales_order, name='invoice_from_sales_order'),
    path('invoices/<int:pk>/edit/', invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/', invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', invoice_pdf, name='invoice_pdf'),
    
    # Purchase RFQ URLs
    path('purchase-rfqs/', purchase_rfq_list, name='purchase_rfq_list'),
    path('purchase-rfqs/create/', purchase_rfq_create, name='purchase_rfq_create'),
    path('purchase-rfqs/create-from-requisition/<int:requisition_id>/', purchase_rfq_from_requisition, name='purchase_rfq_from_requisition'),
    path('purchase-rfqs/<int:pk>/edit/', purchase_rfq_edit, name='purchase_rfq_edit'),
    path('purchase-rfqs/<int:pk>/', purchase_rfq_detail, name='purchase_rfq_detail'),
    path('purchase-rfqs/<int:pk>/send/', purchase_rfq_send, name='purchase_rfq_send'),
     
    # Supplier Comparison URL
    path('purchase-rfqs/<int:rfq_id>/comparison/', supplier_comparison, name='supplier_comparison'),

    # Purchase Quotation URLs
    path('purchase-quotations/', purchase_quotation_list, name='purchase_quotation_list'),
    path('purchase-quotations/create/', purchase_quotation_create, name='purchase_quotation_create'),
    path('purchase-quotations/create-from-rfq/<int:rfq_id>/', purchase_quotation_from_rfq, name='purchase_quotation_from_rfq'),
    path('purchase-quotations/<int:pk>/edit/', purchase_quotation_edit, name='purchase_quotation_edit'),
    path('purchase-quotations/<int:pk>/', purchase_quotation_detail, name='purchase_quotation_detail'),
    path('purchase-quotations/<int:pk>/pdf/', purchase_quotation_pdf, name='purchase_quotation_pdf'),
    path('purchase-quotations/<int:pk>/status/<str:status>/', update_quotation_status, name='update_purchase_quotation_status'),

    # Purchase Order URLs
    path('purchase-orders/', purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/create-from-rfq/<int:rfq_id>/', purchase_order_from_rfq, name='purchase_order_from_rfq'),
    path('purchase-orders/<int:pk>/edit/', purchase_order_edit, name='purchase_order_edit'),
    path('purchase-orders/<int:pk>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/pdf/', purchase_order_pdf, name='purchase_order_pdf'),
    
    # Vertex AI Invoice
    path('invoice_list_vai/', InvoiceListView.as_view(), name='invoice_list_vai'),
    path('invoice_upload_vai/', InvoiceUploadView.as_view(), name='invoice_upload_vai'),
    path('invoice_detail_vai<int:pk>/', InvoiceDetailView.as_view(), name='invoice_detail_vai'),
    path('<int:pk>/update_invoice_status_vai/', update_invoice_status, name='update_invoice_status_vai'),

    # GRN URLs
    path('grns/', grn_list, name='grn_list'),
    path('grns/create/', grn_create, name='grn_create'),
    path('grns/create-from-po/<int:po_id>/', grn_from_po, name='grn_from_po'),
    path('grns/<int:pk>/edit/', grn_edit, name='grn_edit'),
    path('grns/<int:pk>/', grn_detail, name='grn_detail'),
    path('grns/<int:pk>/verify/', grn_verify, name='grn_verify'),
    
    # Supplier Invoice URLs
    path('supplier-invoices/', supplier_invoice_list, name='supplier_invoice_list'),
    path('supplier-invoices/create/', supplier_invoice_create, name='supplier_invoice_create'),
    path('supplier-invoices/create-from-grn/<int:grn_id>/', supplier_invoice_from_grn, name='supplier_invoice_from_grn'),
    path('supplier-invoices/<int:pk>/edit/', supplier_invoice_edit, name='supplier_invoice_edit'),
    path('supplier-invoices/<int:pk>/', supplier_invoice_detail, name='supplier_invoice_detail'),
    
    # AJAX URLs
    path('ajax/get-customer-details/<int:customer_id>/', get_customer_details, name='get_customer_details'),
    path('ajax/component/<int:component_id>/', get_component_details, name='get_component_details'),
    path('ajax/bom/<int:bom_id>/', get_bom_details, name='get_bom_details'),
    path('ajax/customer-pricing/<int:customer_id>/<int:component_id>/', get_customer_pricing, name='get_customer_pricing'),
    path('ajax/calculate-bom-cost/<int:bom_id>/', calculate_bom_cost, name='calculate_bom_cost'),

     # File upload URLs
    path('sales-orders/<int:order_id>/upload-po/', upload_customer_po, name='upload_customer_po'),
    path('supplier-invoices/<int:invoice_id>/upload-invoice/', upload_supplier_invoice, name='upload_supplier_invoice'),
    
    # Payment URLs
    path('invoices/<int:invoice_id>/mark-paid/', mark_invoice_paid, name='mark_invoice_paid'),
    path('supplier-invoices/<int:invoice_id>/mark-paid/', mark_supplier_invoice_paid, name='mark_supplier_invoice_paid'),

    # Form 
    path('form_builder/', form_builder, name='form_builder'),
    path('form_action_builder/', form_action_builder, name='form_action_builder'),  
    path('form_action_builder_master/', form_action_builder_master, name='form_action_builder_master'),  # Render HTML
    path('save_form/', save_form, name='save_form'), 
    path('save_form_action/', save_form_action, name='save_form_action'), 
    path('update-action-form/<int:form_id>/',update_action_form, name='update_action_form'),
    path('form_master/',form_master, name='form_master'),
    path('common_form_post/',common_form_post, name='common_form_post'),
    path('common_form_edit/',common_form_edit, name='common_form_edit'),
    path('common_form_action/',common_form_action, name='common_form_action'),
    path('update_form/<int:form_id>/', update_form, name='update_form'),
    path('form_preview/',form_preview, name='form_preview'),
    path('get_uploaded_files/',get_uploaded_files, name='get_uploaded_files'),
    path('get_dublicate_name',get_dublicate_name, name='get_dublicate_name'),
    path('download_file/',download_file, name='download_file'),
    path('delete-file/', delete_file, name='delete_file'),
    path('get_query_data/', get_query_data, name='get_query_data'),
    path('check_field_before_delete/', check_field_before_delete, name='check_field_before_delete'),
    path('get_field_names/', get_field_names, name='get_field_names'),
    path('get_regex_pattern/', get_regex_pattern, name='get_regex_pattern'),
    path('create_new_section/', create_new_section, name='create_new_section'),
    path('reference_workflow/', reference_workflow, name='reference_workflow'),
    path('get_compare_data/<int:final_id>/', get_compare_data, name='get_compare_data'),
    path("preview_file",preview_file, name="preview_file"),
    path("check_file_status",check_file_status, name="check_file_status"),
    


    # Account
    path("", Login,name='Account'),
    path("Login", Login,name='Account'),
    path("Login", Login,name='Login'),
    path("home", home,name='home'),
    path("logout",logoutView,name='logout'),
    path("forgot_password",forgot_password,name='forgot_password'),
    path('search/', search, name='search'),
    path("register_new_user",register_new_user, name="register_new_user"),
    path("reset_password",reset_password, name="reset_password"),
    path("change_password",change_password, name="change_password"),
    path("forget_password_change",forget_password_change, name="forget_password_change"),

    # Workflow
    path('index/', index, name='index'),
    path('partial_table', partial_table, name='partial_table'),
    path('download_xls', download_xls, name='download_xls'),
    path('work_flow', work_flow, name='work_flow'),
    path('download_doc/<str:filepath>/', download_doc, name='download_doc'), 

    # Masters
    path('masters/', masters, name='masters'),

    path("update_form/", update_form, name="update_form"),

    #Reports 
    path('common_html', common_html, name='common_html'),
    path('get_filter', get_filter, name='get_filter'),
    path('get_sub_filter', get_sub_filter, name='get_sub_filter'),
    path('add_new_filter', add_new_filter, name='add_new_filter'),
    path('partial_report', partial_report, name='partial_report'),
    path('report_pdf', report_pdf, name='report_pdf'),
    path('report_xlsx', report_xlsx, name='report_xlsx'),
    path('save_filters', save_filters, name='save_filters'),
    path('delete_filters', delete_filters, name='delete_filters'),
    path('saved_filters', saved_filters, name='saved_filters'),
    path('download/<str:file_id>/', dl_file, name='dl_file'),

    # Menu Management
    path("menu_admin",menu_admin, name="menu_admin"),
    path("menu_master",menu_master, name="menu_master"),
    path("assign_menu",assign_menu, name="assign_menu"),
    path("get_assigned_values",get_assigned_values, name="get_assigned_values"),
    path("menu_order",menu_order, name="menu_order"),
    path("delete_menu",delete_menu, name="delete_menu"),
    
    # Bootstarp Pages
    path("dashboard",dashboard,name='dashboard'),
    path("buttons",buttons,name='buttons'),
    path("cards",cards,name='cards'),
    path("utilities_color",utilities_color,name='utilities_color'),
    path("utilities_border",utilities_border,name='utilities_border'),
    path("utilities_animation",utilities_animation,name='utilities_animation'),
    path("utilities_other",utilities_other,name='utilities_other'),
    path("error_page",error_page,name='error_page'),
    path("blank",blank,name='blank'),
    path("charts",charts,name='charts'),  
    path("tables",tables,name='tables'),

# Workflow mapping
    path('workflow_mapping/', workflow_mapping, name='workflow_mapping'),
    path('get_actions_by_button_type/', get_actions_by_button_type, name='get_actions_by_button_type'),
    path('submit_workflow/', submit_workflow, name='submit_workflow'),
    path('workflow_Editmap/', workflow_Editmap, name='workflow_Editmap'),
    path('workflow_starts/', workflow_starts, name='workflow_starts'),
    path('workflow_form_step/', workflow_form_step, name='workflow_form_step'),
    path('workflowcommon_form_post/', workflowcommon_form_post, name='workflowcommon_form_post'),
    path('get_formdataid/', get_formdataid, name='get_formdataid'),
    path('get_formdataidEdit/', get_formdataidEdit, name='get_formdataidEdit'),
    path('reject_workflow_step/', reject_workflow_step, name='reject_workflow_step'),
    path('redirect_to_workflow_start/', redirect_to_workflow_start, name='redirect_to_workflow_start'),
    path('get_versiondata/', get_versiondata, name='get_versiondata'),
    path('check_fileNameExistsInVersion/', check_fileNameExistsInVersion, name='check_fileNameExistsInVersion'),
    path('view_access/', view_access, name='view_access'),
    path('common_form_post_master/', common_form_post_master, name='common_form_post_master'),
    path('workflow_module/', workflow_module, name='workflow_module'),


    # MachinePlan
    path('mcp/', include('MachinePlan.urls', namespace='mcp')),
    path('manpower/', include('Manpower.urls', namespace='manpower')),
    path('convert-input/', convert_input_view, name='convert_input'),

    # path('get_faq_answer', get_faq_answer, name='get_faq_answer'),


    # chatbot
    # path('chatbot_view/', chatbot_view, name='chatbot_home'),
    # path('chat/', ChatBotView.as_view(), name='chatbot'),

    path('chat/', ChatBotView.as_view(), name='chatbot'),
    path('sessions/', chat_session_list, name='chat_session_list'),
    path('sessions/<str:reqno>/',chat_session_detail, name='chat_session_detail'),
    path('chat_log_search/', chat_log_search, name='chat_log_search'),
    path('plan/<int:pk>/confirm/', confirm_plan, name='plan_confirm'),


    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),




    #   path('dashboard/', powerbi_dashboard_view, name='dashboard'),
    path('insights', include('Dashboard.urls')),  # include app URL


    # inventory and and stock

    path('inventory/dashboard/', InventoryDashboardView.as_view(), name='inventory_dashboard'),
    
    # Stock transactions
    path('inventory/transactions/', StockTransactionListView.as_view(), name='stock_transaction_list'),
    path('inventory/transactions/add/', StockTransactionCreateView.as_view(), name='stock_transaction_add'),
    
    # Stock takes
    path('inventory/stocktakes/', StockTakeListView.as_view(), name='stocktake_list'),
    path('inventory/stocktakes/add/', StockTakeCreateView.as_view(), name='stocktake_add'),
    path('inventory/stocktakes/<int:pk>/', StockTakeDetailView.as_view(), name='stocktake_detail'),
    path('inventory/stocktakes/<int:pk>/edit/', StockTakeUpdateView.as_view(), name='stocktake_edit'),
    path('inventory/stocktakes/<int:pk>/complete/', StockTakeCompleteView.as_view(), name='stocktake_complete'),
    path('inventory/stocktakes/<int:pk>/update-item/', StockTakeItemUpdateView.as_view(), name='stocktake_update_item'),
    
    # Reorder rules
    path('inventory/reorder-rules/', ReorderRuleListView.as_view(), name='reorder_rule_list'),
    path('inventory/reorder-rules/add/', ReorderRuleCreateView.as_view(), name='reorder_rule_add'),
    path('inventory/reorder-rules/<int:pk>/edit/', ReorderRuleUpdateView.as_view(), name='reorder_rule_edit'),
    
    # BOM inventory integration
    path('bom/<int:pk>/inventory-check/', BOMInventoryCheckView.as_view(), name='bom_inventory_check'),
    path('bom/<int:pk>/allocate-inventory/', BOMInventoryAllocateView.as_view(), name='bom_allocate_inventory'),
    path('get-bom/', get_bom_for_production_order, name='get_bom'),
    path("get-suppliers/<int:component_id>/", get_suppliers_by_component, name="get_suppliers_by_component"),

    path("components/<int:pk>/component_upload_document/", component_upload_document, name="component_upload_document"),

    path("get_bom_item", get_bom_item, name="get_bom_item"),

    path("plm_index/", plm_index, name="plm_index"),

    path("update_inventory/", update_inventory, name="update_inventory"),

    path("generate_invoice/", generate_invoice, name="generate_invoice"),




]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)