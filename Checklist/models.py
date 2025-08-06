from django.db import models
from django.urls import reverse
from django.core.validators import FileExtensionValidator

class Checklist(models.Model):
    RISK_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]
    
    type = models.CharField(max_length=100)
    task = models.CharField(max_length=255)
    description = models.TextField()
    risk = models.CharField(max_length=10, choices=RISK_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['type', 'task']
        verbose_name = 'Compliance Checklist'
        verbose_name_plural = 'Compliance Checklists'
    class Meta:
        db_table = 'checklist'

    def __str__(self):
        return f"{self.type} - {self.task}"
    
    def get_absolute_url(self):
        return reverse('checklist_detail', kwargs={'pk': self.pk})

class ChecklistDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('PDF', 'Reference Document (PDF)'),
        ('DOC', 'Declaration Form (Word .docx)'),
    ]
    
    checklist_type = models.CharField(max_length=100)
    doc_type = models.CharField(max_length=3, choices=DOC_TYPE_CHOICES)
    file = models.FileField(
        upload_to='compliance_docs/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])
        ]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        ordering = ['checklist_type', 'doc_type']
        verbose_name = 'Checklist Document'
        verbose_name_plural = 'Checklist Documents'
    
    class Meta:
        db_table = 'checklist_doc'
    
    def __str__(self):
        return f"{self.checklist_type} - {self.get_doc_type_display()}"
    
    def get_absolute_url(self):
        return reverse('document_detail', kwargs={'pk': self.pk})