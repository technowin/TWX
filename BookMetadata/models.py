from django.db import models

class BookMetadata(models.Model):
    LANGUAGE_CHOICES = [
    # Major Indian Languages
    ('Hindi', 'Hindi'),
    ('Bengali', 'Bengali'),
    ('Tamil', 'Tamil'),
    ('Telugu', 'Telugu'),
    ('Marathi', 'Marathi'),
    ('Gujarati', 'Gujarati'),
    ('Kannada', 'Kannada'),
    ('Malayalam', 'Malayalam'),
    ('Punjabi', 'Punjabi'),
    ('Odia', 'Odia'),
    ('Assamese', 'Assamese'),
    ('Maithili', 'Maithili'),
    ('Santali', 'Santali'),
    ('Kashmiri', 'Kashmiri'),
    ('Nepali', 'Nepali'),
    ('Sindhi', 'Sindhi'),
    ('Konkani', 'Konkani'),
    ('Dogri', 'Dogri'),
    ('Manipuri', 'Manipuri'),
    ('Bhojpuri', 'Bhojpuri'),
    ('Urdu', 'Urdu'),
    
    # Other Widely Used Languages
    ('English', 'English'),
    ('French', 'French'),
    ('German', 'German'),
    ('Spanish', 'Spanish'),
    ('Portuguese', 'Portuguese'),
    ('Russian', 'Russian'),
    ('Chinese', 'Chinese'),
    ('Japanese', 'Japanese'),
    ('Arabic', 'Arabic'),
    
    # Additional Indian Languages
    ('Bodo', 'Bodo'),
    ('Sanskrit', 'Sanskrit'),
    ('Mizo', 'Mizo'),
    ('Tulu', 'Tulu'),
    ('Khasi', 'Khasi'),
    ('Garo', 'Garo'),
    ('Nagamese', 'Nagamese'),
    
    # Generic Option
    ('Other', 'Other'),
]
    language = models.TextField(
        choices=LANGUAGE_CHOICES,
        blank=True,
        null=True
    )
    isbn_no = models.TextField(
        blank=True,
        null=True,
        verbose_name='ISBN Number'
    )
    title = models.TextField(
        blank=True,
        null=True
    )
    author = models.TextField(
        blank=True,
        null=True
    )
    edition = models.TextField(
        blank=True,
        null=True
    )
    publisher_name = models.TextField(
        blank=True,
        null=True,
        verbose_name='Publisher'
    )
    publisher_place = models.TextField(
        blank=True,
        null=True,
        verbose_name='Publisher Location'
    )
    year_of_publication = models.TextField(
        blank=True,
        null=True,
        verbose_name='Year'
    )
    accession_no = models.TextField(
        blank=True,
        null=True,
        verbose_name='Accession Number'
    )
    class_no = models.TextField(
        blank=True,
        null=True,
        verbose_name='Class Number'
    )
    book_no = models.TextField(
        blank=True,
        null=True,
        verbose_name='Book Number'
    )
    pagination = models.TextField(
        blank=True,
        null=True,
        verbose_name='Pages'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_auto_generated = models.BooleanField(default=False)

    def __str__(self):
        return self.title or "Untitled Book"

    class Meta:
        verbose_name = "Book Metadata"
        verbose_name_plural = "Books Metadata"
        ordering = ['-created_at']