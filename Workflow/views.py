from django.shortcuts import render
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render,redirect
from Account import apps
from Account.models import *
from Form.views import common_module_master
from Masters.models import *
from Workflow.models import *
from Form.models import *
import traceback
from Account.db_utils import callproc

from django.apps import apps


from django.contrib import messages
from django.conf import settings
from TWX.encryption import *
import os
from TWX.settings import *
from django.contrib.auth.decorators import login_required
import openpyxl
import mimetypes
from openpyxl.styles import Font, Border, Side
import pandas as pd
import calendar
from django.utils import timezone
from datetime import timedelta
# Create your views here.
from django.template.loader import render_to_string
import time
import xlsxwriter
import io
import Db

from django.db.models import Q, Count
from Form.models import *
from django.urls import reverse
from django.utils.timezone import now

@login_required 
def index(request):
    pre_url = request.META.get('HTTP_REFERER')
    header, data = [], []
    name,def_dt = '',''
    try:
        if request.user.is_authenticated ==True:                
                global user,role_id
                user = request.user.id    
                role_id = request.user.role_id
        if request.method == "GET":
            disp_type = callproc("stp_get_dropdown_values",['disp_type'])
            dp = callproc("stp_get_dropdown_values",['dept'])
            su = callproc("stp_get_dropdown_values",['send_user'])
            bh = callproc("stp_get_dropdown_values",['branch'])
            sh = callproc("stp_get_dropdown_values",['stakeholder'])
            datalist1= callproc("stp_get_masters",['wf','','name',user])
            name = datalist1[0][0]
            if role_id == 2 :def_dt = 'Inward'
            elif role_id == 3 :def_dt = 'Outward'
            
            dt = dec(dt) if (dt := request.GET.get('dt', '')) else def_dt
            header = callproc("stp_get_masters", ['wf',dt,'header',user])
            rows = callproc("stp_get_masters",['wf',dt,'data',user])
            for row in rows:
                id = enc(str(row[0]))
                data.append((id,) + row[1:])
        context = {'role_id':role_id,'name':name,'header':header,'data':data,'user_id':request.user.id,'dt':disp_type,'su':su,'dp':dp,'bh':bh,'sh':sh,'def_dt':def_dt}
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name
        callproc("stp_error_log",[fun,str(e),user])  
        messages.error(request, 'Oops...! Something went wrong!')
    finally: 
         return render(request,'Workflow/index.html', context)
    
@login_required
def partial_table(request):
    data = []
    try:
        if request.user.is_authenticated ==True:                
            global user
            user = request.user.id    
            role_id = request.user.role_id
            if request.method == "GET":
                dt = request.GET.get('dt', '')
                if(dt!=''):
                    ca = request.GET.get('ca', '')
                    dp = request.GET.get('dp', '')
                    su = request.GET.get('su', '')
                    bh = request.GET.get('bh', '')
                    sh = request.GET.get('sh', '')
                    header = callproc("stp_get_masters", ['wf',dt,'header',user])
                    rows = callproc("stp_get_workflow",[dt,dp,su,bh,sh,ca,user,'data'])
                    for row in rows:
                        id = enc(str(row[0]))
                        data.append((id,) + row[1:])
                context = {'header':header,'data':data}
                html = render_to_string('Workflow/_partial_table.html', context)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name
        callproc("stp_error_log",[fun,str(e),request.user.id])  
        messages.error(request, 'Oops...! Something went wrong!')
    finally:
        data = {'html': html}
        return JsonResponse(data, safe=False)
    
@login_required    
def work_flow(request):
    data = []
    context,wf_id,dispatch_no1  = '','',''
    try:
        if request.user.is_authenticated ==True:                
            global user,role_id
            user = request.user.id   
            role_id = request.user.role_id   
        if request.method == "GET":
            dt = callproc("stp_get_dropdown_values",['disp_type'])
            dp = callproc("stp_get_dropdown_values",['dept'])
            su = callproc("stp_get_dropdown_values",['send_user'])
            bh = callproc("stp_get_dropdown_values",['branch'])
            sh = callproc("stp_get_dropdown_values",['stakeholder'])
            if role_id == 2 :def_dt = 'Inward'
            elif role_id == 3 :def_dt = 'Outward'
            wf_id = dec(wf_id) if (wf_id := request.GET.get('wf', '')) else ''
            if wf_id: wf,enc_wfid = workflow.objects.get(id=wf_id),enc(wf_id)
            else: wf,enc_wfid='',''
            if wf :def_dt = wf.dispatch_type
            if wf :dispatch_no1 = wf.dispatch_no
            header = callproc("stp_get_masters", ['wd','','header',dispatch_no1])
            rows = callproc("stp_get_masters",['wd','','data',dispatch_no1])
            for row in rows:
                if os.path.exists(os.path.join(MEDIA_ROOT, str(row[4]))):
                    encrypted_id = enc(str(row[4]))
                else: encrypted_id = ''
                new_row = row[:4] + (encrypted_id,)
                data.append(new_row)
            context = {'role_id':role_id,'user_id':request.user.id,'header': header,'data': data,'wf_id':enc_wfid,
                       'wf':wf,'dt':dt,'def_dt':def_dt,'su':su,'dp':dp,'bh':bh,'sh':sh}

        if request.method == "POST":
            response = None
            wf_id = dec(wf_id) if (wf_id := request.POST.get('wf_id', '')) else ''
            if wf_id : wf = workflow.objects.get(id=wf_id) 
            else: wf = ''
            
            files = request.FILES.getlist('fileInput')          
            
            if(wf): dispatch_no =  request.POST.get('dispatch_no', '')
            else: dispatch_no = ''
            disp_type =  request.POST.get('disp_type', '')
            received_date =  request.POST.get('received_date', '')
            from_field =  request.POST.get('from', '')
            to =  request.POST.get('to', '')
            subject =  request.POST.get('subject', '')
            comment =  request.POST.get('comment', '')
            department =  request.POST.get('department', '')
            send_user =  request.POST.get('send_user', '')
            branch =  request.POST.get('branch', '')
            stakeholder =  request.POST.get('stakeholder', '')

            r = callproc("stp_post_workflow", [disp_type,dispatch_no,received_date,from_field,to,subject,comment,department,send_user,branch,stakeholder,wf_id,user])
            if r[0][0] == 'update':
                for file in files:
                    response =  docs_upload(file,role_id,user,dispatch_no)
                messages.success(request, "Data Updated Successfully")
            elif r[0][0] != "":
                for file in files:
                    response =  docs_upload(file,role_id,user,str(r[0][0]))
                messages.success(request, "Data Added Successfully")
            else: messages.error(request, 'Oops...! Something went wrong!')
            return redirect(f'/index')
                
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name
        callproc("stp_error_log",[fun,str(e),user])  
        messages.error(request, 'Oops...! Something went wrong!')
    finally: 
         if request.method == "GET" :
            return render(request,'Workflow/workflow.html', context)

def download_doc(request, filepath):
    file = dec(filepath)
    file_path = os.path.join(settings.MEDIA_ROOT, file)
    file_name = os.path.basename(file_path)
    try:
        if os.path.exists(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=mime_type)
                response['Content-Disposition'] = f'inline; filename="{file_name}"'
                return response
        else:
            return HttpResponse("File not found", status=404)

    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name
        callproc("stp_error_log", [fun, str(e), ''])  
        return HttpResponse("An error occurred while trying to download the file.", status=500)
    
def docs_upload(file,role_id,user,dispatch_no1):
    file_resp = None
    role = roles.objects.get(id=role_id)
    sub_path = f'{role.role_name}/User_{user}/{dispatch_no1}/{file.name}'
    full_path = os.path.join(MEDIA_ROOT, sub_path)
    folder_path = os.path.dirname(full_path)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    file_exists_in_folder = os.path.exists(full_path)
    file_exists_in_db = workflow_document.objects.filter(file_path=sub_path,dispatch_no=dispatch_no1).exists()
    if file_exists_in_db:
        document = workflow_document.objects.filter(file_path=sub_path,dispatch_no=dispatch_no1).first()
        document.updated_at = datetime.now()
        document.updated_by = str(user)
        document.save()
        with open(full_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        file_resp =  f"Files has been updated."
    else:
        with open(full_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        workflow_document.objects.create(
            dispatch_no=dispatch_no1, file_name=file.name,file_path=sub_path,
            created_at=datetime.now(),created_by=str(user),updated_at=datetime.now(),updated_by=str(user)
        )  
        file_resp =  f"Files has been inserted."
    return file_resp
 
@login_required
def download_xls(request):
    response = ''
    try:
        if request.user.is_authenticated ==True:                
            global user,role_id
            user = request.user.id   
            role_id = request.user.role_id  
            if request.method == "POST":
                dt =str(request.POST.get('disp_typeh', ''))
                ca =str(request.POST.get('created_ath', ''))
                dp =str(request.POST.get('departmenth', ''))
                su =str(request.POST.get('send_userh', ''))
                bh =str(request.POST.get('branchh', ''))
                sh =str(request.POST.get('stakeholderh', ''))
                import array

                header = callproc("stp_get_masters", ['wf',dt,'sample_xlsx',user])
                header = [item[0] for item in header]

                rows = callproc("stp_get_workflow",[dt,dp,su,bh,sh,ca,user,'xls'])
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output)
                worksheet = workbook.add_worksheet(str(dt) + ' Report')

                worksheet.insert_image('A1', 'static/images/technologo1.png', {'x_offset': 50, 'y_offset': 50, 'x_scale': 0.5, 'y_scale': 0.5})

                header_format = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 14})
                data_format = workbook.add_format({'border': 1})
                # title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                worksheet.merge_range('A4:{}'.format(chr(65+len(header)-1)+'2'), dt + ' Report', header_format)

                header_format = workbook.add_format({'bold': True, 'bg_color': '#ABCaff', 'font_color': 'black','border': 1})
                for i, column_name in enumerate(header):
                    worksheet.write(6, i, column_name, header_format)

                for row_num, row_data in enumerate(rows, start=7):
                    for col_num, col_data in enumerate(row_data):
                        worksheet.write(row_num, col_num, col_data, data_format)
                        
                workbook.close()
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="' + str(dt) + ' Report' + '.xlsx"'
                output.seek(0)
                response.write(output.read())
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        fun = tb[0].name
        callproc("stp_error_log",[fun,str(e),request.user.id])  
        messages.error(request, 'Oops...! Something went wrong!')
    finally:
        return response

@login_required
def workflow_starts(request):  
    Db.closeConnection()
    m = Db.get_connection()
    cursor = m.cursor()

    if request.user.is_authenticated:
        user = request.user.id    
        role_id = str(request.user.role_id)
    workflowSelect = request.GET.get('workflowSelect')
    workflow_para = "CIDCO File Scanning and DMS Flow"
    param = [workflowSelect]
    
    workflow_value = roles.objects.filter(id=role_id).values_list('workflow_view', flat=True).first()

    reference_workflow_status = request.GET.get("reference_workflow_status")


    cursor.callproc("stp_getdataWorkflowIndex",param)
    WFIndexdata_raw = []
    for result in cursor.stored_results():
        WFIndexdata_raw = result.fetchall()

    latest_steps = {}
    for item in WFIndexdata_raw:
        req_num = item[0]        # request number
        increment_id = item[6]   # increment_id column (adjust index if different)
        if req_num not in latest_steps or increment_id > latest_steps[req_num][6]:
            latest_steps[req_num] = item
    WFIndexdata_raw = list(latest_steps.values())

    # 2. Get ALL steps from matrix (the workflow path)
    cursor.callproc("stp_checkRoleForWorkflow", param)
    workflow_steps = []
    for result in cursor.stored_results():
        raw_steps = result.fetchall()

    for row in raw_steps:
        workflow_steps.append({
            'id': row[0],
            'step_name': row[1],
            'role_ids': [r.strip() for r in row[2].split(',')],
            'form_id': row[3],
            'but_type': row[4],
            'but_act': row[5],
            'status': row[6],
            'color_status': row[8],
            'actual_stepID': row[7],
            'step_id_flow': str(row[7]) if row[7] else None  
            
        })

    WFIndexdata = [] 
    
    step_roles_map = {
        str(step['actual_stepID']): step
        for step in workflow_steps
        if step.get('actual_stepID') is not None
    }

    for item in WFIndexdata_raw:
        step_id_str = str(item[3])
       
        
        # to get edit or create
        req_num = item[0]    
               
        detail = workflow_details.objects.get(req_id=req_num)
        current_EditCrtStep = detail.step_id
        editcrt = current_EditCrtStep + 1
        next_step = current_EditCrtStep + 1
        
        try:
            form_data = history_workflow_details.objects.filter(
                req_id=req_num,
                step_id=1
            ).values_list('form_data_id', flat=True).first()

            if form_data:
                file_number = form_field_values.objects.filter(
                    form_data_id=form_data
                ).order_by('id').values_list('value', flat=True).first()
            else:
                    file_number = None
        except Exception as e:
            file_number = None
        
        try:
            next_matrix_entry = workflow_matrix.objects.get(step_id_flow=next_step,wf_id=workflowSelect)
            forwarded_to_role = next_matrix_entry.role_id  
            
            role_ids = [int(role_id.strip()) for role_id in forwarded_to_role.split(',')]
            role_names = roles.objects.filter(id__in=role_ids).values_list('role_name', flat=True)
            forwarded_to_display = ', '.join(role_names)
        except workflow_matrix.DoesNotExist:
            forwarded_to_display = "N/A"

        formDataId_Status= item[7]
        #revised_Status = VersionControlFileMap.objects.filter(form_data=formDataId_Status)
        revised_Status = WorkflowVersion.objects.filter(req_id=req_num).exclude(version=1)
        #revised_Status = WorkflowVersionControl.objects.filter(form_data_id=formDataId_Status).exclude(temp_version=1)
        rejectedCheckWF=None
        if revised_Status.exists():
            status = f"{item[1]}<br>Revised"
            rejectedCheckWF="rejectedCheck"
        else:
            status = item[1]
        form_data_id= enc(str(item[7]))
        updated_by= item[9]
        updated_at= item[10]
        
        latest_entry = history_workflow_details.objects.filter(
        req_id=req_num
        ).order_by('-id').first()  # latest entry, could be reject or forward

        if latest_entry and latest_entry.sent_back == '1':
            last_rejected_step = latest_entry.step_id
            last_rejected_status = latest_entry.status
            if rejectedCheckWF:
                status = f"{status}-Rejected"
            else:
                status = f"{status}<br>Rejected"
        else:
            last_rejected_step = None
            last_rejected_status = None
            
            
        if step_id_str not in step_roles_map:
            print(f"[DEBUG] step_id_str '{step_id_str}' not found in step_roles_map keys: {list(step_roles_map.keys())}")    
        current_step_info = step_roles_map.get(step_id_str)

        # Init vars
        include_for_current_user = False
        next_step_name = ''
        next_step_id = None
        
        
        if not current_step_info:
            continue

        current_step_flow = int(current_step_info['step_id_flow']) if current_step_info['step_id_flow'].isdigit() else None
        if current_step_flow is None:
            continue
        
        if role_id == '2' and item[8] is not None:
            operator_user_id = item[8]  # item[8] is operator column
            if operator_user_id is None or operator_user_id != user:
                continue  # Skip this row if it's not assigned to the current operator
    
        for step in workflow_steps:
            current_step_flowForActBut = current_step_flow - 1
            step_flow = int(step['step_id_flow']) if step['step_id_flow'].isdigit() else None
            if step_flow is not None and step_flow <= current_step_flow:
                if role_id in step['role_ids']:
                    include_for_current_user = True
                    break
        ActUsenext_step_name = None        
        next_flow_id = current_step_flow + 1
        for step in workflow_steps:
            if step.get('step_id_flow') and step['step_id_flow'].isdigit():
                if int(step['step_id_flow']) == next_flow_id:
                    next_step_name = step['step_name']
                    ActUsenext_step_name = step['step_id_flow']
                    next_step_id = enc(str(step['id']))

                    if role_id in step['role_ids']:
                        include_for_current_user = True  # Show to next step user too
                    
                    break
          
        user_prev_step = None
        for step in workflow_steps:
            if role_id in step['role_ids']:
                user_prev_step = step
                break
        if user_prev_step:    
            matrix_obj = workflow_matrix.objects.get(id=user_prev_step['id']) 
            current_stepId = matrix_obj.step_id_flow
            editORcreate = matrix_obj.button_act_details
            
            

        if last_rejected_step is not None and user_prev_step and user_prev_step.get('id') == last_rejected_step - 1:
            extra_flag = 'edit_again'
        else:
            extra_flag = 'view_only'
        
        # # current_step_actual_id = str(item[3])
        # current_step_actual_id=current_step_info['actual_stepID']
        # user_role_id = str(request.user.role_id)
        # form_increment_id = item[6]  # say 2
        
        # is_current_user_at_this_step = False
        # is_current_user_done = False

        # varfor_row=int(ActUsenext_step_name)-1
        # submitted_by_user = history_workflow_details.objects.filter(
        #     req_id=req_num,
        #     step_id=int(varfor_row),
        #     workflow_id=workflowSelect,
        #     created_by=request.user.id  # or use operator if you store it there
        # ).exists()
        
        actual_step_id = int(current_step_info['actual_stepID']) if current_step_info else 0
        next_stepID_forRejectedStep = actual_step_id + 1
        role_id_value = (
            workflow_matrix.objects
            .filter(step_id_flow=next_stepID_forRejectedStep, wf_id=workflowSelect)
            .values_list('role_id', flat=True)
            .first()
        )
        tocheck_role=role_id
        allowed_roles = [r.strip() for r in role_id_value.split(',')] if role_id_value else []

        is_allowed_to_view = tocheck_role in allowed_roles

        # Pass to template
        # context['is_allowed_to_view'] = is_allowed_to_view
        # context['rejected_step_id'] = next_stepID_forRejectedStep
        
        # here just bring all needing ids for current step
        workflow_detail = workflow_details.objects.get(req_id=req_num)
        current_step_id = workflow_detail.step_id
        wf_id = workflow_detail.workflow_id

        # Calculate next step
        next_step_id = current_step_id + 1

        # Get all matrix rows where wf_id and step_id_flow match
        matching_matrix_entries = workflow_matrix.objects.filter(
            wf_id=wf_id,
            step_id_flow=next_step_id
        )

        # Flag to track role presence
        matching_step = None

        # Loop through matches and check if role is included
        for matrix_row in matching_matrix_entries:
            matrix_roles = [r.strip() for r in matrix_row.role_id.split(',')]
            if role_id in matrix_roles:
                matching_step = matrix_row
                break

        if matching_step:
            # action_button = f'<button class="btn btn-primary">{matching_step.step_name}</button>'
            action_button = True
            action_button_name = matching_step.step_name
        else:
            
            # action_button = f'''
            #     <img src="/static/img/eye-open.png" width="20" height="20"
            #         alt="View"
            #         style="cursor:pointer"
            #         onclick="startStepView('{form_data_id}', '{req_num}', '{current_step_id}', '{workflowSelect}')"
            #     />
            # '''
            action_button = False

        if include_for_current_user:
            user_prev_step_id_val = user_prev_step['id'] if user_prev_step else ''
            WFIndexdata.append({
                "req_num": item[0],
                "status": status,
                "id_wfd": item[2],
                "step_id": item[3],
                "enc_id_wfd": enc(str(item[2])),
                "created_by": item[4],
                "created_at": item[5],
                "increment_id": item[6],
                "operator_email": item[11],
                "step_name": current_step_info['step_name'] if current_step_info else '',
                "form_id": current_step_info['form_id'] if current_step_info else '',
                "but_type": current_step_info['but_type'] if current_step_info else '',
                "but_act": current_step_info['but_act'] if current_step_info else '',
                "color_status": current_step_info['color_status'] if current_step_info else '',
                "idEncrypt": enc(str(current_step_info['id'])) if current_step_info else '',
               "form_data_id":form_data_id,
               "editORcreate":editORcreate,
               "reference_workflow_status":reference_workflow_status,
               "actual_step_id": current_step_info['actual_stepID'] if current_step_info else '',
               "tocheck_role":tocheck_role,"role_id_value":role_id_value,
               "current_stepId":current_stepId,
                "next_step_name": next_step_name if next_step_name else 'No next step',
                # "ActUsenext_step_name":int(ActUsenext_step_name),
                "ActUsenext_step_name": int(ActUsenext_step_name) if ActUsenext_step_name not in [None, ''] else None,
                "next_step_id": next_step_id,
                "increment_idCheck": item[6] + 1,
                # "has_user_submitted": has_user_submitted,
                # "user_prev_step_id": user_prev_step['id'] if user_prev_step else '',
                "user_prev_step_id": enc(str(user_prev_step_id_val)) if user_prev_step_id_val != '' else '',
                 "user_prev_step_Check":user_prev_step_id_val,
                 "updated_at":updated_at,"updated_by":updated_by,
                "user_prev_step_name": user_prev_step['step_name'] if user_prev_step else '',
                "include_for_current_user": include_for_current_user,
                "last_rejected_step": last_rejected_step,'action_button': action_button,"action_button_name": action_button_name if action_button else "",
                "last_rejected_status": last_rejected_status,"file_number":file_number,
                'extra_flag': extra_flag,"next_matrix_role":forwarded_to_display,"workflow_value":workflow_value,
            })
            if last_rejected_step is not None:
                # This is where the backend resets rejection
                last_rejected_step = None
                last_rejected_status = None
            
    first_step = next((step for step in workflow_steps if step.get('step_id_flow') == '1'), None)
    show_top_button = False
    top_button_context = {}

    if first_step:
        if str(role_id) in first_step['role_ids']:
            show_top_button = True
            top_button_context = {
                'step_name': first_step['step_name'],
                'form_id': first_step['form_id'],
                'but_type': first_step['but_type'],
                'but_act': first_step['but_act'],
                'actual_stepIDForFirstStep': first_step['step_id_flow'],
                'id_firstStep': first_step['id'],
                'encid_FS': enc(str(first_step['id']))
        }
        
        
        # Check if any current row is *at* first step
        # for item in WFIndexdata_raw:
        #     current_step_id = str(item[3])
            
        #     if current_step_id == first_step_actual_id and first_step.get('step_id_flow') == '1':
        #         if str(role_id) in first_step['role_ids']:
        #             show_top_button = True
        #             top_button_context = {
        #                 'step_name': first_step['step_name'],
        #                 'form_id': first_step['form_id'],
        #                 'but_type': first_step['but_type'],
        #                 'but_act': first_step['but_act'],
        #                 'id_firstStep': first_step['id'],
        #                 'encid_FS': enc(str(first_step['id']))
        #             }
        #             break    

    # if first_step and role_id in first_step['role_ids']:
    #     show_top_button = True
    #     top_button_context = {
    #         'step_name': first_step['step_name'],
    #         'form_id': first_step['form_id'],
    #         'but_type': first_step['but_type'],
    #         'but_act': first_step['but_act'],
    #         'id_firstStep': first_step['id'],
    #         'encid_FS': enc(str(first_step['id']))
               
    #     }
    if show_top_button == True:
        firstStep = '1'
    else:
        firstStep = '0'
    
    return render(request, "Workflow/workflow_starts.html", {
        "WFIndexdata": WFIndexdata,'show_top_button': show_top_button,'firstStep': firstStep, "reference_workflow_status":reference_workflow_status,
        "workflowSelect":workflowSelect,"workflowSelect_enc":enc(workflowSelect),
    **top_button_context
    })

def get_formdataid(request):
    Db.closeConnection()
    m = Db.get_connection()
    cursor = m.cursor()

    if request.user.is_authenticated:
        user = request.user.id    
        role_id = str(request.user.role_id)
        
    id = request.GET.get("id")
    req_num = request.GET.get("req_num")
    step_id = request.GET.get("step_id")
    form_id = request.GET.get("form_id")
    wf_id = request.GET.get("wf_id")
    readonlyWF = "1"
    param=[req_num,step_id,wf_id]
    cursor.callproc("stp_getFormDataIdForWorkflow", param)
    workflow_steps = []
    for result in cursor.stored_results():
        form_data_id = result.fetchall()[0][0]
    form=enc(str(form_data_id))
    primary_value = get_object_or_404(workflow_details,req_id = req_num).primary_key
    # return redirect('form_master', form=form)
    # url = reverse('form_master') + f'?form={form}'
    url = reverse('form_master') + f'?form={form}&readonlyWF={readonlyWF}&step_id={step_id}&req_num={req_num}&primary_key={primary_value}&form_idWF={form_id}'
    return redirect(url)



def get_formdataidEdit(request):
    Db.closeConnection()
    m = Db.get_connection()
    cursor = m.cursor()

    if request.user.is_authenticated:
        user = request.user.id    
        role_id = str(request.user.role_id)
        
    id = request.GET.get("id")
    req_num = request.GET.get("req_num")
    step_id = request.GET.get("step_id")
    form_id = request.GET.get("form_id")
    wfdetailsID = request.GET.get("wfdetailsID")
    viewStepWF = request.GET.get("editORcreate")
    wfDetailsTable_id = request.GET.get("wf_id")
    button_type_id = None
    if wfdetailsID:
        wfdetailsID=dec(wfdetailsID)
    if step_id:
        step = workflow_matrix.objects.get(step_id_flow=step_id,wf_id=wfdetailsID)
        button_type_id = step.button_type_id
    if id:
        id=dec(id)
    workflow_YN = '1E'
    param=[form_id,req_num,wfdetailsID,step_id]
    cursor.callproc("stp_getFormDataIdForWorkflowEdit", param)
    workflow_steps = []
    for result in cursor.stored_results():
        form_data_id = result.fetchall()[0][0]
    form=enc(str(form_data_id))
    primary_value = get_object_or_404(workflow_details,req_id = req_num).primary_key
    # return redirect('form_master', form=form)
    # url = reverse('form_master') + f'?form={form}'
    url = reverse('form_master') + f'?form={form}&button_type_id={button_type_id}&workflow_YN={workflow_YN}&step_id={step_id}&form_idWF={form_id}&role_id={role_id}&wfdetailsID={wfdetailsID}&viewStepWF={viewStepWF}&req_num={req_num}&primary_key={primary_value}&wfDetailsTable_id={wfDetailsTable_id}'
    return redirect(url)
    
        
# def workflow_form_step(request):
#     Db.closeConnection()
#     m = Db.get_connection()
#     cursor = m.cursor()
    
#     id = request.GET.get("id")
#     # instance = YourModel.objects.get(id=id)
#     # file_number_forFN = instance.file_number_forFN
    
#     wfdetailsid = request.GET.get("wfdetailsID")
#     firstStep = request.GET.get("firstStep")
#     editORcreate = request.GET.get("editORcreate")
#     new_data_id = request.GET.get("new_data_id")
#     reference_type = request.GET.get("reference_type")
#     data_save_status = request.GET.get("data_save_status")
#     wfSelected_id = request.GET.get("wfSelected_id")
#     if not new_data_id:
#         new_data_id = ''
#     if new_data_id:
#         matched_form_data_id = new_data_id
#     id = dec(id) 
#     # if wfdetailsid:
#     #     wfdetailsid = dec(wfdetailsid) 

    
#     if not id:
#         return render(request, "Form/_formfields.html", {"fields": []}) 

#     try:
#         cursor.callproc("stp_getOperatorWorkflow")
#         WFoperator_dropdown = []
#         for result in cursor.stored_results():
#             WFoperator_dropdown = result.fetchall()

#         if not data_save_status :
#             data_save_status == '0'
        
#         if not reference_type:
#             reference_type = '0'

        
#         workflow = get_object_or_404(workflow_matrix, id=id)
#         form_ids = workflow.form_id.split(",")  # Comma-separated form IDs
#         action_id = workflow.button_type_id
#         role_id = workflow.role_id
#         action_detail_id = workflow.button_act_details
#         status_wfM = workflow.status

#         matched_form_data_id = None
#         type = "create"  # Default type

#         # Handling wfdetailsid logic (matched form_data based on file_ref)
#         if wfdetailsid:
#             workflow_detail_id = dec(wfdetailsid)
#             try:
#                 workflow_det = workflow_details.objects.get(id=workflow_detail_id)
#                 form_dataID_forFN = workflow_det.form_data_id
#                 file_num_forFN = workflow_det.file_number

#                 file_no_value = ''
#                 if reference_type != '1':
#                     file_obj = FormFieldValues.objects.filter(
#                         value=file_num_forFN, form_data_id=form_dataID_forFN
#                     ).first()
#                     file_no_value = file_obj.value if file_obj else ''

#                 workflow_data = workflow_details.objects.get(id=workflow_detail_id)
#                 inward_req_id = workflow_data.req_id
#                 inward_form_data_id = workflow_data.form_data_id

#                 if inward_req_id:
#                     inward_workflow = workflow_details.objects.get(req_id=inward_req_id)
#                     new_form_data_id = inward_workflow.form_data_id

#                 if inward_form_data_id and inward_req_id:
#                     form_data = FormData.objects.get(id=inward_form_data_id)

#                     if form_data.file_ref and form_data.file_ref != 'New File':
#                         file_ref_value = form_data.file_ref
#                         try:
#                             field_value_entry = FormFieldValues.objects.get(
#                                 form_id__in=form_ids, value=file_ref_value
#                             )
#                             matched_form_data_id = field_value_entry.form_data.id
#                             type = "reference"
#                         except FormFieldValues.DoesNotExist:
#                             matched_form_data_id = None
#                     else:
#                         type = "create"
#             except workflow_details.DoesNotExist:
#                 pass
#         else:
#             type = "create"


#         forms_data = []

#         action_fields = list(FormActionField.objects.filter(action_id=action_id).values(
#                 "id", "type", "label_name", "button_name", "bg_color", "text_color", 
#                 "button_type", "dropdown_values", "status", "action_id"
#             ))
        
#         for action in action_fields:
#             action["dropdown_values"] = action["dropdown_values"].split(",") if action["dropdown_values"] else []

#         for form_id in form_ids:
#             form_id = form_id.strip()
#             if not form_id:
#                 continue

#             form = get_object_or_404(Form, id=form_id)

#             raw_fields = FormField.objects.filter(form_id=form_id).values(
#                 "id", "label", "field_type", "values", "attributes", "form_id", "form_id__name", "section"
#             ).order_by("order")


#             sectioned_fields = {}

#             for field in raw_fields:
#                 field["values"] = [v.strip() for v in field["values"].split(",")] if field.get("values") else []
#                 field["attributes"] = [a.strip() for a in field["attributes"].split(",")] if field.get("attributes") else []

#                 section_id = field.get("section")
#                 if section_id:
#                     try:
#                         section = SectionMaster.objects.get(id=section_id)
#                         section_name = section.name
#                     except SectionMaster.DoesNotExist:
#                         section_name = ""
#                 else:
#                     section_name = ""

#                 field["section_name"] = section_name

#                 validations = FieldValidation.objects.filter(
#                     field_id=field["id"], form_id=form_id
#                 ).values("value")
#                 field["validations"] = list(validations)

#                 if any("^" in v["value"] for v in field["validations"]):
#                     field["field_type"] = "regex"
#                     pattern_value = field["validations"][0]["value"]
#                     try:
#                         regex_obj = RegexPattern.objects.get(regex_pattern=pattern_value)
#                         field["regex_id"] = regex_obj.id
#                         field["regex_description"] = regex_obj.description
#                     except RegexPattern.DoesNotExist:
#                         field["regex_id"] = None
#                         field["regex_description"] = ""

#                 if field["field_type"] in ["file", "file multiple", "text"]:
#                     file_validation = next((v for v in field["validations"]), None)
#                     field["accept"] = file_validation["value"] if file_validation else ""

#                 if field["field_type"] == "field_dropdown":
#                     split_values = field["values"]
#                     if len(split_values) == 2:
#                         dropdown_form_id, dropdown_field_id = split_values
#                         field_values = FormFieldValues.objects.filter(field_id=dropdown_field_id).values("value").distinct()
#                         field["dropdown_data"] = list(field_values)

#                 if field["field_type"] in ["master dropdown", "multiple"] and field["values"]:
#                     dropdown_id = field["values"][0]
#                     try:
#                         master_data = MasterDropdownData.objects.get(id=dropdown_id)
#                         query = master_data.query
#                         result = callproc("stp_get_query_data", [query])
#                         field["values"] = [{"id": row[0], "name": row[1]} for row in result]
#                     except MasterDropdownData.DoesNotExist:
#                         field["values"] = []

#                 sectioned_fields.setdefault(section_name, []).append(field)

#                 forms_data.append({
#                     "form": form,
#                     "sectioned_fields": sectioned_fields,
#                 })

#         # Process action fields
#         for action in action_fields:
#             action["dropdown_values"] = action["dropdown_values"].split(",") if action["dropdown_values"] else []

#             if action["type"] == "button":
#                 if action["button_type"] == "Submit":
#                     form_action_url = reverse('common_form_post')
#                     break
#                 elif action["button_type"] == "Action":
#                     form_action_url = reverse('common_form_action')
#                     break


#         if wfdetailsid:
#             return render(request, "Form/_formfieldedit.html", {
#                 "forms_data":forms_data,
#                 "sectioned_fields": sectioned_fields,
#                 "form":form,"type":type,
#                 'file_no_value':file_no_value,
#                 "action_fields": action_fields,"reference_type":reference_type,
#                 "form_action_url": form_action_url,"file_ref_value":file_ref_value,"new_form_data_id":new_form_data_id,
#                 "workflow": 1,"WFoperator_dropdown":WFoperator_dropdown,
#                 "role_id":role_id,"action_detail_id":action_detail_id,"form_id":form_id,"inward_req_id":inward_req_id,
#                 "matched_form_data_id":matched_form_data_id,"new_data_id":new_data_id,
#                 "action_id":action_id,"step_id":id,"wfdetailsid":wfdetailsid,"status_wfM":status_wfM,"firstStep":firstStep,"editORcreate":editORcreate,"data_save_status":data_save_status,"wfSelected_id":wfSelected_id,
#             })
#         else:
#             return render(request, "Form/_formfieldedit.html", {
#                 "forms_data":forms_data,
#                 "sectioned_fields": sectioned_fields,
#                 "form":form,
#                 "type":type,
#                 "action_fields": action_fields,
#                 "form_action_url": form_action_url,
#                 "workflow": 1,"WFoperator_dropdown":WFoperator_dropdown,
#                 "role_id":role_id,"action_detail_id":action_detail_id,"form_id":form_id,
#                 "matched_form_data_id":matched_form_data_id,
#                 "action_id":action_id,"step_id":id,"status_wfM":status_wfM,"firstStep":firstStep,"editORcreate":editORcreate,"wfSelected_id":wfSelected_id,
#             })
            

#     except Exception as e:
#         traceback.print_exc()
#         messages.error(request, "Oops...! Something went wrong!")   
#         return render(request, "Form/_formfields.html", {"fields": []})

#     finally:
#         cursor.close()
#         m.commit()
#         m.close()
#         Db.closeConnection()
    # save to yuor workflow_details and call nect step in index

    
def common_module_master(module_id):
    try: # assuming this is the field that links Form to ModuleMaster
        module = get_object_or_404(ModuleMaster, id=module_id)

        return {
            "index_table": module.index_table,  # this should be the model class or its name
            "data_table": module.data_table,
            "file_table": module.file_table,
            "action_table": module.action_table,
        }
    except Exception as e:
        raise Exception(f"Error in retrieving module tables: {str(e)}")

# def workflow_form_step(request):
#     Db.closeConnection()
#     m = Db.get_connection()
#     cursor = m.cursor()

#     id = request.GET.get("id")
#     wfdetailsid = request.GET.get("wfdetailsID")
#     firstStep = request.GET.get("firstStep")
#     editORcreate = request.GET.get("editORcreate")
#     new_data_id = request.GET.get("new_data_id") or ''
#     reference_type = request.GET.get("reference_type") or '0'
#     data_save_status = request.GET.get("data_save_status") or '0'
#     wfSelected_id = request.GET.get("wfSelected_id")

#     id = dec(id)
#     if not id:
#         return render(request, "Form/_formfields.html", {"fields": []})

#     try:
#         # Get Operator Dropdown
#         cursor.callproc("stp_getOperatorWorkflow")
#         WFoperator_dropdown = []
#         for result in cursor.stored_results():
#             WFoperator_dropdown = result.fetchall()

#         workflow = get_object_or_404(workflow_matrix, id=id)
#         form_ids = [fid.strip() for fid in workflow.form_id.split(",") if fid.strip()]
#         action_id = workflow.button_type_id
#         role_id = workflow.role_id
#         action_detail_id = workflow.button_act_details
#         status_wfM = workflow.status
#         actual_step_id = workflow.step_id_flow
#         module = get_object_or_404(workflow_details,id = id).module
#         primary_key = get_object_or_404(workflow_details, id = id).primary_key

#         module_tables = common_module_master(module)
            

#         IndexTable = apps.get_model('Form', module_tables["index_table"])
#         DataTable = apps.get_model('Form', module_tables["data_table"])
#         FileTable = apps.get_model('Form', module_tables["file_table"])

#         action_fields = list(FormActionField.objects.filter(action_id=action_id).values(
#             "id", "type", "label_name", "button_name", "bg_color", "text_color",
#             "button_type", "dropdown_values", "status", "action_id"
#         ))
#         for action in action_fields:
#             action["dropdown_values"] = action["dropdown_values"].split(",") if action["dropdown_values"] else []

#         forms_data = []
#         for form_id in form_ids:
#             form = get_object_or_404(Form, id=form_id)
#             module = form.module
#             raw_fields = FormField.objects.filter(form_id=form_id).values(
#                 "id", "label", "field_type", "values", "attributes", "form_id", "form_id__name", "section","is_primary","foriegn_key_form_id"
#             ).order_by("order")

#             sectioned_fields = {}
#             for field in raw_fields:
#                 field["values"] = [v.strip() for v in field["values"].split(",")] if field.get("values") else []
#                 field["attributes"] = [a.strip() for a in field["attributes"].split(",")] if field.get("attributes") else []

#                 section_id = field.get("section")
#                 section_name = ""
#                 if section_id:
#                     section = SectionMaster.objects.filter(id=section_id).first()
#                     if section:
#                         section_name = section.name

#                 field["section_name"] = section_name

#                 # Field Validations
#                 validations = FieldValidation.objects.filter(field_id=field["id"], form_id=form_id).values("value")
#                 field["validations"] = list(validations)

#                 # Regex Field Type
#                 if any("^" in v["value"] for v in field["validations"]):
#                     field["field_type"] = "regex"
#                     pattern_value = field["validations"][0]["value"]
#                     regex_obj = RegexPattern.objects.filter(regex_pattern=pattern_value).first()
#                     if regex_obj:
#                         field["regex_id"] = regex_obj.id
#                         field["regex_description"] = regex_obj.description
#                     else:
#                         field["regex_id"] = None
#                         field["regex_description"] = ""

#                 # File Accept
#                 if field["field_type"] in ["file", "file multiple", "text"]:
#                     file_validation = next((v for v in field["validations"]), None)
#                     field["accept"] = file_validation["value"] if file_validation else ""

#                 # Field Dropdown
#                 if field["field_type"] == "field_dropdown":
#                     if len(field["values"]) == 2:
#                         dropdown_form_id, dropdown_field_id = field["values"]
#                         field_values = form_field_values.objects.filter(field_id=dropdown_field_id).values("value").distinct()
#                         field["dropdown_data"] = list(field_values)

#                 # Master Dropdown or Multiple
#                 if field["field_type"] in ["master dropdown", "multiple"] and field["values"]:
#                     dropdown_id = field["values"][0]
#                     master_data = MasterDropdownData.objects.filter(id=dropdown_id).first()
#                     if master_data:
#                         query = master_data.query
#                         result = callproc("stp_get_query_data", [query])
#                         field["values"] = [{"id": row[0], "name": row[1]} for row in result]
#                     else:
#                         field["values"] = []

#                 sectioned_fields.setdefault(section_name, []).append(field)

#             forms_data.append({
#                 "form": form,
#                 "sectioned_fields": sectioned_fields,
#             })

#         context = {
#             "forms_data": forms_data,"type": "create","action_fields": action_fields,"workflow": 1, "WFoperator_dropdown": WFoperator_dropdown,
#             "role_id": role_id,"action_detail_id": action_detail_id,"matched_form_data_id": new_data_id,"new_data_id": new_data_id,
#             "action_id": action_id,"step_id": id,"status_wfM": status_wfM, "firstStep": firstStep,"editORcreate": editORcreate,"data_save_status": data_save_status,
#             "form_ids":form_ids, "wfSelected_id": wfSelected_id,"reference_type": reference_type,"module":module,"actual_step_id":actual_step_id,
#         }

#         if wfdetailsid:
#             context["wfdetailsid"] = wfdetailsid

#         return render(request, "Form/_formfieldedit.html", context)

#     except Exception as e:
#         traceback.print_exc()
#         messages.error(request, "Oops...! Something went wrong!")
#         return render(request, "Form/_formfields.html", {"fields": []})

#     finally:
#         cursor.close()
#         m.commit()
#         m.close()
#         Db.closeConnection()


def workflow_form_step(request):
    Db.closeConnection()
    m = Db.get_connection()
    cursor = m.cursor()

    id = request.GET.get("id")
    wfdetailsid = request.GET.get("wfdetailsID")
    firstStep = request.GET.get("firstStep")
    editORcreate = request.GET.get("editORcreate")
    new_data_id = request.GET.get("new_data_id") or ''
    reference_type = request.GET.get("reference_type") or '0'
    data_save_status = request.GET.get("data_save_status") or '0'
    wfSelected_id = request.GET.get("wfSelected_id")
    next_step = request.GET.get("next_step")
    wfDetails_id = request.GET.get("wfDetails_id")

    id = dec(id)
    if not id:
        return render(request, "Form/_formfields.html", {"fields": []})

    try:
        # Get Operator Dropdownwfdetailsid
        cursor.callproc("stp_getOperatorWorkflow")
        WFoperator_dropdown = []
        for result in cursor.stored_results():
            WFoperator_dropdown = result.fetchall()
        if wfDetails_id:
            workflow = get_object_or_404(workflow_matrix, wf_id=wfSelected_id,step_id_flow=next_step)
        else:
            workflow = get_object_or_404(workflow_matrix,wf_id = wfSelected_id,step_id_flow = 1)
        form_ids = [fid.strip() for fid in workflow.form_id.split(",") if fid.strip()]
        action_id = workflow.button_type_id
        role_id = workflow.role_id
        action_detail_id = workflow.button_act_details
        status_wfM = workflow.status
        actual_step_id = workflow.step_id_flow
        
        # Initialize variables that might be used later
        module = get_object_or_404(ModuleMaster,id = wfSelected_id).id
        module_tables = common_module_master(module)
                
        IndexTable = apps.get_model('Form', module_tables["index_table"])
        DataTable = apps.get_model('Form', module_tables["data_table"])
        FileTable = apps.get_model('Form', module_tables["file_table"])
        primary_key = None
        form_data_id = None
        module_tables = None
        
        existing_data = {}
        file_data = {}
        
        if actual_step_id != 1:
            workflow_detail = get_object_or_404(workflow_details, id=dec(wfdetailsid))
            # module = workflow_detail.module
            primary_key = workflow_detail.primary_key

            if primary_key: 
                
                index_record = IndexTable.objects.filter(
                    primary_key=primary_key
                ).first()

                if index_record:
                    # Get all data records for this index
                    data_records = DataTable.objects.filter(
                        form_data_id=index_record.id
                    ).select_related('field')

                    # Organize data by form_id and field_id
                    for record in data_records:
                        if str(record.field.form_id) not in existing_data:
                            existing_data[str(record.field.form_id)] = {}
                        existing_data[str(record.field.form_id)][str(record.field_id)] = record.value

                    # Get file records
                    file_records = FileTable.objects.filter(
                        form_data_id=index_record.id
                    ).select_related('field')

                    for file_record in file_records:
                        if str(file_record.field.form_id) not in file_data:
                            file_data[str(file_record.field.form_id)] = {}
                        file_data[str(file_record.field.form_id)][str(file_record.field_id)] = {
                            'file_name': file_record.file_name,
                            'file_path': file_record.file_path
                        }

                    form_data_id = index_record.id

        action_fields = list(FormActionField.objects.filter(action_id=action_id).values(
            "id", "type", "label_name", "button_name", "bg_color", "text_color",
            "button_type", "dropdown_values", "status", "action_id"
        ))
        for action in action_fields:
            action["dropdown_values"] = action["dropdown_values"].split(",") if action["dropdown_values"] else []

        forms_data = []
        for form_id in form_ids:
            form = get_object_or_404(Form, id=form_id)
            if actual_step_id != 1 and not module:  # If module wasn't set earlier, get it from form
                module = form.module
                
            raw_fields = FormField.objects.filter(form_id=form_id).values(
                "id", "label", "field_type", "values", "attributes", "form_id", "form_id__name", "section","is_primary","foriegn_key_form_id"
            ).order_by("order")

            sectioned_fields = {}
            for field in raw_fields:
                field = dict(field)  # Convert to mutable dict
                field_id_str = str(field["id"])
                form_id_str = str(field["form_id"])

                # Set default values
                field["value"] = ""
                field["saved_value"] = ""
                field["existing_file"] = None

                # Prefill existing data if available
                if existing_data and form_id_str in existing_data and field_id_str in existing_data[form_id_str]:
                    field["value"] = existing_data[form_id_str][field_id_str]
                    field["saved_value"] = existing_data[form_id_str][field_id_str]

                # Handle file data
                if field["field_type"] in ['file', 'file multiple']:
                    if file_data and form_id_str in file_data and field_id_str in file_data[form_id_str]:
                        field["existing_file"] = file_data[form_id_str][field_id_str]
                        field["value"] = file_data[form_id_str][field_id_str]["file_name"]

                # Process field values and attributes
                field["values"] = [v.strip() for v in field["values"].split(",")] if field.get("values") else []
                field["attributes"] = [a.strip() for a in field["attributes"].split(",")] if field.get("attributes") else []

                section_id = field.get("section")
                section_name = ""
                if section_id:
                    section = SectionMaster.objects.filter(id=section_id).first()
                    if section:
                        section_name = section.name

                field["section_name"] = section_name

                # Field Validations
                validations = FieldValidation.objects.filter(field_id=field["id"], form_id=form_id).values("value")
                field["validations"] = list(validations)

                # Regex Field Type
                if any("^" in v["value"] for v in field["validations"]):
                    field["field_type"] = "regex"
                    pattern_value = field["validations"][0]["value"]
                    regex_obj = RegexPattern.objects.filter(regex_pattern=pattern_value).first()
                    if regex_obj:
                        field["regex_id"] = regex_obj.id
                        field["regex_description"] = regex_obj.description
                    else:
                        field["regex_id"] = None
                        field["regex_description"] = ""



                # File Accept
                if field["field_type"] in ["file", "file multiple", "text"]:
                    file_validation = next((v for v in field["validations"]), None)
                    field["accept"] = file_validation["value"] if file_validation else ""

                # Field Dropdown
                if field["field_type"] == "field_dropdown":
                    if len(field["values"]) == 2:
                        dropdown_form_id, dropdown_field_id = field["values"]
                        field_values = DataTable.objects.filter(field_id=dropdown_field_id).values("value").distinct()
                        field_values = form_field_values.objects.filter(field_id=dropdown_field_id).values("value").distinct()

                        field["dropdown_data"] = list(field_values)

                # Master Dropdown or Multiple
                if field["field_type"] in ["master dropdown", "multiple"] and field["values"]:
                    dropdown_id = field["values"][0]
                    master_data = MasterDropdownData.objects.filter(id=dropdown_id).first()
                    if master_data:
                        query = master_data.query
                        result = callproc("stp_get_query_data", [query])
                        field["values"] = [{"id": row[0], "name": row[1]} for row in result]
                    else:
                        field["values"] = []

                if field["field_type"] == "foreign" and index_record:
                    foreign_form_id = field.get("foriegn_key_form_id")
                    if foreign_form_id:
                        try:
                            # Get the foreign index record using the current index_record.id and foreign form_id
                            foreign_index = IndexTable.objects.get(
                                id=index_record.id,
                                form_id=foreign_form_id
                            )
                            field["foreign_data"] = foreign_index.primary_key  # Return the primary_key value
                        except IndexTable.DoesNotExist:
                            field["foreign_data"] = None

                sectioned_fields.setdefault(section_name, []).append(field)

            forms_data.append({
                "form": form,
                "sectioned_fields": sectioned_fields,
                "has_existing_data": form_id_str in existing_data if existing_data else False
            })

        context = {
            "forms_data": forms_data,
            "type": "create",
            "form_data_id":form_data_id,
            "action_fields": action_fields,
            "workflow": 1, 
            "WFoperator_dropdown": WFoperator_dropdown,
            "role_id": role_id,
            "action_detail_id": action_detail_id,
            "matched_form_data_id": new_data_id,
            "new_data_id": new_data_id,
            "action_id": action_id,
            "step_id": id,
            "status_wfM": status_wfM, 
            "firstStep": firstStep,
            "editORcreate": editORcreate,
            "data_save_status": data_save_status,
            "form_ids": form_ids, 
            "wfSelected_id": wfSelected_id,
            "reference_type": reference_type,
            "actual_step_id": actual_step_id,
            "primary_key": primary_key,
            "module": module,"wfDetailsTable_id":wfDetails_id,
        }

        # Only add module to context if it exists
        # if module:
        #     context["module"] = module
            
        if wfdetailsid:
            context["wfdetailsid"] = wfdetailsid

        return render(request, "Form/_formfieldedit.html", context)

    except Exception as e:
        traceback.print_exc()
        messages.error(request, "Oops...! Something went wrong!")
        return render(request, "Form/_formfields.html", {"fields": []})

    finally:
        cursor.close()
        m.commit()
        m.close()
        Db.closeConnection()
    
def reject_workflow_step(request):
    wfdetailsid = request.POST.get("wfdetailsid")
    wfDetailsTable_id = request.POST.get("wfDetailsTable_id")
    wfSelected_id = request.POST.get("wfSelected_id")
    logged_actual_step_id = request.POST.get("actual_step_id")
    logged_StepId = int(logged_actual_step_id)
    wd_stepId = logged_StepId - 1
    forwf_stepId = wd_stepId -1
    
    # if wfdetailsid:
    #     wfdetailsid = dec(wfdetailsid)

    step_id_previous = int(wd_stepId)  # Current step
    step_id = step_id_previous - 1  # Previous step

    # Get req_id from workflow_details
    wf_record = workflow_details.objects.filter(id=wfDetailsTable_id, step_id=wd_stepId).first()
    # if not wf_record:
    #     return {'status': False, 'message': 'Workflow detail not found'}

    req_id = wf_record.req_id

    # 1. Insert rejected status in history_workflow_details
    history_workflow_details.objects.create(
        workflow_id=wfSelected_id,
        # workflow_id=None,
        step_id=step_id_previous,
        form_data_id=wf_record.form_data_id,
        req_id=req_id,
        action_details_id=wf_record.action_details_id,
        role_id=wf_record.role_id,
        status=(wf_record.status or '') + " - Rejected",
        operator=None,
        user_id=wf_record.user_id,
        created_by=str(wf_record.user_id),
        created_at=timezone.now(),
        updated_at=timezone.now(),
        updated_by=str(wf_record.user_id),
        increment_id=wf_record.increment_id,
        form_id=wf_record.form_id,
        sent_back='1',
    )
    
    workflow_details.objects.filter(req_id=req_id).update(
        increment_id=wf_record.increment_id - 1,
        status=(wf_record.status or '') + " - Rejected"
        # step_id=forwf_stepId
    )
    
    # context={"reject":1}

    # 2. Fetch previous step from history
    # previous_step = history_workflow_details.objects.filter(
    #     req_id=req_id,
    #     step_id=step_id
    # ).order_by('-increment_id').first()

    # if not previous_step:
    #     return {'status': False, 'message': 'Previous step not found'}

    # # 3. Insert previous step back as editable into history (to re-open it)
    # history_workflow_details.objects.create(
    #     workflow_id=None,
    #     step_id=previous_step.step_id,
    #     form_data_id=previous_step.form_data_id,
    #     req_id=req_id,
    #     action_details_id=previous_step.action_details_id,
    #     role_id=previous_step.role_id,
    #     status="Reopened after Rejection",
    #     operator=None,
    #     user_id=None,
    #     created_by=str(request.user.id),
    #     created_at=timezone.now(),
    #     updated_at=timezone.now(),
    #     updated_by=str(request.user.id),
    #     increment_id=(previous_step.increment_id or 0) + 1,
    #     form_id=previous_step.form_id,
    # )

    # return JsonResponse({'status': True, 'message': 'Rejected and moved back to previous step successfully'})
    messages.success(request, "Workflow Rejected successfully!")
    # return redirect('workflow_starts')
    return redirect(f"{reverse('workflow_starts')}?workflowSelect={wfSelected_id}")
    
    # NOT USING THIS
def workflowcommon_form_post(request):
    user = request.session.get('user_id', '')
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Invalid request method"}, status=400)

        created_by = request.session.get('user_id', '').strip()
        form_name = request.POST.get('form_name', '').strip()

        # Get form ID
        form_id_key = next((key for key in request.POST if key.startswith("form_id_")), None)
        if not form_id_key:
            return JsonResponse({"error": "Form ID not found"}, status=400)

        # form_id = request.POST.get(form_id_key, '').strip()
        # form = get_object_or_404(Form, id=form_id)

        # # Create FormData entry
        # form_data = FormData.objects.create(form=form)
        # form_data.req_no = f"REQNO-00{form_data.id}"
        # form_data.created_by = user
        # form_data.save()

        # saved_values = []
        # file_records = []
        # field_value_map = {}  # Map to store field_id -> FormFieldValues instance

        # # Process each field
        # for key, value in request.POST.items():
        #     if key.startswith("field_id_"):
        #         field_id = value.strip()
        #         field = get_object_or_404(FormField, id=field_id)

        #         # Get actual input value
        #         input_value = request.POST.get(f"field_{field_id}", "").strip()

        #         # Insert into FormFieldValues first
        #         form_field_value = FormFieldValues.objects.create(
        #             form_data=form_data,form=form, field=field, value=input_value, created_by=created_by
        #         )
        #         field_value_map[field_id] = form_field_value


        # for field_key, uploaded_files in request.FILES.lists():
        #     if field_key.startswith("field_"):
        #         field_id = field_key.split("_")[-1].strip()
        #         field = get_object_or_404(FormField, id=field_id)

        #         # Retrieve the corresponding FormFieldValues instance
        #         form_field_value = field_value_map.get(field_id)
        #         if not form_field_value:
        #             continue

        #         # Define file directory
        #         file_dir = os.path.join(settings.MEDIA_ROOT, form_name, created_by, form_data.req_no)
        #         os.makedirs(file_dir, exist_ok=True)

        #         # Loop through files (whether single or multiple)
        #         form_file_ids = []

        #         for uploaded_file in uploaded_files:
        #             original_file_name, file_extension = os.path.splitext(uploaded_file.name.strip())
        #             timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        #             saved_file_name = f"{original_file_name}_{timestamp}{file_extension}"

        #             # Save file
        #             fs = FileSystemStorage(location=file_dir)
        #             saved_path = fs.save(saved_file_name, uploaded_file)

        #             # Generate file path
        #             file_path = os.path.join(form_name, created_by, form_data.req_no, saved_file_name)

        #             # Create FormFile entry
        #             form_file = FormFile.objects.create(
        #                 file_name=saved_file_name,
        #                 uploaded_name=uploaded_file.name.strip(),
        #                 file_id=form_field_value.id,
        #                 file_path=file_path,
        #                 created_by=user,
        #                 form_data=form_data,
        #                 form=form,
        #                 field=field
        #             )


        #             form_file_ids.append(str(form_file.id))

        #         # Save comma-separated list of file IDs
        #         form_field_value.value = ",".join(form_file_ids)
        #         form_field_value.save()

        messages.success(request, "Form data saved successfully!")
    except Exception as e:
        traceback.print_exc()
        messages.error(request, 'Oops...! Something went wrong!')

    finally:
        return redirect('/masters?entity=form_master&type=i')


def redirect_to_workflow_start(request):
    user = request.session.get('user_id', '')
    new_form_data_id = request.POST.get('new_form_data_id')  # or retrieve from POST/session if needed

    if new_form_data_id:
        ReferenceFormStatus.objects.update_or_create(
            form_data=new_form_data_id,  # Assuming form_data_id == req_id in model
            defaults={'status': '2','updated_by':user}
        )

    messages.success(request, "Form data stored with reference successfully!")
    return redirect(reverse('workflow_starts'))


@login_required
def workflow_module(request):  
    Db.closeConnection()
    m = Db.get_connection()
    cursor = m.cursor()

    if request.user.is_authenticated:
        user = request.user.id    
        role_id = str(request.user.role_id)
        
        cursor.callproc("stp_get_Client_module")
        for result in cursor.stored_results():
            module_wf = list(result.fetchall())

    return render(request, "Workflow/workflow_module.html", {
        "module_wf": module_wf,
    })