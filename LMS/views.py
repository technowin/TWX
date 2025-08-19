
# User Management System

# views.py
from email.message import EmailMessage
import uuid
from django.forms import FloatField
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from TWX import settings
from .forms import *
from .models import *
from django.db.models import Sum, Max, Count, F, Q, ExpressionWrapper, DecimalField
import razorpay
from django.views.decorators.csrf import csrf_exempt

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime   # if you need datetime somewhere else

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'LMS/accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'LMS/accounts/login.html', {'form': form})

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'LMS/accounts/profile.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('Account')


# Course Management

# views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Course, Module, Lesson, Resource

class CourseListView(ListView):
    model = Course
    template_name = 'LMS/courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 9
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        category_slug = self.request.GET.get('category')
        level = self.request.GET.get('level')
        search = self.request.GET.get('search')
        
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if level:
            queryset = queryset.filter(level=level)
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['levels'] = Course.LEVEL_CHOICES
        return context

class CourseDetailView(DetailView):
    model = Course
    template_name = 'LMS/courses/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        context['is_enrolled'] = False
        context['in_wishlist'] = False
        
        if self.request.user.is_authenticated:
            context['is_enrolled'] = course.students.filter(id=self.request.user.id).exists()
            context['in_wishlist'] = course.wishlist.filter(id=self.request.user.id).exists()
        
        return context

class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'LMS/courses/course_form.html'
    success_url = reverse_lazy('course_list')
    paginate_by = 10
    ordering = ['-created_at']   # safe ordering
    def test_func(self):
        return self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.instructor = self.request.user
        return super().form_valid(form)

class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'LMS/courses/course_form.html'
    success_url = reverse_lazy('admin_course_management')
    def test_func(self):
        return self.request.user == self.get_object().instructor or self.request.user.is_superuser
    
    def get_success_url(self):
        return reverse_lazy('course_detail', kwargs={'slug': self.object.slug})
    
class CourseDeleteView(DeleteView):
    model = Course
    template_name = 'LMS/admin/course_confirm_delete.html'
    success_url = reverse_lazy('admin_course_management')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Course deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
class ModuleCreateView(CreateView):
    model = Module
    form_class = ModuleForm
    template_name = 'LMS/courses/module_form.html'
    
    def test_func(self):
        course = Course.objects.get(slug=self.kwargs['slug'])
        return self.request.user == course.instructor or self.request.user.is_superuser
    
    def get_initial(self):
        initial = super().get_initial()
        course = Course.objects.get(slug=self.kwargs['slug'])
        initial['course'] = course
        return initial
    
    def form_valid(self, form):
        course = Course.objects.get(slug=self.kwargs['slug'])
        form.instance.course = course
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('course_detail', kwargs={'slug': self.kwargs['slug']})

class LessonCreateView(CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'LMS/courses/lesson_form.html'
    
    def test_func(self):
        module = Module.objects.get(id=self.kwargs['module_id'])
        return self.request.user == module.course.instructor or self.request.user.is_superuser
    
    def get_initial(self):
        initial = super().get_initial()
        module = Module.objects.get(id=self.kwargs['module_id'])
        initial['module'] = module
        return initial
    
    def form_valid(self, form):
        module = Module.objects.get(id=self.kwargs['module_id'])
        form.instance.module = module
        return super().form_valid(form)
    
    def get_success_url(self):
        module = Module.objects.get(id=self.kwargs['module_id'])
        return reverse_lazy('course_detail', kwargs={'slug': module.course.slug})

class ResourceCreateView(CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'LMS/courses/resource_form.html'
    
    def test_func(self):
        lesson = Lesson.objects.get(id=self.kwargs['lesson_id'])
        return self.request.user == lesson.module.course.instructor or self.request.user.is_superuser
    
    def get_initial(self):
        initial = super().get_initial()
        lesson = Lesson.objects.get(id=self.kwargs['lesson_id'])
        initial['lesson'] = lesson
        return initial
    
    def form_valid(self, form):
        lesson = Lesson.objects.get(id=self.kwargs['lesson_id'])
        form.instance.lesson = lesson
        return super().form_valid(form)
    
    def get_success_url(self):
        lesson = Lesson.objects.get(id=self.kwargs['lesson_id'])
        return reverse_lazy('course_detail', kwargs={'slug': lesson.module.course.slug})
    

# Enrollment & Access Control

# views.py
@login_required
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.warning(request, 'You are already enrolled in this course!')
        return redirect('course_detail', slug=slug)
    
    # Handle corporate enrollment
    if request.user.user_type == 'CORPORATE_TRAINEE' and request.user.company:
        # Check if company has purchased seats
        corporate_enrollment = CorporateEnrollment.objects.filter(
            company=request.user.company,
            course=course,
            is_active=True,
            access_expiry__gte=timezone.now()
        ).first()
        
        if corporate_enrollment and corporate_enrollment.remaining_seats > 0:
            # Create enrollment request
            request_obj = CorporateEnrollmentRequest.objects.create(
                corporate_enrollment=corporate_enrollment,
                user=request.user,
                requested_by=request.user
            )
            
            # Notify approvers
            approvers = CustomUser.objects.filter(
                company=request.user.company,
                user_type='CORPORATE_APPROVER'
            )
            
            for approver in approvers:
                send_mail(
                    'New Enrollment Request',
                    f'A new enrollment request for {course.title} has been submitted by {request.user.email}.',
                    'noreply@edubrandx.com',
                    [approver.email],
                    fail_silently=False,
                )
            
            messages.info(request, 'Your enrollment request has been submitted for approval.')
            return redirect('course_detail', slug=slug)
    
    # For individual enrollment or when no corporate seats available
    if request.method == 'POST':
        enrollment = Enrollment.objects.create(
            user=request.user,
            course=course,
            status='ACTIVE',
            is_paid=False  # Payment will be handled separately
        )
        
        messages.success(request, 'You have successfully enrolled in this course!')
        return redirect('course_learning', slug=slug)
    
    return render(request, 'LMS/enrollment/enroll_confirm.html', {'course': course})

@login_required
def course_learning(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    
    if enrollment.status != 'ACTIVE':
        messages.warning(request, 'Your enrollment is not currently active.')
        return redirect('course_detail', slug=slug)
    
    # Get first incomplete lesson or last accessed lesson
    completed_lessons = enrollment.lesson_completions.values_list('lesson__id', flat=True)
    modules = course.modules.all().prefetch_related('lessons')
    
    # Find the first incomplete lesson
    next_lesson = None
    for module in modules:
        for lesson in module.lessons.all():
            if lesson.id not in completed_lessons:
                next_lesson = lesson
                break
        if next_lesson:
            break
    
    # If all lessons completed, go to the first lesson
    if not next_lesson and modules.exists() and modules.first().lessons.exists():
        next_lesson = modules.first().lessons.first()
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'next_lesson': next_lesson,
        'progress': enrollment.progress,
    }
    
    return render(request, 'LMS/enrollment/course_learning.html', context)

@login_required
def lesson_detail(request, slug, module_id, lesson_id):
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, id=module_id, course=course)
    lesson = get_object_or_404(Lesson, id=lesson_id, module=module)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    
    if enrollment.status != 'ACTIVE':
        messages.warning(request, 'Your enrollment is not currently active.')
        return redirect('course_detail', slug=slug)
    
    # Check if lesson is free or user is enrolled
    if not lesson.is_free and not enrollment.is_paid and not request.user.is_staff:
        messages.warning(request, 'You need to complete payment to access this lesson.')
        return redirect('course_payment', slug=slug)
    
    # Mark as completed or update last accessed
    LessonCompletion.objects.update_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={'last_accessed': timezone.now()}
    )
    
    # Get next and previous lessons
    lessons = list(module.lessons.all())
    current_index = lessons.index(lesson)
    prev_lesson = lessons[current_index - 1] if current_index > 0 else None
    next_lesson = lessons[current_index + 1] if current_index < len(lessons) - 1 else None
    
    # Get resources
    resources = lesson.resources.all()
    
    context = {
        'course': course,
        'module': module,
        'lesson': lesson,
        'enrollment': enrollment,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'resources': resources,
        'progress': enrollment.progress,
    }
    
    return render(request, 'LMS/enrollment/lesson_detail.html', context)

@login_required
def corporate_enrollment_requests(request):
    if not request.user.user_type == 'CORPORATE_APPROVER':
        raise PermissionDenied
    
    requests = CorporateEnrollmentRequest.objects.filter(
        corporate_enrollment__company=request.user.company,
        status='PENDING'
    ).select_related('user', 'corporate_enrollment', 'corporate_enrollment__course')
    
    context = {
        'requests': requests,
    }
    
    return render(request, 'LMS/enrollment/corporate_requests.html', context)

@login_required
def process_corporate_request(request, request_id, action):
    if not request.user.user_type == 'CORPORATE_APPROVER':
        raise PermissionDenied
    
    enrollment_request = get_object_or_404(CorporateEnrollmentRequest, id=request_id)
    
    if enrollment_request.corporate_enrollment.company != request.user.company:
        raise PermissionDenied
    
    if action == 'approve':
        if enrollment_request.approve(request.user):
            messages.success(request, 'Enrollment request approved successfully.')
        else:
            messages.error(request, 'Could not approve the request. No seats available or request already processed.')
    elif action == 'reject':
        comments = request.POST.get('comments', '')
        if enrollment_request.reject(request.user, comments):
            messages.success(request, 'Enrollment request rejected.')
        else:
            messages.error(request, 'Could not reject the request. It may have already been processed.')
    
    return redirect('corporate_enrollment_requests')


# Payment & Subscription

# views.py
@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    course_ids = list(cart.keys())
    courses = Course.objects.filter(id__in=course_ids, is_active=True)
    
    # Calculate total
    total = sum(course.current_price * cart[str(course.id)] for course in courses)
    
    # Apply coupon if exists
    coupon_code = request.session.get('coupon_code')
    coupon = None
    discount = 0
    
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid(request.user):
                discount = coupon.apply_discount(total)
            else:
                messages.warning(request, 'The coupon code is no longer valid.')
                request.session.pop('coupon_code', None)
                coupon = None
        except Coupon.DoesNotExist:
            messages.warning(request, 'Invalid coupon code.')
            request.session.pop('coupon_code', None)
    
    context = {
        'courses': courses,
        'cart': cart,
        'total': total,
        'coupon': coupon,
        'discount': discount,
        'subtotal': total - discount,
    }
    
    return render(request, 'LMS/payment/cart.html', context)

@login_required
def add_to_cart(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    
    cart = request.session.get('cart', {})
    course_id = str(course.id)
    
    if course_id in cart:
        cart[course_id] += 1
    else:
        cart[course_id] = 1
    
    request.session['cart'] = cart
    messages.success(request, f'"{course.title}" has been added to your cart.')
    
    return redirect('course_detail', slug=slug)

@login_required
def remove_from_cart(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    cart = request.session.get('cart', {})
    course_id = str(course.id)
    
    if course_id in cart:
        del cart[course_id]
        request.session['cart'] = cart
        messages.success(request, f'"{course.title}" has been removed from your cart.')
    
    return redirect('cart')

@login_required
def apply_coupon(request):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code', '').strip()
        
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid(request.user):
                request.session['coupon_code'] = coupon_code
                messages.success(request, 'Coupon applied successfully!')
            else:
                messages.warning(request, 'This coupon is no longer valid.')
        except Coupon.DoesNotExist:
            messages.error(request, 'Invalid coupon code.')
    
    return redirect('cart')

@login_required
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    messages.info(request, 'Coupon removed.')
    return redirect('cart')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('course_list')
    
    course_ids = list(cart.keys())
    courses = Course.objects.filter(id__in=course_ids, is_active=True)
    
    # Calculate total
    total = sum(course.current_price * cart[str(course.id)] for course in courses)
    
    # Apply coupon if exists
    coupon_code = request.session.get('coupon_code')
    coupon = None
    discount = 0
    
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid(request.user):
                discount = coupon.apply_discount(total)
            else:
                messages.warning(request, 'The coupon code is no longer valid.')
                request.session.pop('coupon_code', None)
                coupon = None
        except Coupon.DoesNotExist:
            messages.warning(request, 'Invalid coupon code.')
            request.session.pop('coupon_code', None)
    
    subtotal = total - discount
    
    if request.method == 'POST':
        # Create order
        order = Order.objects.create(
            user=request.user,
            amount=total,
            discount_amount=discount,
            tax_amount=0,  # Can be calculated based on location
            status='CREATED'
        )
        
        if coupon:
            order.coupon = coupon
            order.save()
            coupon.uses += 1
            coupon.save()
        
        # Create order items
        for course in courses:
            OrderItem.objects.create(
                order=order,
                course=course,
                price=course.current_price,
                quantity=cart[str(course.id)]
            )
        
        # Initialize Razorpay payment
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        payment_data = {
            'amount': int(subtotal * 100),  # Razorpay expects amount in paise
            'currency': 'INR',
            'receipt': f'order_{order.id}',
            'payment_capture': '1',
            'notes': {
                'order_id': str(order.id),
                'user_id': str(request.user.id),
            }
        }
        
        razorpay_order = client.order.create(data=payment_data)
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=subtotal,
            currency='INR',
            payment_method='RAZORPAY',
            transaction_id=razorpay_order['id'],
            razorpay_order_id=razorpay_order['id'],
            status='PENDING',
            notes={
                'order_id': str(order.id),
                'courses': [str(course.id) for course in courses],
            }
        )
        
        order.payment = payment
        order.save()
        
        context = {
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount': subtotal,
            'currency': 'INR',
            'name': settings.COMPANY_NAME,
            'description': f'Payment for {len(courses)} course(s)',
            'image': settings.LOGO_URL,
            'prefill': {
                'name': request.user.get_full_name(),
                'email': request.user.email,
                'contact': request.user.phone or '',
            },
            'theme': {
                'color': '#F37254' if not request.user.dark_mode else '#2D3748',
            },
            'order_id': order.id,
        }
        
        return render(request, 'LMS/payment/checkout.html', context)
    
    context = {
        'courses': courses,
        'cart': cart,
        'total': total,
        'coupon': coupon,
        'discount': discount,
        'subtotal': subtotal,
        'user': request.user,
    }
    
    return render(request, 'LMS/payment/checkout_review.html', context)

@csrf_exempt
def razorpay_callback(request):
    if request.method == 'POST':
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        # Verify payment
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
            
            # Get payment and order
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            order = payment.orders.first()
            
            # Update payment status
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'COMPLETED'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Update order status
            order.status = 'PAID'
            order.save()
            
            # Enroll user in courses
            for item in order.items.all():
                if item.course:
                    Enrollment.objects.create(
                        user=order.user,
                        course=item.course,
                        is_paid=True,
                        payment_amount=item.price,
                        payment_date=timezone.now(),
                        payment_method='RAZORPAY',
                        transaction_id=razorpay_payment_id
                    )
            
            # Clear cart and coupon
            if 'cart' in request.session:
                del request.session['cart']
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
            
            return redirect('payment_success', order_id=order.id)
        
        except Exception as e:
            print(f"Payment verification failed: {str(e)}")
            return redirect('payment_failed')
    
    return redirect('payment_failed')

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'LMS/payment/success.html', {'order': order})

@login_required
def payment_failed(request):
    return render(request, 'LMS/payment/failed.html')


# Learning Experience

@login_required
def generate_certificate(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)

    if enrollment.progress < 100:
        messages.warning(request, 'You must complete the course to generate a certificate.')
        return redirect('course_learning', slug=enrollment.course.slug)

    # Create or get certificate
    certificate, created = Certificate.objects.get_or_create(
        enrollment=enrollment,
        defaults={
            'certificate_id': str(uuid.uuid4()),
            'issued_date': datetime.now(),
            'verification_url': f"{settings.SITE_URL}/verify/{uuid.uuid4()}"
        }
    )

    if not created:
        certificate.download_count = (certificate.download_count or 0) + 1
        certificate.save()

    # Prepare PDF response
    response = FileResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{enrollment.course.slug}.pdf"'

    # PDF page setup
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Add background image if exists
    bg_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'certificate_bg.jpg')
    if os.path.exists(bg_path):
        p.drawImage(bg_path, 0, 0, width=width, height=height)

    # Title
    p.setFont("Helvetica-Bold", 32)
    p.drawCentredString(width / 2, height - 100, "Certificate of Completion")

    # Subtitle
    p.setFont("Helvetica", 18)
    p.drawCentredString(width / 2, height - 140, "This is to certify that")

    # Recipient Name
    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(width / 2, height - 180, request.user.get_full_name())

    # Course completion line
    p.setFont("Helvetica", 18)
    p.drawCentredString(width / 2, height - 220, "has successfully completed the course")

    # Course title
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 260, enrollment.course.title)

    # Issue date
    p.setFont("Helvetica", 16)
    p.drawCentredString(width / 2, height - 300, f"on {certificate.issued_date.strftime('%B %d, %Y')}")

    # Footer details
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2, 40, f"Certificate ID: {certificate.certificate_id}")
    p.drawCentredString(width / 2, 25, f"Verify at: {certificate.verification_url}")

    # Finalize PDF
    p.showPage()
    p.save()

    return response

@login_required
def verify_certificate(request, verification_uuid):
    certificate = get_object_or_404(
        Certificate, 
        verification_url__contains=verification_uuid,
        is_active=True
    )
    
    return render(request, 'LMS/learning/verify_certificate.html', {'certificate': certificate})

@login_required
def add_note(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = get_object_or_404(
        Enrollment, 
        user=request.user, 
        course=lesson.module.course
    )
    
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.lesson = lesson
            note.save()
            messages.success(request, 'Note saved successfully!')
            return redirect('lesson_detail', 
                          slug=lesson.module.course.slug,
                          module_id=lesson.module.id,
                          lesson_id=lesson.id)
    else:
        form = NoteForm()
    
    return render(request, 'LMS/learning/add_note.html', {
        'form': form,
        'lesson': lesson,
    })

@login_required
def toggle_bookmark(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = get_object_or_404(
        Enrollment, 
        user=request.user, 
        course=lesson.module.course
    )
    
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )
    
    if not created:
        bookmark.delete()
        messages.info(request, 'Bookmark removed.')
    else:
        messages.success(request, 'Lesson bookmarked!')
    
    return redirect('lesson_detail', 
                   slug=lesson.module.course.slug,
                   module_id=lesson.module.id,
                   lesson_id=lesson.id)

@login_required
def update_bookmark(request, bookmark_id):
    bookmark = get_object_or_404(Bookmark, id=bookmark_id, user=request.user)
    
    if request.method == 'POST':
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bookmark updated!')
            return redirect('lesson_detail', 
                          slug=bookmark.lesson.module.course.slug,
                          module_id=bookmark.lesson.module.id,
                          lesson_id=bookmark.lesson.id)
    else:
        form = BookmarkForm(instance=bookmark)
    
    return render(request, 'LMS/learning/update_bookmark.html', {
        'form': form,
        'bookmark': bookmark,
    })

@login_required
def add_discussion(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = get_object_or_404(
        Enrollment, 
        user=request.user, 
        course=lesson.module.course
    )
    
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.user = request.user
            discussion.lesson = lesson
            discussion.save()
            messages.success(request, 'Discussion posted!')
            return redirect('lesson_detail', 
                          slug=lesson.module.course.slug,
                          module_id=lesson.module.id,
                          lesson_id=lesson.id)
    else:
        form = DiscussionForm()
    
    return render(request, 'LMS/learning/add_discussion.html', {
        'form': form,
        'lesson': lesson,
    })

@login_required
def reply_discussion(request, discussion_id):
    parent_discussion = get_object_or_404(Discussion, id=discussion_id)
    lesson = parent_discussion.lesson
    enrollment = get_object_or_404(
        Enrollment, 
        user=request.user, 
        course=lesson.module.course
    )
    
    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.user = request.user
            reply.lesson = lesson
            reply.parent = parent_discussion
            reply.save()
            
            # Notify the parent discussion author
            if parent_discussion.user != request.user:
                send_mail(
                    'New Reply to Your Discussion',
                    f'{request.user.get_full_name()} has replied to your discussion on "{lesson.title}".',
                    'noreply@edubrandx.com',
                    [parent_discussion.user.email],
                    fail_silently=False,
                )
            
            messages.success(request, 'Reply posted!')
            return redirect('lesson_detail', 
                          slug=lesson.module.course.slug,
                          module_id=lesson.module.id,
                          lesson_id=lesson.id)
    else:
        form = ReplyForm()
    
    return render(request, 'LMS/learning/reply_discussion.html', {
        'form': form,
        'parent_discussion': parent_discussion,
        'lesson': lesson,
    })

def send_mail(subject, message, from_email, recipient_list, fail_silently=False):
    # This function can be customized to use any email backend
    return EmailMessage(subject, message, from_email, recipient_list).send(fail_silently=fail_silently)

@login_required
def vote_discussion(request, discussion_id, vote_type):
    discussion = get_object_or_404(Discussion, id=discussion_id)
    
    # Ensure user can't vote on their own discussion
    if discussion.user == request.user:
        messages.warning(request, "You can't vote on your own discussion.")
        return redirect('lesson_detail', 
                       slug=discussion.lesson.module.course.slug,
                       module_id=discussion.lesson.module.id,
                       lesson_id=discussion.lesson.id)
    
    # Check if user already voted
    existing_vote = DiscussionVote.objects.filter(
        discussion=discussion,
        user=request.user
    ).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Same vote - remove it
            existing_vote.delete()
            messages.info(request, 'Your vote has been removed.')
        else:
            # Different vote - update it
            existing_vote.vote_type = vote_type
            existing_vote.save()
            messages.success(request, 'Your vote has been updated.')
    else:
        # New vote
        DiscussionVote.objects.create(
            discussion=discussion,
            user=request.user,
            vote_type=vote_type
        )
        messages.success(request, 'Thank you for voting!')
    
    return redirect('lesson_detail', 
                   slug=discussion.lesson.module.course.slug,
                   module_id=discussion.lesson.module.id,
                   lesson_id=discussion.lesson.id)

@login_required
def mark_resolved(request, discussion_id):
    discussion = get_object_or_404(Discussion, id=discussion_id, user=request.user)
    
    discussion.is_resolved = True
    discussion.save()
    
    messages.success(request, 'Discussion marked as resolved.')
    return redirect('lesson_detail', 
                   slug=discussion.lesson.module.course.slug,
                   module_id=discussion.lesson.module.id,
                   lesson_id=discussion.lesson.id)


# Admin Interface

# views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model

User = get_user_model()


@method_decorator(staff_member_required, name='dispatch')
class AdminDashboardView(TemplateView):
    template_name = 'LMS/admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Total counts (fewer queries)
        total_users = CustomUser.objects.count()
        total_courses = Course.objects.count()
        total_enrollments = Enrollment.objects.count()
        total_revenue = Payment.objects.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Recent activity (limit to 5 each)
        recent_users = CustomUser.objects.order_by('-date_joined')[:5]
        recent_payments = Payment.objects.filter(
            status='COMPLETED'
        ).select_related('user').order_by('-completed_at')[:5]
        recent_courses = Course.objects.order_by('-created_at')[:5]

        # Enrollment stats by user type (1 query with aggregation)
        enrollment_stats_qs = Enrollment.objects.values('user__user_type').annotate(total=Count('id'))
        enrollment_stats = {
            'individual': 0,
            'corporate': 0,
            'group': 0
        }
        for stat in enrollment_stats_qs:
            if stat['user__user_type'] == 'INDIVIDUAL':
                enrollment_stats['individual'] = stat['total']
            elif stat['user__user_type'] == 'CORPORATE_TRAINEE':
                enrollment_stats['corporate'] = stat['total']
            elif stat['user__user_type'] == 'GROUP_TRAINEE':
                enrollment_stats['group'] = stat['total']

        # Course completion stats
        completed_count = Enrollment.objects.filter(status='COMPLETED').count()
        in_progress_count = Enrollment.objects.filter(status='ACTIVE').count()
        completion_rate = round(
            (completed_count / total_enrollments * 100) if total_enrollments else 0, 1
        )

        completion_stats = {
            'completed': completed_count,
            'in_progress': in_progress_count,
            'completion_rate': completion_rate
        }

        # Assign to context
        context.update({
            'total_users': total_users,
            'total_courses': total_courses,
            'total_enrollments': total_enrollments,
            'total_revenue': total_revenue,
            'recent_users': recent_users,
            'recent_payments': recent_payments,
            'recent_courses': recent_courses,
            'enrollment_stats': enrollment_stats,
            'completion_stats': completion_stats
        })

        return context


@method_decorator(staff_member_required, name='dispatch')
class UserManagementView(ListView):
    model = CustomUser
    template_name = 'LMS/admin/user_management.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user type if specified
        user_type = self.request.GET.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        # Search by name or email
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_types'] = CustomUser.USER_TYPES
        return context

@staff_member_required
def user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    enrollments = user.enrollments.select_related('course')
    payments = user.payments.order_by('-created_at')
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully!')
            return redirect('admin_user_detail', user_id=user.id)
    else:
        form = UserEditForm(instance=user)
    
    context = {
        'user': user,
        'enrollments': enrollments,
        'payments': payments,
        'form': form,
    }
    
    return render(request, 'LMS/admin/user_detail.html', context)

@method_decorator(staff_member_required, name='dispatch')
class CourseManagementView(ListView):
    model = Course
    template_name = 'LMS/admin/course_management.html'
    context_object_name = 'courses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if specified
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by category if specified
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Search by title
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

@staff_member_required
def enrollment_management(request):
    enrollments = Enrollment.objects.select_related('user', 'course').order_by('-enrollment_date')
    
    # Filters
    status = request.GET.get('status')
    if status:
        enrollments = enrollments.filter(status=status)
    
    user_type = request.GET.get('user_type')
    if user_type:
        enrollments = enrollments.filter(user__user_type=user_type)
    
    course = request.GET.get('course')
    if course:
        enrollments = enrollments.filter(course__slug=course)
    
    context = {
        'enrollments': enrollments[:50],  # Limit to 50 for performance
        'status_choices': Enrollment.STATUS_CHOICES,
        'user_types': CustomUser.USER_TYPES,
        'courses': Course.objects.all(),
    }
    
    return render(request, 'LMS/admin/enrollment_management.html', context)

@staff_member_required
def update_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Enrollment updated successfully!')
            return redirect('admin_enrollment_management')
    else:
        form = EnrollmentForm(instance=enrollment)
    
    context = {
        'form': form,
        'enrollment': enrollment,
    }
    
    return render(request, 'LMS/admin/update_enrollment.html', context)

@staff_member_required
def corporate_management(request):
    companies = Company.objects.annotate(
        user_count=Count('customuser'),
        enrollment_count=Count('corporateenrollment')
    ).order_by('-user_count')

    
    context = {
        'companies': companies,
    }
    
    return render(request, 'LMS/admin/corporate_management.html', context)

@staff_member_required
def company_detail(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    approvers = CustomUser.objects.filter(company=company, user_type='CORPORATE_APPROVER')
    trainees = CustomUser.objects.filter(company=company, user_type='CORPORATE_TRAINEE')
    enrollments = CorporateEnrollment.objects.filter(company=company)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company updated successfully!')
            return redirect('admin_company_detail', company_id=company.id)
    else:
        form = CompanyForm(instance=company)
    
    context = {
        'company': company,
        'approvers': approvers,
        'trainees': trainees,
        'enrollments': enrollments,
        'form': form,
    }
    
    return render(request, 'LMS/admin/company_detail.html', context)

@staff_member_required
def reports(request):
    # Course completion report
    course_completion = Course.objects.annotate(
        total_enrollments=Count('enrollments'),
        completed_enrollments=Count('enrollments', filter=Q(enrollments__status='COMPLETED')),
    ).order_by('-completed_enrollments')

    for course in course_completion:
        if course.total_enrollments > 0:
            course.completion_rate = course.completed_enrollments * 100.0 / course.total_enrollments
        else:
            course.completion_rate = 0

    
    # Revenue report
    revenue_by_course = Course.objects.annotate(
        total_revenue=Sum('enrollments__payment_amount', filter=Q(enrollments__is_paid=True)),
        enrollments_count=Count('enrollments', filter=Q(enrollments__is_paid=True))
    ).filter(total_revenue__gt=0).order_by('-total_revenue')
    
    # User activity report
    active_users = CustomUser.objects.annotate(
    enrollment_count=Count('enrollments'),
    last_enrollment_activity=Max('enrollments__lesson_completions__last_accessed')
    ).order_by('-last_enrollment_activity')[:10]
    
    context = {
        'course_completion': course_completion,
        'revenue_by_course': revenue_by_course,
        'active_users': active_users,
    }
    
    return render(request, 'LMS/admin/reports.html', context)


# Notification 

# views.py
@login_required
def notifications_view(request):
    notifications = request.user.notifications.order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Mark as read via AJAX
        notification_id = request.POST.get('notification_id')
        if notification_id:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'status': 'success'})
    
    return render(request, 'LMS/notifications/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


# Feedback 

# views.py
@login_required
def submit_feedback(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    
    if enrollment.status != 'COMPLETED':
        messages.warning(request, 'You must complete the course to submit feedback.')
        return redirect('course_learning', slug=enrollment.course.slug)
    
    if Feedback.objects.filter(enrollment=enrollment).exists():
        messages.info(request, 'You have already submitted feedback for this course.')
        return redirect('course_learning', slug=enrollment.course.slug)
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.enrollment = enrollment
            feedback.save()
            
            # Generate certificate if not already exists
            Certificate.objects.get_or_create(enrollment=enrollment)
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('course_learning', slug=enrollment.course.slug)
    else:
        form = FeedbackForm()
    
    return render(request, 'LMS/feedback/submit_feedback.html', {
        'form': form,
        'enrollment': enrollment,
    })


# views.py
@staff_member_required
def corporate_enrollment_requests(request):
    requests = CorporateEnrollmentRequest.objects.select_related(
        'corporate_enrollment', 
        'user',
        'corporate_enrollment__company',
        'corporate_enrollment__course'
    ).order_by('-request_date')
    
    status = request.GET.get('status')
    if status:
        requests = requests.filter(status=status)
    
    company = request.GET.get('company')
    if company:
        requests = requests.filter(corporate_enrollment__company__id=company)
    
    context = {
        'requests': requests,
        'status_choices': CorporateEnrollmentRequest.STATUS_CHOICES,
        'companies': Company.objects.all(),
    }
    
    return render(request, 'LMS/admin/corporate_enrollment_requests.html', context)

@staff_member_required
def process_corporate_request(request, request_id):
    enrollment_request = get_object_or_404(CorporateEnrollmentRequest, id=request_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # Create enrollment for the user
            Enrollment.objects.create(
                user=enrollment_request.user,
                course=enrollment_request.corporate_enrollment.course,
                status='ACTIVE',
                is_paid=True,
                payment_amount=0,  # Already paid by company
                approved_by=request.user,
                approved_date=timezone.now(),
                access_expiry=enrollment_request.corporate_enrollment.access_expiry
            )
            enrollment_request.status = 'APPROVED'
            enrollment_request.processed_by = request.user
            enrollment_request.processed_date = timezone.now()
            enrollment_request.save()
            
            messages.success(request, 'Request approved and enrollment created!')
            
        elif action == 'reject':
            enrollment_request.status = 'REJECTED'
            enrollment_request.processed_by = request.user
            enrollment_request.processed_date = timezone.now()
            enrollment_request.save()
            
            messages.success(request, 'Request rejected!')
        
        return redirect('admin_corporate_enrollment_requests')
    
    context = {
        'request': enrollment_request,
    }
    
    return render(request, 'LMS/admin/process_corporate_request.html', context)


@require_POST
def add_to_wishlist(request, slug):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to add items to your wishlist')
        return redirect('login')
    
    course = get_object_or_404(Course, slug=slug)
    if course in request.user.wishlisted_courses.all():
        messages.info(request, 'This course is already in your wishlist')
    else:
        request.user.wishlisted_courses.add(course)
        messages.success(request, 'Course added to your wishlist')
    
    # Redirect back to the previous page
    return redirect(request.META.get('HTTP_REFERER', 'course_list'))

@require_POST
def remove_from_wishlist(request, slug):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to manage your wishlist')
        return redirect('login')
    
    course = get_object_or_404(Course, slug=slug)
    if course in request.user.wishlisted_courses.all():
        request.user.wishlisted_courses.remove(course)
        messages.success(request, 'Course removed from your wishlist')
    else:
        messages.info(request, 'This course was not in your wishlist')
    
    # Redirect back to the previous page
    return redirect(request.META.get('HTTP_REFERER', 'course_list'))

def wishlist_view(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to view your wishlist')
        return redirect('login')
    
    wishlist_courses = request.user.wishlisted_courses.all()
    context = {
        'wishlist_courses': wishlist_courses,
    }
    return render(request, 'LMS/courses/wishlist.html', context)