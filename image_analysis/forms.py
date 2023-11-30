from django import forms

class ImageUploadForm(forms.Form):
    images = forms.FileField(
        label='Select multiple images',
        help_text='Images only (e.g., JPEG, PNG)',
        widget=forms.ClearableFileInput()
    )
