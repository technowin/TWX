from django.db import models

class ChecklistType(models.Model):
    """Model to manage compliance types dynamically"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'checklist_types'

class Checklist(models.Model):
    RISK_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]
    
    type = models.ForeignKey(ChecklistType, on_delete=models.CASCADE, related_name='checklists')
    task = models.CharField(max_length=200)
    description = models.TextField()
    risk = models.CharField(max_length=10, choices=RISK_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['type__name', 'task']
        verbose_name_plural = 'Checklists'

    class Meta:
        db_table = 'checklists'

    def __str__(self):
        return f"{self.type.name} - {self.task}"

class ChecklistDoc(models.Model):
    DOC_TYPE_CHOICES = [
        ('PDF', 'PDF Document'),
        ('DOC', 'Word Document (.docx)'),
        ('XLS', 'Excel Spreadsheet'),
        ('PPT', 'PowerPoint Presentation'),
    ]
    
    checklist_type = models.ForeignKey(ChecklistType, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=10, choices=DOC_TYPE_CHOICES)
    file = models.FileField(upload_to='compliance_docs/%Y/%m/%d/')
    title = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Checklist Document"
        verbose_name_plural = "Checklist Documents"
        ordering = ['checklist_type__name', 'doc_type']
    
    class Meta:
        db_table = 'checklist_documents'
    
    def __str__(self):
        return f"{self.checklist_type.name} - {self.get_doc_type_display()}"