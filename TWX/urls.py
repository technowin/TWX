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
from Dashboard.views import *
from Masters.views import *
from Form.views import *
from Reports.views import *
from MenuManager.views import *
from Workflow.views import *
from BOM.views import *
from MaterialPlan.views import *
from BookMetadata.views import *
# from ChatBot.views import *
urlpatterns = [
    
    # Django Admin, use {% url 'admin:index' %}

    path('admin/', admin.site.urls),
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
    path('mtp/dashboard',MaterialPlanDashboardView.as_view(), name='dashboard'),
    path('mtp/dashboard2/', mtp_dashboard, name='mtp_dashboard'),
    path('mtp/dashboard3/', mtp_dashboar3, name='mtp_dashboard3'),

    path('plans/',MaterialPlanListView.as_view(), name='plan_list'),
    
    # Material Plan CRUD
    path('plans/create/',MaterialPlanCreateView.as_view(), name='plan_create'),
    path('plans/<int:pk>/',MaterialPlanDetailView.as_view(), name='plan_detail'),
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

    # path('get_faq_answer', get_faq_answer, name='get_faq_answer'),


    # chatbot
    # path('chatbot_view/', chatbot_view, name='chatbot_home'),
    # path('chat/', ChatBotView.as_view(), name='chatbot'),


    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)